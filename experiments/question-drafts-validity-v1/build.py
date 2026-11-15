"""Build the validity question set v1 from `drafts.json`: `questions.json` (the question-file format `run-retrieval` and
`answer-run` read) and `check-sheet.csv` (one row per question and unit for two human checkers), then run every check
of `validate.py`; nothing is written when a check fails.

The drafts were written by Claude Opus 5.5 in a Claude Code agent session on 2026-11-15 (unreviewed model draft); the
answer and stale sets follow from vbpl.vn document dates and the `amendment-rules-v2` edges, never from a legal
judgment, and the check sheet asks people only to compare texts and dates.

Usage: python build.py  (from the repository root or this folder; run pairs.py first on a fresh clone)
"""

import csv
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import validate  # noqa: E402
from legal_ai.kb.amendment_check import unit_path  # noqa: E402  (validate put src/ on the path)

DRAFTED_BY = {"model": "Claude Opus 5.5", "via": "Claude Code agent session", "date": "2026-11-15", "status": "unreviewed model draft"}
ROLES = {"answer": "đáp án", "stale": "lỗi thời", "later": "chưa có hiệu lực"}
COLUMNS = ["question_id", "group", "as_of", "question", "role", "unit_id", "unit_path", "status_at_as_of", "reason", "quotes",
           "context", "unit_text", "annotator_agrees", "annotator_note"]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reason(unit_id, role, as_of, question, units, documents, validity):
    """Why the unit has its role, in plain words from dates and edges only."""
    unit = units[unit_id]
    document = documents[unit["document_id"]]
    note = validity.note(unit_id, as_of)
    if role == "answer":
        text = f"Còn hiệu lực tại {as_of}: văn bản có hiệu lực từ {document['effective_from']} theo vbpl.vn"
        if document.get("effective_to"):
            text += f", hết hiệu lực từ {document['effective_to']}"
        for pair in question.get("amendments", []):
            if pair["new"] == unit_id:
                text += f"; đây là lời văn mới thay cho {unit_path(pair['old'], units, documents)}"
        for pair in question.get("pairs", []):
            if pair["new"] == unit_id:
                text += f"; quy định tương ứng của văn bản cũ: {unit_path(pair['old'], units, documents)}"
        return text
    counterpart = [p["new"] for p in question.get("pairs", []) + question.get("amendments", []) if p["old"] == unit_id]
    counterpart += [p["old"] for p in question.get("pairs", []) + question.get("amendments", []) if p["new"] == unit_id]
    suffix = f" Đơn vị tương ứng: {'; '.join(unit_path(u, units, documents) for u in counterpart)}." if counterpart else ""
    return (note or "") + suffix


def context_of(unit_id, units):
    """First lines of the ancestors (article heading, clause lead-in) that a point or clause depends on."""
    lines, current = [], units.get(units[unit_id]["parent_id"])
    while current and current["unit_type"] in ("article", "clause", "point"):
        lines.append(current["text"].strip().splitlines()[0])
        current = units.get(current["parent_id"])
    return "\n".join(reversed(lines))


def quotes_of(unit_id, question):
    found = [x["quote"] for x in question.get("quotes", []) if x["unit_id"] == unit_id]
    for pair in question.get("pairs", []):
        if unit_id in (pair["old"], pair["new"]):
            found.append(f"(cụm chữ chung của cặp) {pair['shared']}")
            found += [f"(câu dẫn) {c['quote']}" for c in pair.get("context", []) if unit_id == c["unit_id"] or unit_id.startswith(c["unit_id"] + "/")]
    return "\n".join(dict.fromkeys(found))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    drafts = json.loads((HERE / "drafts.json").read_text(encoding="utf-8"))["questions"]
    units, documents, edges, validity = validate.corpus()
    questions = [{"question_id": d["question_id"], "question": d["question"], "question_type": d["question_type"], "group": d["group"],
                  "family_id": "hlf-" + d["question_id"][3:], "expected_status": "answer", "as_of": d["as_of"],
                  "relevant_unit_ids": d["relevant_unit_ids"], "stale_unit_ids": d.get("stale_unit_ids", []),
                  **({"not_yet_effective_unit_ids": d["not_yet_effective_unit_ids"]} if d.get("not_yet_effective_unit_ids") else {}),
                  **{k: d[k] for k in ("pairs", "amendments", "quotes") if d.get(k)},
                  "rationale": d["rationale"], "annotation_status": "model_draft", "drafted_by": DRAFTED_BY} for d in drafts]
    problems = validate.check(questions, units, documents, edges, validity)
    if problems:
        print(json.dumps({"problems": problems}, ensure_ascii=False, indent=1))
        return 1
    document = {
        "description": ("Validity question set v1 (research plan WP4.5): 30 questions on corpus scope v3 in four groups (expired document "
                        "NĐ 12/2022 -> NĐ 283/2026, unit-level amendments, explicit past date, controls). Unreviewed model draft by Claude Opus 5.5 "
                        "(Claude Code agent session, 2026-11-15); answer and stale sets follow from vbpl.vn document dates and amendment-rules-v2 "
                        "edges, checked by validate.py; every question has an explicit as_of. Not human labels."),
        "set_version": "validity-v1-draft", "drafted_by": DRAFTED_BY,
        "corpus": {"bundle": validate.BUNDLE.relative_to(validate.ROOT).as_posix(), "units_sha256": sha256(validate.BUNDLE / "units.jsonl")},
        "amendments": {"edges": validate.EDGES.relative_to(validate.ROOT).as_posix(), "edges_sha256": sha256(validate.EDGES), "status_version": validate.STATUS_VERSION},
        "questions": questions}
    (HERE / "questions.json").write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    rows = []
    for q in questions:
        for role, ids in (("answer", q["relevant_unit_ids"]), ("stale", q["stale_unit_ids"]), ("later", q.get("not_yet_effective_unit_ids", []))):
            for unit_id in ids:
                rows.append({"question_id": q["question_id"], "group": q["group"], "as_of": q["as_of"], "question": q["question"],
                             "role": ROLES[role], "unit_id": unit_id, "unit_path": unit_path(unit_id, units, documents),
                             "status_at_as_of": validity.status(unit_id, q["as_of"]),
                             "reason": reason(unit_id, role, q["as_of"], q, units, documents, validity), "quotes": quotes_of(unit_id, q),
                             "context": context_of(unit_id, units), "unit_text": units[unit_id]["text"].strip(),
                             "annotator_agrees": "", "annotator_note": ""})
    with (HERE / "check-sheet.csv").open("w", encoding="utf-8-sig", newline="") as handle:  # BOM so spreadsheet apps read UTF-8.
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"questions": len(questions), "check_rows": len(rows), "groups": validate.summary(questions), "problems": []},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
