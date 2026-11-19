"""Importer 1: GSMS-B Indian-Legal-QA (Apache-2.0) -> RAG-format chat examples (English).

Each example = the app's real system prompt + retrieved-style context (the real
section text from GSMS-B sections, plus unrelated "noise" sections like a real
retriever returns) + the dataset question -> the dataset's reference answer,
reformatted with the app's citation style.  Rows are DROPPED when they cannot be
verified against the context.  A slice becomes refusals (context unrelated).

Run:  python finetune/importers/gsmsb_qa.py [--acts BNS,BSA,BNSS] [--refusal-frac 0.12]
"""
from __future__ import annotations

import argparse
import hashlib
import random
import re
from collections import Counter

from common import *

SRC_TAG = re.compile(r"\s*\[Source:[^\]]*\]\s*$")
DEICTIC = re.compile(
    r"\b(this|the above|aforementioned)\s+(section|provision|sub-?section|clause|article|rule|illustration|exception|explanation)\b"
    r"|\bunder this\b|\bin this (act|sanhita|law)\b|\bthis (sanhita|adhiniyam)\b",
    re.I,
)
STOP = set("the of and or in to a an for on by with as at from is are be any other shall".split())


def toks(title: str) -> set:
    return {w for w in re.findall(r"[a-z]{4,}", title.lower()) if w not in STOP}


def stable_split(chunk_id: str, test_frac: float) -> str:
    h = int(hashlib.md5(chunk_id.encode()).hexdigest(), 16) % 1000
    return "test" if h < test_frac * 1000 else "train"


def verify(answer_body: str, ctx: str, question: str) -> str | None:
    """Return a rejection reason, or None if the answer is supported by the prompt."""
    if len(answer_body) < 40:
        return "too_short"
    if CASE_LAW.search(answer_body):
        return "case_law"
    if re.search(r"[ऀ-ॿ]", answer_body):
        return "script"
    extra = numbers(answer_body) - numbers(ctx) - numbers(question)
    if extra:
        return "number_not_in_context"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--acts", default="BNS,BSA,BNSS")
    ap.add_argument("--refusal-frac", type=float, default=0.25)
    ap.add_argument("--test-frac", type=float, default=0.08)
    ap.add_argument("--noise", type=int, default=2, help="unrelated sections added to each context")
    ap.add_argument("--max-tokens", type=int, default=5500)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    acts = set(a.acts.split(","))

    qa = load_jsonl(QA_REPO, "bns_bnss_bsa_combined_legal_qa.jsonl")
    secs = {s["chunk_id"]: s for s in load_json(SEC_REPO, "bns_bnss_bsa_sections.json")}
    pool = [s for s in secs.values() if s["chunk_id"].split("_")[0] in acts and len(s["text"]) < 6000]

    drops, train, test = Counter(), [], []
    seen_q = set()
    for r in qa:
        act = r["chunk_id"].split("_")[0]
        if act not in acts:
            continue
        sec = secs[r["chunk_id"]]
        q = r["question"].strip()
        if DEICTIC.search(q):
            drops["deictic_question"] += 1
            continue
        key = (r["chunk_id"], re.sub(r"\W+", " ", q.lower()))
        if key in seen_q:
            drops["duplicate"] += 1
            continue
        seen_q.add(key)
        body = SRC_TAG.sub("", r["answer"]).strip()
        target_text = clean_body(sec["text"])
        why = verify(body, target_text, q)
        if why:
            drops[why] += 1
            continue

        # noise: sections from other titles/chapters (never the target, never same title words)
        tt = toks(sec["section_title"])
        noise = []
        for _ in range(60):
            c = rng.choice(pool)
            if c["chunk_id"] == sec["chunk_id"] or (toks(c["section_title"]) & tt) or c["chapter"] == sec["chapter"]:
                continue
            noise.append(c)
            if len(noise) == a.noise:
                break

        title_words = re.findall(r"[A-Za-z]+", sec["section_title"])
        eligible = (
            r["question_type"] in ("definitional_topic", "scenario")
            and len(title_words) >= 2
            and not re.search(r"\d", sec["section_title"])
            and not re.search(r"sub-?section|clause|proviso|illustration|explanation|\(\d+\)|\([a-z]\)", q, re.I)
        )
        refusal = eligible and rng.random() < a.refusal_frac
        if refusal:
            docs = noise
            topic = sec["section_title"].strip().rstrip(".").lower()
            ans = (
                f'I do not have any laws or provisions related to {topic} in my statutory database. '
                f"The retrieved sections deal with other subjects, so I cannot answer this question from the provided context."
            )
        else:
            docs = [sec] + noise
            rng.shuffle(docs)
            code = act
            ans = f"{body}\n\nSource: {ACT_DISPLAY[code]} Section {sec['section_number']}"
        parts = []
        for i, d in enumerate(docs, 1):
            code = d["chunk_id"].split("_")[0]
            parts.append(
                context_header(i, code, d["section_number"], d["section_title"], d["chapter"])
                + "\n" + clean_body(d["text"])
            )
        ctx = "\n\n".join(parts)
        if detect_query_language(q) != "english":
            drops["not_english_query"] += 1
            continue
        sp = system_prompt(q, ctx)
        if approx_tokens(sp) + 400 > a.max_tokens:
            drops["too_long"] += 1
            continue
        ex = chat(sp, q, ans, {
            "source": "GSMS-B/Indian-Legal-QA-BNS-BNSS-BSA", "license": "Apache-2.0",
            "kind": "refusal" if refusal else "grounded_qa", "lang": "english",
            "act": act, "section": sec["section_number"], "qtype": r["question_type"],
        })
        (test if stable_split(r["chunk_id"], a.test_frac) == "test" else train).append(ex)

    rng.shuffle(train)
    write_jsonl(OUT / "gsmsb_qa_train.jsonl", train)
    write_jsonl(OUT / "gsmsb_qa_test.jsonl", test)
    print(f"train={len(train)} test={len(test)} (split by section, no leakage)")
    print("by kind:", Counter(e['meta']['kind'] for e in train + test))
    print("by act :", Counter(e['meta']['act'] for e in train + test))
    print("by type:", Counter(e['meta']['qtype'] for e in train + test))
    print("dropped:", dict(drops))


if __name__ == "__main__":
    main()
