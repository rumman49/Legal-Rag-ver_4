"""Importer 2: GSMS-B old<->new law mapping (CC-BY-4.0) -> RAG-format chat examples.

Old->new (IPC->BNS, CrPC->BNSS, IEA->BSA) and new->old questions in English,
Hinglish (Roman) and Hindi (Devanagari).  Context = the real text of the new-law
section (GSMS-B sections dataset); the transition block uses the app's exact
format.  Answers are templated from the mapping row + the section text, and are
number-checked against the prompt.  Rows whose target is a sub-section, whose
text is missing, or whose section is too long are skipped.

NOTE: CrPC<->BNSS examples assume the BNSS text is in the retriever's store.  The
app does not ingest BNSS today (see CLAUDE.md); they are tagged
meta.needs_bnss_in_store so you can leave them out until it is ingested.

Run:  python finetune/importers/gsmsb_mapping.py
"""
from __future__ import annotations

import argparse
import hashlib
import random
import re
from collections import Counter, defaultdict

from common import *

# (file, old act code, new act code, old display, new display)
PAIRS = [
    ("ipc_to_bns.json", "IPC", "BNS"),
    ("crpc_to_bnss.json", "CrPC", "BNSS"),
    ("iea_to_bsa.json", "IEA", "BSA"),
]
SHORT_DEVA = {"IPC": "आईपीसी", "CrPC": "सीआरपीसी", "IEA": "भारतीय साक्ष्य अधिनियम", "BNS": "बीएनएस", "BNSS": "बीएनएसएस", "BSA": "बीएसए"}
OLD_FULL = {"IPC": "Indian Penal Code, 1860", "CrPC": "Code of Criminal Procedure, 1973", "IEA": "Indian Evidence Act, 1872"}

PREAMBLE = (
    "=== STATUTORY TRANSITION MAPPING (CURRENT LAW VS REPLACED LAW) ===\n"
    "IMPORTANT LEGAL NOTICE ON APPLICABLE LAW:\n"
    "India replaced IPC 1860, CrPC 1973, and IEA 1872 with Bharatiya Nyaya Sanhita 2023 (BNS), "
    "Bharatiya Nagarik Suraksha Sanhita 2023 (BNSS), and Bharatiya Sakshya Adhiniyam 2023 (BSA), "
    "which came into full force on July 1, 2024.\n"
    "- Offenses committed ON OR AFTER July 1, 2024 MUST be charged under the NEW LAWS (BNS/BNSS/BSA).\n"
    "- Offenses committed PRIOR TO July 1, 2024 continue under the OLD LAWS (IPC/CrPC/IEA).\n\n"
    "Applicable Mappings for this Query:\n"
)
POSTAMBLE = "\n\nWhen providing the legal explanation, explain BOTH the Current Law (BNS/BNSS) and the former law (IPC/CrPC) so the user has complete legal clarity."


def assert_matches_app():
    """Fail loudly if the app's transition-block wording changed since this file was written."""
    src = (REPO / "backend/app/rag/law_mapping_service.py").read_text(encoding="utf-8")
    for frag in ("STATUTORY TRANSITION MAPPING", "Applicable Mappings for this Query:", "is replaced by **BNS Section",
                 "corresponds to former **IPC Section", "explain BOTH the Current Law"):
        assert frag in src, f"app transition wording changed ({frag!r}); update PREAMBLE in gsmsb_mapping.py"


def block(line: str) -> str:
    return PREAMBLE + line + POSTAMBLE


def opening(body: str, lo=120, hi=320) -> str:
    """First operative words of a section, heading stripped, cut at a sentence/clause end."""
    t = re.sub(r"^\s*\d+[A-Za-z]*\.\s.{0,200}?[—–]{1,2}", "", body, count=1, flags=re.S).strip() or body
    t = re.sub(r"\s+", " ", t)
    if len(t) <= hi:
        return t
    cut = max(t.rfind(".", lo, hi), t.rfind(";", lo, hi))
    return t[: cut + 1] if cut > 0 else t[:hi].rsplit(" ", 1)[0] + " …"


