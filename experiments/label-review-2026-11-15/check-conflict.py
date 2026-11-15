"""Validate the model review of the conflict/overlap set on corpus v3 (15/11/2026): `conflict.jsonl` in this folder.

These are MODEL REVIEW labels (a Claude agent compared every unit with the corpus v3 text), not human labels.

Record format (one JSON object per line, one per question of the source set): the fields of the 12/11 review
(`question_id`, `question_type`, `expected_status`, `relevant_unit_ids`, `kept`, `dropped`, `added` with `unit_id`,
`reason`, `quote`, `outside_corpus`, `reference_outcome_supported`, `confidence`, `note`) plus `as_of` (ISO date the
question is answered at) and `as_of_source`, `stale_unit_ids` with one `stale_pairs` entry each (`unit_id`,
`replaced_by` or null, `old_quote`, `new_quote`, `reason`), `outcome_issue` (null or text),
`changed_from_2026_11_12` and `previous_review` (the 12/11 unit list, the baseline of `kept`/`dropped`/`added`).

Checks (fail loudly, exit 1): every question of the source set appears exactly once; every unit ID exists in the v3
bundle; every quote is an exact substring of its unit (added quotes, both quotes of every stale pair); answer records
have at least one unit (also after dropping ancestors of listed units) and refuse records none; no answer unit is
stale, not yet effective or of unknown status at the record's `as_of` according to `legal_ai.kb.validity` with the
amendment edges of corpus v3; every `stale_unit_ids` entry is stale at that date and its replacement (if any) is in
force; `kept`/`dropped`/`added`/`stale_unit_ids` agree with `relevant_unit_ids` and the 12/11 baseline; no em dash.

The unit status comes from `src/legal_ai/kb/validity.py` as it is when this script runs; the printed status version
and the per-record `as_of` let the result be re-validated after that module changes.

Usage: python check-conflict.py [--version unit-status-v1|unit-status-v2]  (from the repository root or this folder;
default: the current version of the module)
"""

from datetime import date
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from legal_ai.kb import validity as validity_module  # noqa: E402
from legal_ai.kb.validity import STALE, STATUS_VERSION, Validity  # noqa: E402
from legal_ai.research.questions import QUESTION_TYPES  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BUNDLE = ROOT / "data/normalized/experiment-scope-v3-v48feefc6d53b"
EDGES = ROOT / "data/kb/amendments-scope-v3-v48feefc6d53b-v2/edges.jsonl"
SOURCE = ROOT / "experiments/runs/dryrun-conflict-v1/questions.json"
PREVIOUS = ROOT / "experiments/label-review-2026-11-12/conflict.jsonl"
RECORDS = HERE / "conflict.jsonl"
TYPE_ALIASES = {"validity": "temporal"}
REQUIRED = ("question_id", "question_type", "expected_status", "relevant_unit_ids", "kept", "dropped", "added",
            "outside_corpus", "reference_outcome_supported", "confidence", "note", "as_of", "as_of_source",
            "stale_unit_ids", "stale_pairs", "outcome_issue", "changed_from_2026_11_12")
EM_DASH = chr(0x2014)


