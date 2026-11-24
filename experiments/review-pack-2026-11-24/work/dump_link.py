"""Dump the link-dependent check sheet with question metadata and recomputed unit status at as_of (unit-status-v2)."""
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
D = ROOT / "experiments/runs/link-set-2026-11-23"
qs = {q["question_id"]: q for q in json.load(open(D / "questions.json", encoding="utf-8"))["questions"]}
rows = list(csv.DictReader(open(D / "check-sheet.csv", encoding="utf-8-sig")))
sel = sys.argv[1:]
for r in rows:
    qid = r["question_id"]
    if sel and qid not in sel:
        continue
    q = qs[qid]
    print("\n######", qid, "type", q.get("link_type"), "as_of", q.get("as_of"), "pair", q.get("source_pair"))
    print("Q:", r["question"])
    extra = {k: q[k] for k in q if k not in ("question_id", "question", "family_id", "split", "question_type", "link_type", "expected_status", "relevant_unit_ids", "link_target_unit_ids", "as_of", "as_of_source", "annotation_status", "drafted_by", "reference_answer", "source_pair")}
    if extra:
        print("EXTRA:", json.dumps(extra, ensure_ascii=False))
    for u in q["relevant_unit_ids"]:
        tag = "B" if u in q.get("link_target_unit_ids", []) else "A"
        print(f"  gold[{tag}] {u} status={v.status(u, q['as_of'])}")
    print("A_label:", r["A_label"])
    print("A_text:", r["A_text"])
    print("B_label:", r["B_label"])
    print("B_text:", r["B_text"])
    print("REF:", r["reference_answer"])
