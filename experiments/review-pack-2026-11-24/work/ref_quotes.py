"""Check every double-quoted span of each link-set reference_answer against A/B unit texts and their ancestors' texts."""
import csv, json, re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[3]
B = ROOT / "data/normalized/experiment-scope-v3-v48feefc6d53b"
units = {}
for l in open(B / "units.jsonl", encoding="utf-8"):
    u = json.loads(l); units[u["unit_id"]] = u
D = ROOT / "experiments/runs/link-set-2026-11-23"
qs = json.load(open(D / "questions.json", encoding="utf-8"))["questions"]
def anc(uid):
    out = []; cur = units.get(uid)
    while cur and cur.get("parent_id") in units:
        cur = units[cur["parent_id"]]; out.append(cur["unit_id"])
    return out
for q in qs:
    gold = q["relevant_unit_ids"]
    for quote in re.findall(r'"([^"]+)"', q["reference_answer"]):
        where = [g for g in gold if quote in units[g]["text"]]
        if where:
            continue
        lead = [(g, a) for g in gold for a in anc(g) if quote in units[a]["text"]]
        if lead:
            print(q["question_id"], "LEAD", quote[:90], "->", lead[0][1])
        else:
            print(q["question_id"], "MISSING", quote[:120])
