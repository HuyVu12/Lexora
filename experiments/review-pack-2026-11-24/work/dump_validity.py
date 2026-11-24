"""Dump the validity check sheet per question with an independent status recomputation (unit-status-v2)."""
import csv, json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from legal_ai.kb.validity import Validity
B = ROOT / "data/normalized/experiment-scope-v3-v48feefc6d53b"
docs = [json.loads(l) for l in open(B / "documents.jsonl", encoding="utf-8")]
units = [json.loads(l) for l in open(B / "units.jsonl", encoding="utf-8")]
edges = [json.loads(l) for l in open(ROOT / "data/kb/amendments-scope-v3-v48feefc6d53b-v2/edges.jsonl", encoding="utf-8")]
v = Validity(docs, units, edges)
rows = list(csv.DictReader(open(ROOT / "experiments/question-drafts-validity-v1/check-sheet.csv", encoding="utf-8-sig")))
sel = sys.argv[1:] 
last = None
seen=set()
for i, r in enumerate(rows):
    if sel and not any(r["question_id"].startswith(s) for s in sel):
        continue
    if r["question_id"] != last:
        print("\n######", r["question_id"], r["group"], r["as_of"], "\nQ:", r["question"])
        last = r["question_id"]
    st = v.status(r["unit_id"], r["as_of"])
    print(f"--[{i}] {r['role']} | {r['unit_path']} | sheet={r['status_at_as_of']} recomputed={st}")
    print("   reason:", r["reason"])
    print("   quotes:", r["quotes"].replace("\n", " || "))
    print("   context:", r["context"].replace("\n", " || ")[:700])
    print("   text:", r["unit_text"][:1500] if r["unit_id"] not in seen else "(as above)")
    seen.add(r["unit_id"])