# ----------------------------------------------------------------------- questions
def question(lang, direction, o, n, os_, ns, rng):
    if direction == "old2new":
        T = {
            "english": [f"What is {o} section {os_} in the {n}?", f"Which {n} section replaced {o} section {os_}?",
                        f"{o} {os_} corresponds to which section of the {n}?"],
            "hinglish": [f"{o} ki dhara {os_} ab {n} mein kaunsi dhara hai?", f"{o} section {os_} ka naya {n} section kya hai?",
                         f"{o} {os_} ko {n} mein kis dhara se badla gaya hai?"],
            "hindi": [f"{SHORT_DEVA[o]} की धारा {os_} अब {SHORT_DEVA[n]} में कौन सी धारा है?",
                      f"{SHORT_DEVA[o]} की धारा {os_} की जगह {SHORT_DEVA[n]} की कौन सी धारा आई?"],
        }
    else:
        T = {
            "english": [f"{n} section {ns} was which {o} section earlier?", f"Which {o} section does {n} section {ns} correspond to?"],
            "hinglish": [f"{n} ki dhara {ns} pehle {o} ki kaunsi dhara thi, kya aap bata sakte hain?", f"{n} section {ns} purane {o} mein kya tha?"],
            "hindi": [f"{SHORT_DEVA[n]} की धारा {ns} पहले {SHORT_DEVA[o]} की कौन सी धारा थी?",
                      f"{SHORT_DEVA[n]} की धारा {ns} {SHORT_DEVA[o]} की किस धारा के अनुरूप है?"],
        }
    return rng.choice(T[lang])


# ----------------------------------------------------------------------- answers
def heads(lang):
    if lang == "hinglish":
        return ["Kanooni Sthiti aur Dharaayein (Legal Provisions)", "Saza aur Jurmana (Penalties & Provisions)",
                "Turant Kya Kadam Uthane Chahiye (Crucial Practical Steps)", "Saral Sankshep (Summary)"]
    return ["कानूनी स्थिति और धाराएं (Legal Provisions)", "सजा और प्रावधान (Penalties & Provisions)",
            "तुरंत क्या कदम उठाने चाहिए (Actionable Steps)", "सरल संक्षेप (Summary)"]


def answer(lang, direction, kind, o, n, os_, ot, ns, nt, status, quote, new_full):
    """kind: 'map' (has counterpart) | 'new_section' (no old counterpart)."""
    changed = status == "Change"
    if lang == "english":
        if kind == "new_section":
            return (f"{n} Section {ns} ({nt}) is a newly introduced provision with no direct counterpart in the {OLD_FULL[o]}.\n\n"
                    f"The retrieved text reads: \"{quote}\"\n\n"
                    f"Because this is a new provision, offences on or after 1 July 2024 are dealt with under it; it has no former {o} section to compare.\n\n"
                    f"Source: {new_full} Section {ns}")
        if direction == "old2new":
            lead = f"{o} Section {os_} ({ot}) is replaced by {n} Section {ns} ({nt})."
        else:
            lead = f"{n} Section {ns} ({nt}) corresponds to the former {o} Section {os_} ({ot})."
        amend = (f" The mapping marks this provision as changed in the new law, so read the {n} wording below rather than assuming it is identical to the old one."
                 if changed else "")
        return (f"{lead}{amend}\n\nThe retrieved {n} text reads: \"{quote}\"\n\n"
                f"Since 1 July 2024 the {n} applies to offences committed on or after that date, while the {o} continues for earlier offences.\n\n"
                f"Source: {new_full} Section {ns}")
    if lang == "hinglish":
        H = heads(lang)
        if kind == "new_section":
            leg = f"{n} Section {ns} ({nt}) ek naya prawadhan hai; {o} mein iska koi seedha samaan section nahi hai. Context ke anusaar: \"{quote}\""
            sm = f"{n} Section {ns} naya hai aur {o} mein iska koi counterpart nahi hai."
        else:
            if direction == "old2new":
                leg = f"{o} Section {os_} ({ot}) ki jagah ab {n} Section {ns} ({nt}) hai."
            else:
                leg = f"{n} Section {ns} ({nt}) pehle {o} ki Section {os_} ({ot}) thi."
            if changed:
                leg += " Mapping ke mutabik is prawadhan mein badlaav hua hai, isliye naye shabd dhyan se padhein."
            leg += f" Context ke anusaar {n} ka paath: \"{quote}\""
            sm = f"{o} {os_} ka naya roop {n} {ns} hai." if direction == "old2new" else f"{n} {ns} pehle {o} {os_} thi."
        return (f"### {H[0]}\n{leg}\n\n### {H[1]}\nIs sawal mein saza nahi poochi gayi hai; saza ke liye upar diye gaye {n} Section {ns} ka paath dekhein.\n\n"
                f"### {H[2]}\n1 July 2024 ya uske baad hue apradh par {n} lagu hota hai, aur usse pehle ke apradh par {o}. Apne case ki tareekh dekh kar sahi kanoon chunein.\n\n"
                f"### {H[3]}\n{sm}\n\nSource: {new_full} Section {ns}")
    # hindi: Devanagari only (no English titles/quotes)
    H = heads(lang)
    O, N = SHORT_DEVA[o], SHORT_DEVA[n]
    if kind == "new_section":
        leg = f"{N} की धारा {ns} एक नया प्रावधान है; {O} में इसका कोई सीधा समकक्ष नहीं है।"
        sm = f"{N} की धारा {ns} नई है और {O} में इसका कोई समकक्ष नहीं है।"
    else:
        if direction == "old2new":
            leg = f"{O} की धारा {os_} की जगह अब {N} की धारा {ns} है।"
            sm = f"{O} की धारा {os_} का नया रूप {N} की धारा {ns} है।"
        else:
            leg = f"{N} की धारा {ns} पहले {O} की धारा {os_} थी।"
            sm = f"{N} की धारा {ns} पहले {O} की धारा {os_} थी।"
        if changed:
            leg += " मैपिंग के अनुसार इस प्रावधान में बदलाव हुआ है, इसलिए नए शब्दों को ध्यान से पढ़ें।"
    return (f"### {H[0]}\n{leg}\n\n### {H[1]}\nइस प्रश्न में सजा नहीं पूछी गई है; सजा के लिए संदर्भ में दी गई {N} की धारा {ns} का पाठ देखें।\n\n"
            f"### {H[2]}\n1 जुलाई 2024 या उसके बाद हुए अपराध पर {N} लागू होता है और उससे पहले के अपराध पर {O}। अपने मामले की तारीख देखकर सही कानून चुनें।\n\n"
            f"### {H[3]}\n{sm}")


