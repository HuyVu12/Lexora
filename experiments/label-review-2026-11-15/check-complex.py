"""Validate the model-review labels of the complex question set on corpus v3 (15/11/2026): `complex.jsonl` in this folder.

These are MODEL REVIEW labels (proposals a human annotator keeps or changes), not human labels and not verified law.

Fails loudly (non-zero exit, one line per problem) unless:
- every question of the source set appears exactly once, and no other question appears;
- every unit ID used anywhere in a record exists in the frozen corpus v3 bundle;
- every quote (added units, restated partner units, stale pairs and their context) is an exact substring of its unit;
- `relevant_unit_ids` equals `kept` + `added`, and `kept` + `dropped` + `stale_unit_ids` is exactly the 12/11 label;
- answer records have at least one unit, refuse records none; question types are the app's `QUESTION_TYPES`;
- no answer unit is anything but `in_force` at the record's `as_of`, by `legal_ai.kb.validity` over the v3 documents and
  `amendment-rules-v2` edges, under every unit-status version the module offers (`VERSIONS`, else its default); every `stale_unit_ids` entry is stale (expired, repealed or amended) at
  that date, has a pair quote in `stale_pairs`, and its replacement is in the answer set;
- members of one paraphrase family have equal answer sets (after dropping ancestors of listed descendants, as the
  12/11 merge does) unless every differing record explains the difference in `family_difference`;
- no text contains the em dash character.

The unit status is computed at run time, so re-running this after `kb/validity.py` or the edges change re-validates the
`as_of` dates recorded in each line.

Usage: python check-complex.py  (from the repository root or this folder)
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

BUNDLE = ROOT / "data/normalized/experiment-scope-v3-v48feefc6d53b"
EDGES = ROOT / "data/kb/amendments-scope-v3-v48feefc6d53b-v2/edges.jsonl"
SOURCE = ROOT / "experiments/runs/dryrun-complex-v1/questions.json"
PREVIOUS = ROOT / "experiments/label-review-2026-11-12/complex.jsonl"
LABELS = HERE / "complex.jsonl"
REQUIRED = ("question_id", "question_type", "expected_status", "relevant_unit_ids", "kept", "dropped", "added", "outside_corpus",
            "confidence", "note", "as_of", "as_of_source", "stale_unit_ids", "stale_pairs", "changed_from_2026_11_12")
TYPE_ALIASES = {"validity": "temporal"}


def load(path):
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def minimal(unit_ids):
    """Drop every unit that has a descendant in the same list (the 12/11 merge convention); keep order."""
    ids = list(dict.fromkeys(unit_ids))
    return [u for u in ids if not any(o != u and o.startswith(u + "/") for o in ids)]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    units = {u["unit_id"]: u for u in load(BUNDLE / "units.jsonl")}
    documents, edges = load(BUNDLE / "documents.jsonl"), load(EDGES)
    versions = getattr(validity_module, "VERSIONS", (STATUS_VERSION,))
    models = {v: (Validity(documents, list(units.values()), edges, version=v) if hasattr(validity_module, "VERSIONS")
                  else Validity(documents, list(units.values()), edges)) for v in versions}
    questions = json.loads(SOURCE.read_text(encoding="utf-8"))["questions"]
    previous = {r["question_id"]: r for r in load(PREVIOUS)}
    raw = LABELS.read_text(encoding="utf-8")
    records = load(LABELS)
    errors = []

    def fail(qid, message):
        errors.append(f"{qid}: {message}")

    if "\u2014" in raw:
        fail("file", "contains the em dash character")
    seen = [r.get("question_id") for r in records]
    source_ids = [q["question_id"] for q in questions]
    for qid in sorted(set(seen)):
        if seen.count(qid) > 1:
            fail(qid, f"appears {seen.count(qid)} times")
    for qid in sorted(set(source_ids) - set(seen)):
        fail(qid, "missing from complex.jsonl")
    for qid in sorted(set(seen) - set(source_ids)):
        fail(qid, "not in the source set")

    def unit_text(qid, unit_id, where):
        if unit_id not in units:
            fail(qid, f"{where}: unknown unit {unit_id}")
            return None
        return units[unit_id]["text"]

    def check_quote(qid, unit_id, quote, where):
        text = unit_text(qid, unit_id, where)
        if text is not None and (not quote or quote not in text):
            fail(qid, f"{where}: quote is not an exact substring of {unit_id}: {quote!r}")

    family = {q["question_id"]: q["family_id"] for q in questions}
    final = {}
    for r in records:
        qid = r.get("question_id", "?")
        missing = [k for k in REQUIRED if k not in r]
        if missing:
            fail(qid, f"missing fields {missing}")
            continue
        qtype = TYPE_ALIASES.get(r["question_type"], r["question_type"])
        if qtype not in QUESTION_TYPES:
            fail(qid, f"question type {qtype} not in QUESTION_TYPES")
        if r["expected_status"] not in ("answer", "refuse"):
            fail(qid, f"expected_status {r['expected_status']}")
        if r["confidence"] not in ("high", "medium", "low"):
            fail(qid, f"confidence {r['confidence']}")
        try:
            as_of = date.fromisoformat(r["as_of"])
        except (TypeError, ValueError):
            fail(qid, f"as_of {r['as_of']!r} is not an ISO date")
            continue
        if not r["as_of_source"] or not r["changed_from_2026_11_12"] or not r["note"]:
            fail(qid, "empty as_of_source, note or changed_from_2026_11_12")

        relevant = r["relevant_unit_ids"]
        for unit_id in relevant + r["kept"] + r["stale_unit_ids"] + [d.get("unit_id") for d in r["dropped"]]:
            unit_text(qid, unit_id, "unit list")
        added_ids = [a.get("unit_id") for a in r["added"]]
        if list(dict.fromkeys(r["kept"] + added_ids)) != list(dict.fromkeys(relevant)):
            fail(qid, "relevant_unit_ids is not kept + added")
        for item in r["added"]:
            if not item.get("reason"):
                fail(qid, f"added {item.get('unit_id')}: no reason")
            check_quote(qid, item.get("unit_id"), item.get("quote"), "added")
            if "restates_unit_id" in item:
                check_quote(qid, item["restates_unit_id"], item.get("restates_quote"), f"added {item['unit_id']} restates")
        for item in r["dropped"]:
            if not item.get("reason"):
                fail(qid, f"dropped {item.get('unit_id')}: no reason")
        if qid in previous:
            before = set(previous[qid]["relevant_unit_ids"])
            accounted = set(r["kept"]) | {d["unit_id"] for d in r["dropped"]} | set(r["stale_unit_ids"])
            if accounted != before:
                fail(qid, f"kept + dropped + stale differ from the 12/11 label: extra {sorted(accounted - before)}, missing {sorted(before - accounted)}")
            if set(r["kept"]) & set(added_ids):
                fail(qid, "a unit is both kept and added")

        answer = minimal(relevant)
        if (r["expected_status"] == "answer") != bool(answer):
            fail(qid, f"status {r['expected_status']} with {len(answer)} answer units")
        for unit_id in relevant:
            if unit_id in units:
                for version, model in models.items():
                    status = model.status(unit_id, as_of)
                    if status != "in_force":
                        fail(qid, f"answer unit {unit_id} is {status} at {as_of} ({version})")
        paired = {}
        for pair in r["stale_pairs"]:
            old, new = pair.get("stale_unit_id"), pair.get("new_unit_id")
            check_quote(qid, old, pair.get("old_quote"), "stale pair (old)")
            check_quote(qid, new, pair.get("new_quote"), "stale pair (new)")
            for side in ("old_context", "new_context"):
                if side in pair:
                    check_quote(qid, pair[side].get("unit_id"), pair[side].get("quote"), f"stale pair {side}")
            if not pair.get("reason"):
                fail(qid, f"stale pair {old}: no reason")
            if new not in relevant:
                fail(qid, f"stale pair {old}: replacement {new} is not in the answer set")
            paired.setdefault(old, []).append(new)
        for unit_id in r["stale_unit_ids"]:
            if unit_id in units:
                for version, model in models.items():
                    if model.status(unit_id, as_of) not in STALE:
                        fail(qid, f"stale unit {unit_id} is {model.status(unit_id, as_of)} at {as_of} ({version})")
            if unit_id in relevant:
                fail(qid, f"stale unit {unit_id} is also an answer unit")
            if unit_id not in paired:
                fail(qid, f"stale unit {unit_id} has no pair quote in stale_pairs")
        for old in paired:
            if old not in r["stale_unit_ids"]:
                fail(qid, f"stale pair for {old}, which is not in stale_unit_ids")
        final[qid] = (frozenset(answer), (r.get("family_difference") or "").strip())

    groups = {}
    for qid, fid in family.items():
        if qid in final:
            groups.setdefault(fid, []).append(qid)
    for fid, members in sorted(groups.items()):
        if len({final[m][0] for m in members}) > 1:
            unexplained = [m for m in members if not final[m][1]]
            if unexplained:
                fail(fid, f"family members {members} have different answer sets and {unexplained} give no family_difference")

    if errors:
        print(f"FAILED: {len(errors)} problem(s)")
        for line in errors:
            print("  " + line)
        sys.exit(1)
    stale = sum(len(r["stale_unit_ids"]) for r in records)
    print(json.dumps({"status": "ok", "records": len(records), "answer_units_after_merge": sum(len(v[0]) for v in final.values()),
                      "stale_units": stale, "unit_status_versions_checked": list(versions),
                      "as_of": sorted({r["as_of"] for r in records}),
                      "families_with_explained_difference": sorted(f for f, m in groups.items() if len({final[x][0] for x in m}) > 1)},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
