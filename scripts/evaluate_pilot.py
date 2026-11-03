"""Offline retrieval smoke on draft pilot questions, never formal test metrics."""

import argparse
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.common.io import digest, read_jsonl, write_json
from legal_ai.retrieval.bm25 import search
from legal_ai.validation.bundle import validate_bundle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    folder = Path(args.bundle)
    documents, units, evidence, claims = [read_jsonl(folder / f"{name}.jsonl") for name in ("documents", "units", "evidence", "claims")]
    validate_bundle(documents, units, evidence, claims)
    question_path = ROOT / "tests/fixtures/pilot-questions.json"
    questions = json.loads(question_path.read_text(encoding="utf-8"))["questions"]
    known = {unit["unit_id"] for unit in units}
    rows = []
    for question in questions:
        gold = set(question["relevant_unit_ids"])
        if not gold <= known:
            raise ValueError("pilot question references missing unit")
        found = search(units, question["question"], 5)
        retrieved = [row["unit_id"] for row in found]
        rows.append({"question_id": question["question_id"], "expected_status": question["expected_status"], "retrieved_unit_ids": retrieved, "recall_at_5": len(gold & set(retrieved)) / len(gold) if gold else None, "behavior_evaluated": False})
    scored = [row["recall_at_5"] for row in rows if row["recall_at_5"] is not None]
    report = {"status": "draft_pilot_smoke_only", "question_sha256": digest(question_path.read_bytes()), "unit_artifact_sha256": digest((folder / "units.jsonl").read_bytes()), "top_k": 5, "scored_questions": len(scored), "excluded_no_gold_questions": len(rows) - len(scored), "mean_recall_at_5": sum(scored) / len(scored) if scored else None, "limitations": ["Draft annotations not independent gold", "Tiny topic-specific pilot, no generalization claim", "Temporal refusal and out-of-scope behavior not implemented", "No generation or legal correctness score"], "rows": rows}
    write_json(args.output, report)
    print(json.dumps({key: report[key] for key in ("status", "scored_questions", "excluded_no_gold_questions", "mean_recall_at_5")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