def check(lang, ans, prompt):
    body = re.sub(r"^### .*$", "", ans, flags=re.M)  # the app's own headings carry English glosses
    if lang == "hindi" and re.search(r"[A-Za-z]", body):
        return "latin_in_hindi"
    if lang != "hindi" and re.search(r"[ऀ-ॿ]", ans):
        return "devanagari_in_non_hindi"
    if lang != "english" and not all(h in ans for h in heads(lang)):
        return "missing_heading"
    if numbers(ans) - numbers(prompt):
        return "number_not_in_prompt"
    if CASE_LAW.search(ans):
        return "case_law"
    return None


def _words(t):
    return set(re.findall(r"[a-z]{3,}", t.lower())) - {"the", "and", "for", "certain", "power", "other", "any"}


def title_agrees(map_title, sec):
    """GSMS-B's mapping and sections files are separate; keep a row only if both name the same section."""
    if not sec:
        return True  # handled by the missing-text drop
    A, B = _words(map_title), _words(sec["section_title"])
    return len(A & B) / max(1, min(len(A), len(B))) >= 0.5


def split_of(key, frac):
    return "test" if int(hashlib.md5(key.encode()).hexdigest(), 16) % 1000 < frac * 1000 else "train"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-frac", type=float, default=0.08)
    ap.add_argument("--max-tokens", type=int, default=5500)
    ap.add_argument("--noise", type=int, default=1)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--no-bnss", action="store_true", help="skip CrPC<->BNSS (BNSS not in the app's store yet)")
    a = ap.parse_args()
    assert_matches_app()
    rng = random.Random(a.seed)
    secs = {s["chunk_id"]: s for s in load_json(SEC_REPO, "bns_bnss_bsa_sections.json")}
    pool = [s for s in secs.values() if len(s["text"]) < 3000]
    langs, wts = ["english", "hinglish", "hindi"], [0.4, 0.35, 0.25]

    train, test, deleted, drops = [], [], [], Counter()

    def build(lang, direction, kind, o, n, row_src, row_tgt, status, split_key, bnss, deleted_row=False):
        old_row, new_row = (row_src, row_tgt) if direction == "old2new" else (row_tgt, row_src)
        os_, ot, ns, nt = old_row["section"], old_row["title"], new_row["section"], new_row["title"]
        if not title_agrees(nt, secs.get(f"{n}_{ns}")):
            drops["title_disagrees_with_sections_file"] += 1
            return
        sec = secs.get(f"{n}_{ns}")
        if not sec or len(sec["text"]) > 6000:
            drops["no_or_long_text"] += 1
            return
        quote = opening(clean_body(sec["text"]))
        q = question(lang, direction, o, n, os_, ns, rng)
        if detect_query_language(q) != lang:
            drops["lang_detect_mismatch"] += 1
            return
        if kind == "new_section":
            line = f"- **Section Transition**: {n} Section {ns} ('{nt}') is a newly introduced provision with no direct counterpart in {OLD_FULL[o]}."
        elif direction == "old2new":
            line = f"- **Section Transition**: {o} Section {os_} ('{ot}') is replaced by **{n} Section {ns}** ('{nt}')."
        else:
            line = f"- **Section Transition**: {n} Section {ns} ('{nt}') corresponds to former **{o} Section {os_}** ('{ot}')."
        noise = [c for c in rng.sample(pool, 6) if c["chunk_id"] != sec["chunk_id"]][: a.noise]
        docs = [sec] + noise
        rng.shuffle(docs)
        ctx = "\n\n".join(
            context_header(i, d["chunk_id"].split("_")[0], d["section_number"], d["section_title"], d["chapter"]) + "\n" + clean_body(d["text"])
            for i, d in enumerate(docs, 1)
        )
        sp = system_prompt(q, ctx, block(line))
        if approx_tokens(sp) + 500 > a.max_tokens:
            drops["too_long"] += 1
            return
        ans = answer(lang, direction, kind, o, n, os_, ot, ns, nt, status, quote, ACT_DISPLAY[n])
        why = check(lang, ans, sp + q)
        if why:
            drops[why] += 1
            return
        ex = chat(sp, q, ans, {"source": "GSMS-B old-new mapping", "license": "CC-BY-4.0", "kind": f"mapping_{direction}_{kind}",
                               "lang": lang, "pair": f"{o}->{n}", "status": status, "needs_bnss_in_store": bnss})
        (test if split_of(sec["chunk_id"], a.test_frac) == "test" else train).append(ex)

    for fname, o, n in PAIRS:
        if a.no_bnss and n == "BNSS":
            continue
        rows = load_json(MAP_REPO, fname)
        by_new = defaultdict(set)  # new section -> distinct OLD sections mapping into it (sub-sections included)
        for r in rows:
            if r["target"]:
                by_new[r["target"]["section"]].add(r["source"]["section"])
        for r in rows:
            if r["status"] == "Deleted":
                deleted.append((o, n, r))
                continue
            t = r["target"]
            if not t or t["sub_section"] or r["source"]["sub_section"]:
                drops["sub_section"] += 1
                continue
            bnss = n == "BNSS"
            build(rng.choices(langs, wts)[0], "old2new", "map", o, n, r["source"], t, r["status"], "", bnss)
            if len(by_new[t["section"]]) == 1:  # reverse only when unambiguous
                # new2old: row_src is the NEW-law row, row_tgt the OLD-law row
                build(rng.choices(langs, wts)[0], "new2old", "map", o, n, t, r["source"], r["status"], "", bnss)
    if not a.no_bnss:  # BNSS rows with no CrPC counterpart
        for r in load_json(MAP_REPO, "bnss_to_crpc.json"):
            if r["status"] == "New Section" and not r["source"]["sub_section"]:
                build(rng.choices(langs, wts)[0], "new2old", "new_section", "CrPC", "BNSS",
                      {"section": r["source"]["section"], "title": r["source"]["title"]}, {"section": "-", "title": "-"}, "New Section", "", True)

    rng.shuffle(train)
    write_jsonl(OUT / "gsmsb_mapping_train.jsonl", train)
    write_jsonl(OUT / "gsmsb_mapping_test.jsonl", test)
    print(f"train={len(train)} test={len(test)}; deleted-rows not used (see below)={len(deleted)}")
    print("by kind:", Counter(e['meta']['kind'] for e in train + test))
    print("by lang:", Counter(e['meta']['lang'] for e in train + test))
    print("by pair:", Counter(e['meta']['pair'] for e in train + test))
    print("dropped:", dict(drops))


if __name__ == "__main__":
    main()
