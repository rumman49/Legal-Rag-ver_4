"""Shared helpers for the GSMS-B importers.

* Loads the app's REAL system-prompt builder (backend/app/rag/rag_pipeline.py) by
  AST, so the heavy app dependencies (langchain, settings, Groq) are not needed
  and the training prompt can never drift from what the app sends.
* Downloads the public datasets from Hugging Face into a cache dir.
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys
import types
import urllib.request
from pathlib import Path
from typing import Callable, List, Optional

REPO = Path(__file__).resolve().parents[2]
PIPELINE = REPO / "backend" / "app" / "rag" / "rag_pipeline.py"
CACHE = Path(os.environ.get("GSMSB_CACHE", REPO / "finetune" / "data" / "_cache"))
OUT = REPO / "finetune" / "data"

HF = "https://huggingface.co/datasets"
QA_REPO = "GSMS-B/Indian-Legal-QA-BNS-BNSS-BSA"
MAP_REPO = "GSMS-B/ipc-bns-crpc-bnss-iea-bsa-respective-old-new-sections-mapping"
SEC_REPO = "GSMS-B/indian-legal-sections-bns-bnss-bsa-2023"

ACT_DISPLAY = {
    "BNS": "The Bharatiya Nyaya Sanhita, 2023",
    "BNSS": "The Bharatiya Nagarik Suraksha Sanhita, 2023",
    "BSA": "The Bharatiya Sakshya Adhiniyam, 2023",
}


def fetch(repo: str, name: str) -> Path:
    """Download one file of a HF dataset (cached)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / name
    if not dest.exists():
        url = f"{HF}/{repo}/resolve/main/{name}"
        with urllib.request.urlopen(url, timeout=120) as r:
            dest.write_bytes(r.read())
    return dest


def load_json(repo: str, name: str):
    return json.loads(fetch(repo, name).read_text(encoding="utf-8"))


def load_jsonl(repo: str, name: str):
    return [json.loads(l) for l in fetch(repo, name).read_text(encoding="utf-8").splitlines() if l.strip()]


# --------------------------------------------------------------------------- app prompt
class _FakeMapping:
    block: Optional[str] = None

    def get_transition_guidance(self, query, docs):
        return _FakeMapping.block


def _load_app_functions():
    src = PIPELINE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    keep = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in ("detect_query_language", "build_dynamic_system_prompt"):
            keep.append(node)
    mod = ast.Module(body=keep, type_ignores=[])
    ns = {"re": re, "List": List, "Document": object, "logger": __import__("logging").getLogger("app")}
    fake = types.ModuleType("app.rag.law_mapping_service")
    fake.get_law_mapping_service = lambda: _FakeMapping()
    for name in ("app", "app.rag"):
        sys.modules.setdefault(name, types.ModuleType(name))
    sys.modules["app.rag.law_mapping_service"] = fake
    exec(compile(mod, str(PIPELINE), "exec"), ns)
    return ns["detect_query_language"], ns["build_dynamic_system_prompt"]


detect_query_language, _build = _load_app_functions()


def system_prompt(query: str, context: str, transition_block: Optional[str] = None) -> str:
    _FakeMapping.block = transition_block
    return _build(query, []).replace("{context}", context)


def context_header(i: int, act_code: str, sec_no: str, title: str, chapter: str = "") -> str:
    act = ACT_DISPLAY[act_code]
    scope = f" | Scope: {chapter}" if chapter else ""
    return f"--- Source [{i}]: {act} — Section {sec_no} | Act: {act} | Provision: {sec_no} {title}{scope} ---"


def clean_body(text: str) -> str:
    """Drop the dataset's '[Context: ...]' preamble (the app strips its own '[Act: ...]' one)."""
    return re.sub(r"^\[Context:[^\]]*\]\s*", "", text).strip()


def approx_tokens(s: str) -> int:
    return len(s) // 3  # conservative for legal English + Devanagari mix


NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers(s: str) -> set:
    return {n.replace(",", "") for n in NUM.findall(s)}


CASE_LAW = re.compile(r"\bv\.?s?\.?\s+[A-Z]|\bAIR\s+\d{4}|\bSCC\b|supreme court (held|ruled)", re.I)


def chat(system: str, user: str, assistant: str, meta: dict) -> dict:
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "meta": meta,
    }


def write_jsonl(path: Path, rows: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
