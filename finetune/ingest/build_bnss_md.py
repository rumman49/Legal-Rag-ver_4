"""Build a BNSS 2023 Markdown file for the app's /api/documents/upload.

Source text: GSMS-B/indian-legal-sections-bns-bnss-bsa-2023 (Apache-2.0).
Old-law cross-reference: GSMS-B old/new mapping (CC-BY-4.0), added only where the
mapping's BNSS title agrees with the section's own title.

Run:  python finetune/ingest/build_bnss_md.py   -> finetune/ingest/bnss_2023.md
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "importers"))
from common import *  # noqa

ACT = ACT_DISPLAY["BNSS"]


def words(t):
    return set(re.findall(r"[a-z]{3,}", t.lower())) - {"the", "and", "for", "certain", "power", "other", "any"}


def agrees(a, b):
    A, B = words(a), words(b)
    return len(A & B) / max(1, min(len(A), len(B))) >= 0.5


def main():
    secs = [s for s in load_json(SEC_REPO, "bns_bnss_bsa_sections.json") if s["chunk_id"].startswith("BNSS_")]
    xwalk = {}
    for r in load_json(MAP_REPO, "bnss_to_crpc.json"):
        t = r["target"]
        if t and not t["sub_section"] and not r["source"]["sub_section"] and r["status"] != "New Section":
            xwalk[r["source"]["section"]] = (t["section"], r["source"]["title"])

    def key(s):
        m = re.match(r"(\d+)([A-Za-z]*)", s["section_number"])
        return int(m[1]), m[2]

    secs.sort(key=key)
    out = [
        "---", f"act_name: {ACT}", "act_year: 2023", "---", "",
        f"# {ACT}", "",
        "Replaces the Code of Criminal Procedure, 1973 (CrPC) with effect from 1 July 2024.", "",
    ]
    chapter, n_x = None, 0
    for s in secs:
        if s["chapter"] != chapter:
            chapter = s["chapter"]
            out += [f"## {chapter}", ""]
        out.append(f"### Section {s['section_number']} {s['section_title'].strip().rstrip('.')}")
        x = xwalk.get(s["section_number"])
        if x and agrees(x[1], s["section_title"]):
            out.append(f"Corresponds to Section {x[0]} of CrPC (Code of Criminal Procedure, 1973).")
            n_x += 1
        out += ["", clean_body(s["text"]), ""]
    dest = Path(__file__).with_name("bnss_2023.md")
    dest.write_text("\n".join(out), encoding="utf-8")
    print(f"{len(secs)} sections, {n_x} with CrPC cross-reference -> {dest} ({dest.stat().st_size//1024} KB)")


main()
