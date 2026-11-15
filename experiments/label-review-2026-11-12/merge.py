"""Merge the model-review labels (12/11/2026) into reviewed question files and check sheets.

These are MODEL REVIEW labels (five Claude agents checked every draft unit against corpus v2), not human labels:
the two annotators label independently in the app and may use the check sheets as a reference.

Checks (fail loudly): every question of the source set is reviewed exactly once; every unit exists in corpus v2;
every added quote is an exact substring of its unit; answer rows have units and refuse rows none; question types
are the app's (`QUESTION_TYPES`).

One convention is applied uniformly here, because the agents differed on it: a unit is dropped from a gold list when
one of its descendants is also in the list. The descendant is the more precise basis, its DK2 record already carries
the ancestor's lead text, and the recall scorer counts an ancestor as covered by any descendant, so keeping both would
make a question easier for some systems than for others.

Usage: python merge.py  (from the repository root or this folder)
"""

import csv
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from legal_ai.research.questions import QUESTION_TYPES  # noqa: E402

UNITS = {json.loads(l)["unit_id"]: json.loads(l) for l in (ROOT / "data/normalized/experiment-scope-v2-ve5261858b8f3/units.jsonl").open(encoding="utf-8")}
SETS = {
    "cases": ("experiments/runs/dryrun-cases-v1/questions.json", ["cases.jsonl"]),
    "conflict": ("experiments/runs/dryrun-conflict-v1/questions.json", ["conflict.jsonl"]),
    "complex": ("experiments/runs/dryrun-complex-v1/questions.json", ["complex.jsonl"]),
    "lookup": ("experiments/runs/dryrun-v1/questions.json", ["lookup-part1.jsonl", "lookup-part2.jsonl"]),
}
TYPE_ALIASES = {"validity": "temporal"}


def minimal(unit_ids):
    """Drop every unit that has a descendant in the same list; keep order."""
    ids = list(dict.fromkeys(unit_ids))
    return [u for u in ids if not any(o != u and o.startswith(u + "/") for o in ids)]


def main():
    summary = {}
    for name, (source, parts) in SETS.items():
        questions = json.loads((ROOT / source).read_text(encoding="utf-8"))
        reviews = [json.loads(l) for p in parts for l in (HERE / p).open(encoding="utf-8")]
        by_id = {r["question_id"]: r for r in reviews}
        ids = [q["question_id"] for q in questions["questions"]]
        assert len(by_id) == len(reviews) and set(by_id) == set(ids), f"{name}: reviewed questions do not match the set"
        out, sheet, stats = [], [], {"questions": len(ids), "status_changed": 0, "ancestors_dropped": 0, "draft_units": 0, "final_units": 0,
                                     "same_as_draft": 0, "confidence": {}}
        for q in questions["questions"]:
            r = by_id[q["question_id"]]
            qtype = TYPE_ALIASES.get(r["question_type"], r["question_type"])
            assert qtype in QUESTION_TYPES, f"{q['question_id']}: question type {qtype}"
            for unit in r["relevant_unit_ids"]:
                assert unit in UNITS, f"{q['question_id']}: unknown unit {unit}"
            for item in r.get("added", []):
                assert item["quote"] in UNITS[item["unit_id"]]["text"], f"{q['question_id']}: quote not in {item['unit_id']}"
            final = minimal(r["relevant_unit_ids"])
            assert (r["expected_status"] == "answer") == bool(final), f"{q['question_id']}: status and units disagree"
            stats["ancestors_dropped"] += len(set(r["relevant_unit_ids"])) - len(final)
            stats["draft_units"] += len(q["relevant_unit_ids"])
            stats["final_units"] += len(final)
            stats["status_changed"] += r["expected_status"] != q.get("expected_status")
            stats["same_as_draft"] += sorted(final) == sorted(q["relevant_unit_ids"]) and r["expected_status"] == q.get("expected_status")
            stats["confidence"][r["confidence"]] = stats["confidence"].get(r["confidence"], 0) + 1
            out.append(q | {"question_type": qtype, "expected_status": r["expected_status"], "relevant_unit_ids": final,
                            "annotation_status": "model_review",
                            "model_review": {"date": "2026-11-12", "draft_unit_ids": q["relevant_unit_ids"], "draft_expected_status": q.get("expected_status"),
                                             "dropped": r.get("dropped", []), "added": r.get("added", []), "outside_corpus": r.get("outside_corpus", []),
                                             "confidence": r["confidence"], "note": r.get("note", ""),
                                             **({"reference_outcome_supported": r["reference_outcome_supported"]} if "reference_outcome_supported" in r else {})}})
            draft, added = set(q["relevant_unit_ids"]), {a["unit_id"]: a for a in r.get("added", [])}
            dropped = {d["unit_id"]: d for d in r.get("dropped", [])}
            for unit in sorted(draft | set(final) | set(dropped)):
                verdict = "giữ" if unit in draft and unit in final else "thêm" if unit in final else "bỏ"
                reason = (added.get(unit) or dropped.get(unit) or {}).get("reason", "")
                if unit in draft and unit not in final and unit not in dropped:
                    verdict, reason = "bỏ", "đã có đơn vị con chính xác hơn trong nhãn"
                sheet.append([q["question_id"], q["question"], r["expected_status"], r["confidence"], verdict, unit, reason,
                              UNITS[unit]["text"][:500] if unit in UNITS else "", r.get("note", ""), "", ""])
        (HERE / f"{name}-reviewed.json").write_text(json.dumps(questions | {
            "description": (questions.get("description") or "") + " | Model review 12/11/2026 (not human labels): see experiments/label-review-2026-11-12/README.md",
            "questions": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        with (HERE / f"{name}-check-sheet.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["question_id", "question", "expected_status", "confidence", "verdict", "unit_id", "reason", "unit_text", "note",
                             "annotator_agrees", "annotator_note"])
            writer.writerows(sheet)
        summary[name] = stats
    (HERE / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
