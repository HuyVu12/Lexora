"""Mechanical checks of the validity question set v1 (`questions.json`, or `drafts.json` with --drafts). Exit code 1 on
any failure. No network, no model; only the frozen corpus v3, its amendment edges and the candidate pair files.

Checks:
1. structure: unique question IDs, a group of GROUPS, a question type of the app's QUESTION_TYPES, expected status
   `answer`, an ISO `as_of` on every question, at least one answer unit, no unit both answer and stale;
2. every unit ID (answer, stale, not yet effective, pairs, amendments, quotes, context) exists in the v3 bundle;
3. every quote and context quote is an exact substring of its unit; the `shared` wording of a pair is a substring of
   both units (compared case-insensitively, so a phrase may start a sentence in one decree and not in the other); a
   context unit is an ancestor of its pair unit;
4. unit status (`kb/validity.py`, `unit-status-v2`, edges of `amendment-rules-v2`) at `as_of`: the stale set equals the listed units (answer + stale)
   that are expired, repealed or amended; every answer unit is in force; every `not_yet_effective_unit_ids` unit is
   not yet effective;
5. pairs NĐ 12/2022 -> NĐ 283/2026: not marked `manual`, the pair is in `pairs-expired.jsonl`; an old unit in the stale
   set has its new unit among the answers, an old unit among the answers has its new unit not yet effective;
6. amendments: (old, new) is a resolved edge of `amendment-rules-v1` with that target and amending unit; old stale
   means the edge is effective by `as_of` and the new unit is an answer, old answer means the edge is not yet
   effective and the new unit is listed as not yet effective; rows of `pairs-amended.jsonl` with a caveat (the
   foreign-worker part of NĐ 152/2020) need an `as_of` before NĐ 219/2025 took effect;
7. groups: control questions have no stale, no not-yet-effective units, no pairs or amendments; every other question
   has at least one stale or not-yet-effective unit.

Usage: python validate.py [--drafts]  (from the repository root or this folder)
"""

from datetime import date
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from legal_ai.kb.validity import STALE, STATUS_VERSION, Validity  # noqa: E402
from legal_ai.research.questions import QUESTION_TYPES  # noqa: E402

BUNDLE = ROOT / "data/normalized/experiment-scope-v3-v48feefc6d53b"
EDGES = ROOT / "data/kb/amendments-scope-v3-v48feefc6d53b-v2/edges.jsonl"
GROUPS = ("expired_document", "unit_amendment", "past_date", "control")


def load(path):
    return [json.loads(line) for line in Path(path).open(encoding="utf-8")]


def corpus():
    units = {u["unit_id"]: u for u in load(BUNDLE / "units.jsonl")}
    documents = {d["document_id"]: d for d in load(BUNDLE / "documents.jsonl")}
    edges = load(EDGES)
    return units, documents, edges, Validity(list(documents.values()), list(units.values()), edges)


