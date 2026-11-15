"""Validate the model review of the case scenario set on corpus v3 (15/11/2026): `cases.jsonl` in this folder.

These are MODEL REVIEW labels (a Claude agent compared every unit with the corpus v3 text and the case research in
`experiments/case-research-v1/`), not human labels and not verified law.

Record format (one JSON object per line, one per question of the source set): the fields of the 12/11 review
(`question_id`, `question_type`, `expected_status`, `relevant_unit_ids`, `kept`, `dropped`, `added` with `unit_id`,
`reason`, `quote` and, for a rule restated in a second document, `restates` with the other `unit_id` and its `quote`,
`outside_corpus`, `confidence`, `note`) plus `case_id`, `excluded`, `as_of` (ISO date of the event, or null when the
law the court applied predates every corpus document for the issue) and `as_of_source`, `checked_at` (the date the
status check uses: `as_of`, or the corpus v3 lock date 2026-11-11 when `as_of` is null), `issues` (the question's
issues that remain) and `issues_dropped` (`issue`, `reason`), `stale_unit_ids` (12/11 units not in force at
`checked_at`), `basis` (one entry or more per answer unit: `unit_id`, `source_basis` = what the court or source relied
on, `quote` from the unit), `changed_from_2026_11_12` and `previous_review` (the 12/11 unit list).

Checks (fail loudly, exit 1): every question of the source set appears exactly once; excluded records are exactly the
nine questions of the 15/11 decision; every unit ID exists in the v3 bundle; every quote is an exact substring of its
unit; non-excluded answer records have at least one unit (also after dropping ancestors of listed units); every answer
unit is `in_force` at `checked_at` according to `legal_ai.kb.validity` with the amendment edges of corpus v3;
`stale_unit_ids` are exactly the 12/11 units not in force at that date; `kept`/`dropped`/`added` agree with
`relevant_unit_ids` and the 12/11 baseline; `issues` plus `issues_dropped` equal the draft issues; every answer unit has
a `basis` entry; question types are the app's; no em dash.

The unit status comes from `src/legal_ai/kb/validity.py` as it is when this script runs; the printed status version
and the per-record `checked_at` let the result be re-validated after that module changes.

Usage: python check-cases.py  (from the repository root or this folder)
"""

from collections import Counter
from datetime import date
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from legal_ai.kb.validity import STATUS_VERSION, Validity  # noqa: E402
from legal_ai.research.questions import QUESTION_TYPES  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BUNDLE = ROOT / "data/normalized/experiment-scope-v3-v48feefc6d53b"
EDGES = ROOT / "data/kb/amendments-scope-v3-v48feefc6d53b-v2/edges.jsonl"
SOURCE = ROOT / "experiments/runs/dryrun-cases-v1/questions.json"
DRAFTS = ROOT / "experiments/question-drafts-cases-v1/drafts.json"
PREVIOUS = ROOT / "experiments/label-review-2026-11-12/cases.jsonl"
RECORDS = HERE / "cases.jsonl"
EXCLUDED = {"k01", "k09", "k15", "k17", "k24", "k25", "k26", "k40", "k41"}
LOCK_DATE = "2026-11-11"
TYPE_ALIASES = {"validity": "temporal"}
REQUIRED = ("question_id", "case_id", "question_type", "expected_status", "excluded", "relevant_unit_ids", "kept", "dropped",
            "added", "outside_corpus", "confidence", "note", "as_of", "as_of_source", "checked_at", "issues", "issues_dropped",
            "stale_unit_ids", "basis", "changed_from_2026_11_12", "previous_review")
EM_DASH = chr(0x2014)


def load(path):
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def minimal(unit_ids):
    ids = list(dict.fromkeys(unit_ids))
    return [u for u in ids if not any(o != u and o.startswith(u + "/") for o in ids)]


