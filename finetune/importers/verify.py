"""Independent verifier: re-reads the generated mapping examples and checks each
transition line against the RAW GSMS-B mapping files, and that the context really
contains the new-law section named.  Also re-checks QA examples against the sections file."""
import json, re, sys
from common import *

def main():
    maps = {}
    for f, o, n in [("ipc_to_bns.json", "IPC", "BNS"), ("crpc_to_bnss.json", "CrPC", "BNSS"), ("iea_to_bsa.json", "IEA", "BSA")]:
        for r in load_json(MAP_REPO, f):
            if r["target"] and not r["target"]["sub_section"] and not r["source"]["sub_section"]:
                maps[(o, r["source"]["section"], n, r["target"]["section"])] = r["status"]
    new_secs = {r["source"]["section"] for r in load_json(MAP_REPO, "bnss_to_crpc.json") if r["status"] == "New Section"}
    bad = 0; n_ok = 0
    for split in ("train", "test"):
        for line in open(OUT / f"gsmsb_mapping_{split}.jsonl", encoding="utf-8"):
            e = json.loads(line); sp = e["messages"][0]["content"]
            m = re.search(r"- \*\*Section Transition\*\*: (\w+) Section (\S+) \('.*?'\) is replaced by \*\*(\w+) Section (\S+)\*\*", sp)
            m2 = re.search(r"- \*\*Section Transition\*\*: (\w+) Section (\S+) \('.*?'\) corresponds to former \*\*(\w+) Section (\S+)\*\*", sp)
            m3 = re.search(r"- \*\*Section Transition\*\*: (\w+) Section (\S+) \('.*?'\) is a newly introduced", sp)
            if m:   key, new_no, new_act = (m[1], m[2], m[3], m[4]), m[4], m[3]
            elif m2: key, new_no, new_act = (m2[3], m2[4], m2[1], m2[2]), m2[2], m2[1]
            elif m3: key, new_no, new_act = None, m3[2], m3[1]
            else: bad += 1; print("NO LINE", e["meta"]); continue
            ok = (key in maps) if key else (new_no in new_secs)
            if key and maps.get(key) != e["meta"]["status"]: ok = False
            hdr = re.search(rf"Provision: {re.escape(new_no)} ", sp)  # new-law section really in context
            ans = e["messages"][2]["content"]
            if not (ok and hdr and new_no in ans):
                bad += 1; print("MISMATCH", key, new_no, e["meta"])
            else: n_ok += 1
    print(f"mapping examples verified: {n_ok} ok, {bad} bad")
    secs = {s["chunk_id"]: s for s in load_json(SEC_REPO, "bns_bnss_bsa_sections.json")}
    qbad = qok = 0
    for split in ("train", "test"):
        for line in open(OUT / f"gsmsb_qa_{split}.jsonl", encoding="utf-8"):
            e = json.loads(line); mt = e["meta"]; sp = e["messages"][0]["content"]
            sec = secs[f"{mt['act']}_{mt['section']}"]
            present = clean_body(sec["text"])[:200] in sp
            if mt["kind"] == "grounded_qa" and not present: qbad += 1; print("QA target missing", mt)
            elif mt["kind"] == "refusal" and present: qbad += 1; print("REFUSAL leaks target", mt)
            elif numbers(e["messages"][2]["content"]) - numbers(sp + e["messages"][1]["content"]): qbad += 1; print("QA number", mt)
            else: qok += 1
    print(f"QA examples verified: {qok} ok, {qbad} bad")
    sys.exit(1 if bad or qbad else 0)

main()