def check(questions, units, documents, edges, validity):
    """[problem strings] for a list of questions; empty when every check passes."""
    problems = []
    expired_pairs = {(r["old_unit_id"], r["new_unit_id"]) for r in load(HERE / "pairs-expired.jsonl")}
    caveats = {(r["old_unit_id"], r["amending_unit_id"]) for r in load(HERE / "pairs-amended.jsonl") if "caveat" in r}
    edge_by_pair = {(e["target_unit_id"], e.get("amending_unit_id")): e for e in edges if e["status"] == "resolved"}
    foreign_worker_end = documents["219-2025-nd-cp"]["effective_from"]
    seen = set()
    for q in questions:
        qid = q.get("question_id")
        fail = lambda message: problems.append(f"{qid}: {message}")
        if qid in seen:
            fail("duplicate question_id")
        seen.add(qid)
        if q.get("group") not in GROUPS:
            fail(f"group {q.get('group')!r}")
        if q.get("question_type") not in QUESTION_TYPES:
            fail(f"question type {q.get('question_type')!r}")
        if q.get("expected_status", "answer") != "answer":
            fail("expected_status must be answer")
        try:
            as_of = date.fromisoformat(q["as_of"]).isoformat()
        except (KeyError, TypeError, ValueError):
            fail("as_of missing or not an ISO date")
            continue
        relevant, stale, later = q.get("relevant_unit_ids", []), q.get("stale_unit_ids", []), q.get("not_yet_effective_unit_ids", [])
        if not relevant:
            fail("no answer unit")
        listed = relevant + stale + later
        if len(set(listed)) != len(listed):
            fail("a unit is listed twice (answer, stale or not yet effective)")
        named = listed + [p[k] for p in q.get("pairs", []) + q.get("amendments", []) for k in ("old", "new")]
        named += [x["unit_id"] for x in q.get("quotes", [])] + [c["unit_id"] for p in q.get("pairs", []) for c in p.get("context", [])]
        missing = sorted({u for u in named if u not in units})
        if missing:
            fail(f"units not in the v3 bundle: {missing}")
            continue
        for item in q.get("quotes", []):
            if item["quote"] not in units[item["unit_id"]]["text"]:
                fail(f"quote not in {item['unit_id']}: {item['quote'][:60]!r}")
        for pair in q.get("pairs", []):
            for side in ("old", "new"):
                if pair["shared"].casefold() not in units[pair[side]]["text"].casefold():
                    fail(f"shared wording not in {pair[side]}: {pair['shared'][:60]!r}")
            for context in pair.get("context", []):
                if not any(pair[side] == context["unit_id"] or pair[side].startswith(context["unit_id"] + "/") for side in ("old", "new")):
                    fail(f"context {context['unit_id']} is neither a pair unit nor its ancestor")
                if context["quote"] not in units[context["unit_id"]]["text"]:
                    fail(f"context quote not in {context['unit_id']}: {context['quote'][:60]!r}")
            if not pair.get("manual") and (pair["old"], pair["new"]) not in expired_pairs:
                fail(f"pair {pair['old']} -> {pair['new']} is not in pairs-expired.jsonl and not marked manual")
            if pair["old"] in stale and pair["new"] not in relevant:
                fail(f"stale {pair['old']} without its in-force counterpart {pair['new']} among the answers")
            if pair["old"] in relevant and pair["new"] not in later:
                fail(f"answer {pair['old']}: its later counterpart {pair['new']} must be listed as not yet effective")
            if pair["old"] not in stale + relevant:
                fail(f"pair {pair['old']} is neither an answer nor stale")
        for pair in q.get("amendments", []):
            edge = edge_by_pair.get((pair["old"], pair["new"]))
            if edge is None:
                fail(f"no resolved edge {pair['old']} -> {pair['new']}")
                continue
            effective = edge["effective_from"] <= as_of
            if pair["old"] in stale and not (effective and pair["new"] in relevant):
                fail(f"stale {pair['old']}: the edge must be effective by as_of and {pair['new']} an answer")
            if pair["old"] in relevant and not (not effective and pair["new"] in later):
                fail(f"answer {pair['old']}: the edge must not be effective yet and {pair['new']} listed as not yet effective")
            if pair["old"] not in stale + relevant:
                fail(f"amended unit {pair['old']} is neither an answer nor stale")
            if (pair["old"], pair["new"]) in caveats and as_of >= foreign_worker_end:
                fail(f"{pair['old']}: foreign-worker part of NĐ 152/2020 needs as_of before {foreign_worker_end} (NĐ 219/2025)")
        status = {u: validity.status(u, as_of) for u in listed}
        expected_stale = [u for u in relevant + stale if status[u] in STALE]
        if sorted(stale) != sorted(expected_stale):
            fail(f"stale set {sorted(stale)} differs from unit-status-v2 at {as_of}: {sorted(expected_stale)}")
        for unit in relevant:
            if status[unit] != "in_force":
                fail(f"answer unit {unit} is {status[unit]} at {as_of}")
        for unit in later:
            if status[unit] != "not_yet_effective":
                fail(f"{unit} is {status[unit]} at {as_of}, listed as not yet effective")
        if q.get("group") == "control":
            if stale or later or q.get("pairs") or q.get("amendments"):
                fail("a control question has no stale or later units, pairs or amendments")
        elif not stale and not later:
            fail("a validity question needs a stale or a not-yet-effective unit")
    return problems


def summary(questions):
    groups = {}
    for q in questions:
        group = groups.setdefault(q["group"], {"questions": 0, "answer_units": 0, "stale_units": 0, "not_yet_effective_units": 0})
        group["questions"] += 1
        group["answer_units"] += len(q["relevant_unit_ids"])
        group["stale_units"] += len(q.get("stale_unit_ids", []))
        group["not_yet_effective_units"] += len(q.get("not_yet_effective_unit_ids", []))
    return groups


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    path = HERE / ("drafts.json" if "--drafts" in argv else "questions.json")
    questions = json.loads(path.read_text(encoding="utf-8"))["questions"]
    problems = check(questions, *corpus())
    print(json.dumps({"file": path.name, "questions": len(questions), "groups": summary(questions), "problems": problems},
                     ensure_ascii=False, indent=1))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