def main():
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    units = {u["unit_id"]: u for u in load(BUNDLE / "units.jsonl")}
    validity = Validity(load(BUNDLE / "documents.jsonl"), list(units.values()), load(EDGES))
    questions = json.loads(SOURCE.read_text(encoding="utf-8"))["questions"]
    drafts = {d["text"]: d for d in json.loads(DRAFTS.read_text(encoding="utf-8"))}
    previous = {r["question_id"]: r for r in load(PREVIOUS)}
    records = load(RECORDS)

    counts = Counter(r.get("question_id") for r in records)
    source_ids = [q["question_id"] for q in questions]
    check(len(records) == len(source_ids), f"{len(records)} records for {len(source_ids)} questions")
    for qid in source_ids:
        check(counts[qid] == 1, f"{qid}: appears {counts[qid]} times")
    for qid in counts:
        check(qid in set(source_ids), f"{qid}: not a question of the source set")
    excluded = {r["question_id"] for r in records if r.get("excluded")}
    check(excluded == EXCLUDED, f"excluded records {sorted(excluded)} differ from the 15/11 decision {sorted(EXCLUDED)}")

    by_id = {r["question_id"]: r for r in records}
    stats = Counter()
    for q in questions:
        qid = q["question_id"]
        r = by_id.get(qid)
        if r is None:
            continue
        missing = [f for f in REQUIRED if f not in r]
        check(not missing, f"{qid}: missing fields {missing}")
        if missing:
            continue
        check(EM_DASH not in json.dumps(r, ensure_ascii=False), f"{qid}: contains an em dash")
        check(r["case_id"] == q["case_id"], f"{qid}: case_id {r['case_id']} is not {q['case_id']}")
        qtype = TYPE_ALIASES.get(r["question_type"], r["question_type"])
        check(qtype in QUESTION_TYPES, f"{qid}: question type {qtype}")
        check(r["confidence"] in ("high", "medium", "low"), f"{qid}: confidence {r['confidence']}")
        check(r["previous_review"] == previous[qid]["relevant_unit_ids"], f"{qid}: previous_review is not the 12/11 unit list")
        draft = drafts.get(q["question"])
        check(draft is not None, f"{qid}: no draft with the same text")
        if r["excluded"]:
            check(not r["relevant_unit_ids"] and not r["added"] and not r["basis"], f"{qid}: excluded record lists units")
            check(r["note"].strip() != "", f"{qid}: excluded record without a reason")
            stats["excluded"] += 1
            continue
        if draft is not None:
            dropped_issues = [i["issue"] for i in r["issues_dropped"]]
            check(all(i.get("reason", "").strip() for i in r["issues_dropped"]), f"{qid}: dropped issue without a reason")
            check(sorted(r["issues"] + dropped_issues) == sorted(draft["issues"]), f"{qid}: issues and issues_dropped do not equal the draft issues")
            check(r["issues"], f"{qid}: no issue left")
        final = r["relevant_unit_ids"]
        prev_ids = r["previous_review"]
        # existence and quotes
        listed = set(final) | set(prev_ids) | set(r["kept"]) | {d["unit_id"] for d in r["dropped"]} | {a["unit_id"] for a in r["added"]} \
            | {b["unit_id"] for b in r["basis"]} | set(r["stale_unit_ids"]) | {a["restates"]["unit_id"] for a in r["added"] if "restates" in a}
        for unit in sorted(listed):
            check(unit in units, f"{qid}: unknown unit {unit}")
        for item in r["added"] + r["basis"] + [a["restates"] for a in r["added"] if "restates" in a]:
            if item["unit_id"] in units:
                check(bool(item.get("quote")) and item["quote"] in units[item["unit_id"]]["text"],
                      f"{qid}: quote not an exact substring of {item['unit_id']}")
        for item in r["added"]:
            check(item.get("reason", "").strip() != "", f"{qid}: added {item['unit_id']} without a reason")
        for item in r["dropped"]:
            check(item.get("reason", "").strip() != "", f"{qid}: dropped {item['unit_id']} without a reason")
        # status and units
        check(r["expected_status"] == "answer", f"{qid}: expected_status {r['expected_status']}")
        check(len(minimal(final)) >= 1, f"{qid}: answer record without units")
        check(len(final) == len(set(final)), f"{qid}: duplicate units")
        check(r["as_of"] is None or date.fromisoformat(r["as_of"]).isoformat() == r["as_of"], f"{qid}: as_of {r['as_of']} is not an ISO date")
        check(r["checked_at"] == (r["as_of"] or LOCK_DATE), f"{qid}: checked_at {r['checked_at']} should be {r['as_of'] or LOCK_DATE}")
        check(r["as_of_source"].strip() != "", f"{qid}: as_of_source is empty")
        at = r["as_of"] or LOCK_DATE
        for unit in final:
            if unit in units:
                status = validity.status(unit, at)
                check(status == "in_force", f"{qid}: {unit} is {status} at {at}")
        stale = [u for u in prev_ids if u in units and validity.status(u, at) != "in_force"]
        check(sorted(r["stale_unit_ids"]) == sorted(stale), f"{qid}: stale_unit_ids {r['stale_unit_ids']} should be {stale}")
        # bookkeeping against the 12/11 baseline
        check(r["kept"] == [u for u in final if u in prev_ids], f"{qid}: kept does not match relevant_unit_ids and the 12/11 list")
        check(sorted(d["unit_id"] for d in r["dropped"]) == sorted(set(prev_ids) - set(final)), f"{qid}: dropped does not match")
        check(sorted(a["unit_id"] for a in r["added"]) == sorted(set(final) - set(prev_ids)), f"{qid}: added does not match")
        based = {b["unit_id"] for b in r["basis"]}
        check(based == set(final), f"{qid}: basis covers {sorted(based ^ set(final))} wrongly")
        stats["answer"] += 1
        stats["units"] += len(final)
        stats["kept"] += len(r["kept"])
        stats["dropped"] += len(r["dropped"])
        stats["added"] += len(r["added"])
        stats["issues_dropped"] += len(r["issues_dropped"])
        stats["unchanged"] += sorted(final) == sorted(prev_ids)
        stats["as_of_null"] += r["as_of"] is None
        stats["confidence_" + r["confidence"]] += 1

    print(f"unit status: {STATUS_VERSION} ({len(validity.edges)} edge targets, {validity.undated} undated edges ignored)")
    print(json.dumps(dict(sorted(stats.items())), ensure_ascii=False))
    if errors:
        print(f"FAILED: {len(errors)} problem(s)")
        for message in errors:
            print(" -", message)
        sys.exit(1)
    print(f"OK: {len(records)} records checked")


if __name__ == "__main__":
    main()