def load(path):
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def minimal(unit_ids):
    ids = list(dict.fromkeys(unit_ids))
    return [u for u in ids if not any(o != u and o.startswith(u + "/") for o in ids)]


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def main():
    args = sys.argv[1:]
    version = args[args.index("--version") + 1] if "--version" in args else STATUS_VERSION
    documents, units = load(BUNDLE / "documents.jsonl"), load(BUNDLE / "units.jsonl")
    text = {u["unit_id"]: u["text"] for u in units}
    options = {"version": version} if hasattr(validity_module, "VERSIONS") else {}
    validity = Validity(documents, units, load(EDGES), **options)
    source_ids = [q["question_id"] for q in json.loads(SOURCE.read_text(encoding="utf-8"))["questions"]]
    previous = {r["question_id"]: r for r in load(PREVIOUS)}
    records = load(RECORDS)
    errors = []

    def fail(qid, message):
        errors.append(f"{qid}: {message}")

    seen = [r.get("question_id") for r in records]
    for qid in sorted(set(source_ids) - set(seen)):
        fail(qid, "question of the source set is missing")
    for qid in sorted(set(seen) - set(source_ids)):
        fail(qid, "question is not in the source set")
    for qid in sorted({q for q in seen if seen.count(q) > 1}):
        fail(qid, f"appears {seen.count(qid)} times")

    stats = {"questions": len(records), "units": 0, "kept": 0, "removed": 0, "added": 0, "stale": 0, "unchanged": 0,
             "status_changed": 0, "outcome_issues": 0, "confidence": {}}
    for r in records:
        qid = r.get("question_id", "?")
        missing = [f for f in REQUIRED if f not in r]
        if missing:
            fail(qid, f"missing fields {missing}")
            continue
        if any(EM_DASH in s for s in strings(r)):
            fail(qid, "contains an em dash")
        if TYPE_ALIASES.get(r["question_type"], r["question_type"]) not in QUESTION_TYPES:
            fail(qid, f"question type {r['question_type']}")
        if r["expected_status"] not in ("answer", "refuse"):
            fail(qid, f"expected_status {r['expected_status']}")
        if r["confidence"] not in ("high", "medium", "low"):
            fail(qid, f"confidence {r['confidence']}")
        if not r["changed_from_2026_11_12"] or not r["as_of_source"]:
            fail(qid, "changed_from_2026_11_12 and as_of_source must not be empty")
        try:
            as_of = date.fromisoformat(r["as_of"])
        except (TypeError, ValueError):
            fail(qid, f"as_of {r['as_of']!r} is not an ISO date")
            continue

        relevant, stale_ids = r["relevant_unit_ids"], r["stale_unit_ids"]
        pairs = r["stale_pairs"]
        listed = (relevant + r["kept"] + stale_ids + [d["unit_id"] for d in r["dropped"]] + [a["unit_id"] for a in r["added"]]
                  + [p["replaced_by"] for p in pairs if p.get("replaced_by")])
        unknown = sorted({u for u in listed if u not in text})
        if unknown:
            fail(qid, f"unknown units {unknown}")
            continue

        for a in r["added"]:
            if not a.get("reason") or not a.get("quote"):
                fail(qid, f"added {a['unit_id']} needs reason and quote")
            elif a["quote"] not in text[a["unit_id"]]:
                fail(qid, f"quote not in {a['unit_id']}: {a['quote'][:80]}")
            if a["unit_id"] not in relevant:
                fail(qid, f"added {a['unit_id']} is not in relevant_unit_ids")
        if sorted(p["unit_id"] for p in pairs) != sorted(stale_ids):
            fail(qid, "stale_pairs must hold exactly one entry per stale_unit_ids item")
        for p in pairs:
            if not p.get("reason") or not p.get("old_quote"):
                fail(qid, f"stale {p['unit_id']} needs reason and old_quote")
                continue
            if p["old_quote"] not in text[p["unit_id"]]:
                fail(qid, f"old quote not in {p['unit_id']}: {p['old_quote'][:80]}")
            new = p.get("replaced_by")
            if new:
                if not p.get("new_quote") or p["new_quote"] not in text[new]:
                    fail(qid, f"new quote not in {new}: {(p.get('new_quote') or '')[:80]}")
                if validity.status(new, as_of) != "in_force":
                    fail(qid, f"replacement {new} is {validity.status(new, as_of)} at {as_of}")
        for unit in stale_ids:
            status = validity.status(unit, as_of)
            if status not in STALE:
                fail(qid, f"stale unit {unit} is {status} at {as_of}, not stale")
            if unit in relevant:
                fail(qid, f"stale unit {unit} is still in relevant_unit_ids")

        final = minimal(relevant)
        if r["expected_status"] == "answer" and not final:
            fail(qid, "answer record without units")
        if r["expected_status"] == "refuse" and relevant:
            fail(qid, "refuse record with units")
        for unit in relevant:
            status = validity.status(unit, as_of)
            if status != "in_force":
                fail(qid, f"answer unit {unit} is {status} at {as_of}")

        base = previous.get(qid, {}).get("relevant_unit_ids", [])
        removed = set(stale_ids) | {d["unit_id"] for d in r["dropped"]}
        if r["kept"] != [u for u in base if u not in removed]:
            fail(qid, "kept must be the 12/11 units minus dropped and stale units")
        if set(relevant) != set(r["kept"]) | {a["unit_id"] for a in r["added"]}:
            fail(qid, "relevant_unit_ids must be kept plus added")
        for d in r["dropped"]:
            if d["unit_id"] not in base or not d.get("reason"):
                fail(qid, f"dropped {d['unit_id']} must be a 12/11 unit with a reason")

        stats["units"] += len(final)
        stats["kept"] += len(r["kept"])
        stats["removed"] += len(r["dropped"])
        stats["added"] += len(r["added"])
        stats["stale"] += len(stale_ids)
        stats["unchanged"] += set(relevant) == set(base) and not stale_ids
        stats["status_changed"] += r["expected_status"] != previous.get(qid, {}).get("expected_status")
        stats["outcome_issues"] += bool(r["outcome_issue"])
        stats["confidence"][r["confidence"]] = stats["confidence"].get(r["confidence"], 0) + 1

    print(f"unit status: {getattr(validity, 'version', STATUS_VERSION)}; edges ignored for unknown date: {validity.undated}")
    print(json.dumps(stats, ensure_ascii=False))
    if errors:
        print(f"FAILED ({len(errors)} problems):")
        for e in errors:
            print("  " + e)
        sys.exit(1)
    print("OK: all checks passed")


if __name__ == "__main__":
    main()
