"""Merge the model-review labels of 15/11/2026 (cases, conflict, complex on corpus v3) into question files, check sheets
and import files.

These are MODEL REVIEW labels (Claude agents checked every unit against the frozen corpus v3 under the label conventions
of 15/11/2026 in docs/decisions.md), not human labels and not verified law. The annotators keep or change each proposal.

Per set it writes:
- `<set>-reviewed.json`: the question file the pipeline reads (`run-retrieval`, `answer-run`, `answer-outcome-judge`),
  `annotation_status: model_review`, with a `model_review` block (the 12/11 label, what changed and why);
- `<set>-check-sheet.csv` (UTF-8 with BOM): one row per question and unit with the verdict, reason, verbatim quote and
  unit path, plus two empty columns for the annotator;
- `<set>-drafts.json`: the import file for `python -m legal_ai.cli question-drafts` (stored as model proposals);
and `summary.json` with the counts.

Checks (fail loudly): the three validators `check-<set>.py` pass; every question of the source set is reviewed exactly
once; every unit exists in corpus v3; every quote is an exact substring of its unit; `relevant_unit_ids` is `kept` +
`added` and every unit of the 12/11 label is kept, dropped or stale; answer rows have units and refuse rows none;
question types are the app's; no answer unit is out of force at the question's date (unit-status-v2, amendment-rules-v2
edges); stale units are stale and not-yet-effective units are not yet effective at that date; case issues are a subset
of the source issues; paraphrase families keep a first member for `paraphrase_of`.

Conventions applied here, as in the 12/11 merge: a unit is dropped from a list when one of its descendants is in the
same list. Units a review listed as stale that are in fact not yet in force at the question's date (k02, k38: Luật BHXH
41/2024 after a 2023 dismissal) go to `not_yet_effective_unit_ids`, the field the answer metrics read for that case.

Usage: python merge.py  (from the repository root or this folder)
"""

import csv
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from legal_ai.kb.validity import STALE, STATUS_VERSION, Validity  # noqa: E402
from legal_ai.research.questions import QUESTION_TYPES  # noqa: E402

BUNDLE = ROOT / "data/normalized/experiment-scope-v3-v48feefc6d53b"
EDGES = ROOT / "data/kb/amendments-scope-v3-v48feefc6d53b-v2/edges.jsonl"
CORPUS_VERSION = "v48feefc6d53b"
REVIEW_DATE = "2026-11-15"
SETS = {
    "cases": ("experiments/runs/dryrun-cases-v1/questions-outcome.json", "Bộ tình huống v1 (rà soát model 15/11/2026, corpus v3)"),
    "conflict": ("experiments/runs/dryrun-conflict-v1/questions.json", "Bộ xung đột v1 (rà soát model 15/11/2026, corpus v3)"),
    "complex": ("experiments/runs/dryrun-complex-v1/questions.json", "Bộ phức tạp v1 (rà soát model 15/11/2026, corpus v3)"),
}
PREVIOUS = "experiments/label-review-2026-11-12"
TYPE_ALIASES = {"validity": "temporal"}
# Case questions whose events predate the law in corpus v3 (`as_of` null in cases.jsonl): the date of the decisive event,
# read from each record's `as_of_source` (precision as stated there). Flagged, never decided here.
OLD_LAW_EVENTS = {
    "k03": "2019-07-01", "k10": "2018-08-01", "k16": "2011-08", "k18": "2020-08", "k20": "2020-05", "k21": "2016-02",
    "k22": "2016-11-25", "k23": "2013-12", "k28": "2016-06", "k29": "2020-11-01", "k32": "2019-11-12", "k36": "2017-10-16",
    "k42": "2017-10-16",
}
VERDICTS = {"kept": "giữ", "added": "thêm", "removed": "bỏ", "ancestor": "bỏ (đã có đơn vị con chính xác hơn)",
            "stale": "lỗi thời", "not_yet_effective": "chưa có hiệu lực"}


def load(path):
    return [json.loads(line) for line in Path(path).open(encoding="utf-8") if line.strip()]


def minimal(unit_ids):
    """Drop every unit that has a descendant in the same list; keep order."""
    ids = list(dict.fromkeys(unit_ids))
    return [u for u in ids if not any(o != u and o.startswith(u + "/") for o in ids)]


def short_document(document):
    title = document["title"]
    for cut in (" Quy định", " Sửa đổi"):
        title = title.split(cut)[0]
    return title + (" (phần sửa đổi luật khác)" if document["document_id"].endswith("-sua-doi") else "")


class Checker:
    def __init__(self):
        self.errors = []

    def fail(self, where, message):
        self.errors.append(f"{where}: {message}")

    def raise_if_any(self):
        if self.errors:
            print(f"FAILED: {len(self.errors)} problem(s)")
            for line in self.errors:
                print("  " + line)
            sys.exit(1)


def run_validators():
    for name in SETS:
        result = subprocess.run([sys.executable, str(HERE / f"check-{name}.py")], capture_output=True, text=True, encoding="utf-8")
        if result.returncode != 0:
            print(result.stdout[-4000:], result.stderr[-4000:])
            sys.exit(f"check-{name}.py failed (exit {result.returncode})")
        print(f"check-{name}.py: ok")


def stale_pairs(record):
    """The three reviews spell replacement pairs differently; one shape here: (old, new, old_quote, new_quote, reason)."""
    out = []
    for pair in record.get("stale_pairs") or []:
        old = pair.get("stale_unit_id") or pair.get("unit_id")
        new = pair.get("new_unit_id") or pair.get("replaced_by")
        out.append({"stale_unit_id": old, "new_unit_id": new, "old_quote": pair.get("old_quote"), "new_quote": pair.get("new_quote"),
                    "reason": pair.get("reason", "")})
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    run_validators()
    units = {u["unit_id"]: u for u in load(BUNDLE / "units.jsonl")}
    documents = {d["document_id"]: d for d in load(BUNDLE / "documents.jsonl")}
    validity = Validity(list(documents.values()), list(units.values()), load(EDGES))
    check = Checker()

    def path(unit_id):
        unit = units[unit_id]
        return validity.describe(unit_id).split(", ")[0] + ", " + short_document(documents[unit["document_id"]])

    def quote_ok(where, unit_id, quote):
        if unit_id not in units:
            check.fail(where, f"unknown unit {unit_id}")
        elif not quote or quote not in units[unit_id]["text"]:
            check.fail(where, f"quote not in {unit_id}: {quote!r}")

    summary = {"review_date": REVIEW_DATE, "corpus_version_id": CORPUS_VERSION, "unit_status": validity.version if hasattr(validity, "version") else STATUS_VERSION,
               "edges": EDGES.relative_to(ROOT).as_posix(), "sets": {}}
    for name, (source, set_name) in SETS.items():
        questions = json.loads((ROOT / source).read_text(encoding="utf-8"))["questions"]
        reviews = load(HERE / f"{name}.jsonl")
        by_id = {r["question_id"]: r for r in reviews}
        if len(by_id) != len(reviews) or set(by_id) != {q["question_id"] for q in questions}:
            check.fail(name, "reviewed questions do not match the source set")
            check.raise_if_any()
        previous = {r["question_id"]: r for r in load(ROOT / PREVIOUS / f"{name}.jsonl")}
        previous_merged = {q["question_id"]: q for q in json.loads((ROOT / PREVIOUS / f"{name}-reviewed.json").read_text(encoding="utf-8"))["questions"]}
        out, sheet, drafts, first_of_family = [], [], [], {}
        stats = {"questions_source": len(questions), "excluded": [], "questions": 0, "answer": 0, "refuse": 0, "units_2026_11_12": 0,
                 "units": 0, "ancestors_dropped": 0, "kept": 0, "added": 0, "removed": 0, "stale": 0, "not_yet_effective": 0,
                 "unchanged": 0, "status_changed": 0, "confidence": {}, "with_as_of": 0, "old_law_cases": [], "outcome_issues": [],
                 "families": 0, "families_with_two_or_more": 0}
        for q in questions:
            qid, r = q["question_id"], by_id[q["question_id"]]
            where = f"{name}/{qid}"
            if r.get("excluded"):
                stats["excluded"].append({"question_id": qid, "reason": r["note"]})
                continue
            qtype = TYPE_ALIASES.get(r["question_type"], r["question_type"])
            if qtype not in QUESTION_TYPES:
                check.fail(where, f"question type {qtype}")
            relevant = list(dict.fromkeys(r["relevant_unit_ids"]))
            added = {a["unit_id"]: a for a in r.get("added", [])}
            dropped = {d["unit_id"]: d for d in r.get("dropped", [])}
            if set(r["kept"]) | set(added) != set(relevant) or len(r["kept"]) + len(added) != len(relevant):
                check.fail(where, "relevant_unit_ids is not kept + added")
            for unit_id in relevant + list(dropped) + r.get("stale_unit_ids", []):
                if unit_id not in units:
                    check.fail(where, f"unknown unit {unit_id}")
            for a in added.values():
                quote_ok(where + " added", a["unit_id"], a.get("quote"))
            pairs = stale_pairs(r)
            for p in pairs:
                quote_ok(where + " stale pair", p["stale_unit_id"], p["old_quote"])
                quote_ok(where + " stale pair", p["new_unit_id"], p["new_quote"])
            check.raise_if_any()

            day = r.get("checked_at") or r.get("as_of")
            for unit_id in relevant:
                status = validity.status(unit_id, day)
                if status != "in_force":
                    check.fail(where, f"answer unit {unit_id} is {status} at {day}")
            stale, not_yet = [], []
            for unit_id in r.get("stale_unit_ids", []):
                status = validity.status(unit_id, day)
                if status in STALE:
                    stale.append(unit_id)
                elif status == "not_yet_effective":
                    not_yet.append(unit_id)
                else:
                    check.fail(where, f"listed stale unit {unit_id} is {status} at {day}")
            before = list(dict.fromkeys(previous[qid]["relevant_unit_ids"]))
            unaccounted = set(before) - set(r["kept"]) - set(dropped) - set(stale) - set(not_yet)
            if unaccounted:
                check.fail(where, f"12/11 units neither kept, dropped nor stale: {sorted(unaccounted)}")
            final = minimal(relevant)
            if (r["expected_status"] == "answer") != bool(final):
                check.fail(where, f"status {r['expected_status']} with {len(final)} units")

            record = {k: q[k] for k in ("question_id", "question", "complex_kind", "case_id", "family_id", "split", "source_ref", "documents") if k in q}
            record |= {"question_type": qtype, "expected_status": r["expected_status"], "relevant_unit_ids": final}
            if r.get("as_of"):
                record["as_of"] = r["as_of"]
                stats["with_as_of"] += 1
            record["as_of_source"] = r.get("as_of_source", "")
            if stale:
                record["stale_unit_ids"] = stale
            if not_yet:
                record["not_yet_effective_unit_ids"] = not_yet
            if name == "cases":
                if not set(r["issues"]) <= set(q.get("issues", [])):
                    check.fail(where, "issues not in the source issues")
                dropped_issues = {i["issue"] for i in r.get("issues_dropped", [])}
                if set(q.get("issues", [])) - set(r["issues"]) - dropped_issues:
                    check.fail(where, "source issues neither kept nor dropped")
                record["issues"] = r["issues"]
                if r.get("as_of") is None:
                    if qid not in OLD_LAW_EVENTS:
                        check.fail(where, "as_of is null but no old-law event date is recorded in OLD_LAW_EVENTS")
                    else:
                        record |= {"old_law_case": True, "event_date": OLD_LAW_EVENTS[qid]}
                        stats["old_law_cases"].append({"question_id": qid, "event_date": OLD_LAW_EVENTS[qid]})
                elif qid in OLD_LAW_EVENTS:
                    check.fail(where, "has as_of but is listed in OLD_LAW_EVENTS")
            for key in ("issues", "reference_outcome"):
                if key in q and key not in record:
                    record[key] = q[key]
            if name == "conflict" and r.get("outcome_issue"):
                stats["outcome_issues"].append(qid)
            review = {"date": REVIEW_DATE, "corpus_version_id": CORPUS_VERSION, "label_2026_11_12": {
                          "relevant_unit_ids": previous_merged[qid]["relevant_unit_ids"], "expected_status": previous_merged[qid]["expected_status"],
                          "confidence": previous_merged[qid]["model_review"]["confidence"]},
                      "kept": r["kept"], "added": r.get("added", []), "dropped": r.get("dropped", []), "stale_pairs": pairs,
                      "ancestors_dropped": [u for u in relevant if u not in final], "outside_corpus": r.get("outside_corpus", []),
                      "confidence": r["confidence"], "note": r["note"], "changed_from_2026_11_12": r["changed_from_2026_11_12"],
                      "checked_at": day}
            for key in ("issues_dropped", "basis", "outcome_issue", "reference_outcome_supported", "family_difference"):
                if r.get(key) not in (None, [], ""):
                    review[key] = r[key]
            out.append(record | {"annotation_status": "model_review", "model_review": review})

            # Check sheet: one row per unit the question touches.
            basis = {b["unit_id"]: b.get("quote") for b in r.get("basis", [])}
            replaced = {p["stale_unit_id"]: p for p in pairs}
            flags = "; ".join(x for x in (
                f"sự việc theo luật cũ ({record['event_date']})" if record.get("old_law_case") else "",
                f"kết quả tham chiếu cần sửa: {r['outcome_issue']}" if r.get("outcome_issue") else "",
                f"khác nhóm diễn đạt: {r['family_difference']}" if r.get("family_difference") else "") if x)
            for unit_id in list(dict.fromkeys(before + relevant + list(dropped) + stale + not_yet)):
                if unit_id in stale or unit_id in not_yet:
                    verdict = "stale" if unit_id in stale else "not_yet_effective"
                    pair = replaced.get(unit_id)
                    reason = (pair or {}).get("reason") or dropped.get(unit_id, {}).get("reason", "")
                    quote = (pair or {}).get("old_quote") or units[unit_id]["text"][:600]
                    replacement = f"{pair['new_unit_id']} ({path(pair['new_unit_id'])}): {pair['new_quote']}" if pair else ""
                elif unit_id in relevant and unit_id not in final:
                    verdict, reason, quote, replacement = "ancestor", "đã có đơn vị con chính xác hơn trong nhãn", units[unit_id]["text"][:600], ""
                elif unit_id in final:
                    verdict = "added" if unit_id in added else "kept"
                    item = added.get(unit_id, {})
                    reason = item.get("reason", "")
                    quote = item.get("quote") or basis.get(unit_id) or units[unit_id]["text"][:600]
                    replacement = ""
                else:
                    verdict, reason, quote, replacement = "removed", dropped.get(unit_id, {}).get("reason", ""), units[unit_id]["text"][:600], ""
                stats[{"kept": "kept", "added": "added", "removed": "removed", "ancestor": "ancestors_dropped",
                       "stale": "stale", "not_yet_effective": "not_yet_effective"}[verdict]] += 1
                sheet.append([qid, q["question"], r["expected_status"], r["confidence"], record.get("as_of") or f"(không ghi; mặc định {day})",
                              VERDICTS[verdict], unit_id, path(unit_id), reason, quote, replacement, r["note"], flags, "", ""])

            # Import file: the fields the app stores as a proposal, and a short rationale for the annotator.
            family = q["family_id"]
            paraphrase_of = first_of_family.get(family)
            first_of_family.setdefault(family, len(drafts))
            parts = [f"Đề xuất của model (rà soát {REVIEW_DATE} trên corpus v3), không phải nhãn người. Độ tin cậy: "
                     f"{ {'high': 'cao', 'medium': 'vừa', 'low': 'thấp'}[r['confidence']] }."]
            undated = record.get("as_of") and "no date in question" in record["as_of_source"]
            parts.append(f"Ngày áp dụng: {record['as_of']} (câu không ghi ngày nên dùng ngày khóa corpus v3)." if undated else
                         f"Ngày áp dụng: {record['as_of']} (ngày nêu trong câu hoặc hồ sơ)." if record.get("as_of") else
                         f"Không có ngày áp dụng trong corpus; đơn vị là quy định hiện hành, kiểm hiệu lực tại {day}.")
            if pairs:
                parts.append("Lỗi thời và được thay: " + "; ".join(f"{path(p['stale_unit_id'])} -> {path(p['new_unit_id'])}" for p in pairs) + ".")
            other = [u for u in stale + not_yet if u not in replaced]
            if other:
                parts.append("Không còn hiệu lực hoặc chưa có hiệu lực tại ngày đó, không có đơn vị thay: " + "; ".join(path(u) for u in other) + ".")
            if record.get("old_law_case"):
                parts.append(f"Cần quyết định: sự việc ({record['event_date']}) theo luật cũ không có trong corpus; giữ hay loại câu (cờ old_law_case).")
            if r.get("outcome_issue"):
                parts.append("Cần quyết định: kết quả tham chiếu phải sửa (xem bảng kiểm).")
            parts.append("Căn cứ và lưu ý: " + r["note"])
            rationale = " ".join(parts)
            if len(rationale) > 2000:
                rationale = rationale[:1990].rsplit(". ", 1)[0] + ". (...)"
            drafts.append({"text": q["question"], "question_type": qtype, "expected_status": r["expected_status"], "relevant_unit_ids": final,
                           "rationale": rationale, "paraphrase_of": paraphrase_of, "source_question_id": qid})

            stats["questions"] += 1
            stats[r["expected_status"]] += 1
            stats["units_2026_11_12"] += len(previous_merged[qid]["relevant_unit_ids"])
            stats["units"] += len(final)
            stats["unchanged"] += sorted(final) == sorted(previous_merged[qid]["relevant_unit_ids"]) and r["expected_status"] == previous_merged[qid]["expected_status"]
            stats["status_changed"] += r["expected_status"] != previous_merged[qid]["expected_status"]
            stats["confidence"][r["confidence"]] = stats["confidence"].get(r["confidence"], 0) + 1
        check.raise_if_any()
        fam_count = {}
        for q in out:
            fam_count[q["family_id"]] = fam_count.get(q["family_id"], 0) + 1
        stats["families"], stats["families_with_two_or_more"] = len(fam_count), sum(v > 1 for v in fam_count.values())

        source_file = json.loads((ROOT / source).read_text(encoding="utf-8"))
        (HERE / f"{name}-reviewed.json").write_text(json.dumps({
            "description": (source_file.get("description") or "") + f" | Model review {REVIEW_DATE} on corpus v3 {CORPUS_VERSION} (not human labels): "
                           "see experiments/label-review-2026-11-15/README.md",
            "name": set_name, "corpus_version_id": CORPUS_VERSION, "unit_status": summary["unit_status"], "edges": summary["edges"],
            "excluded": stats["excluded"], "questions": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        with (HERE / f"{name}-check-sheet.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["question_id", "question", "expected_status", "confidence", "as_of", "verdict", "unit_id", "unit_path", "reason",
                             "quote", "replaced_by", "note", "flags", "annotator_agrees", "annotator_note"])
            writer.writerows(sheet)
        (HERE / f"{name}-drafts.json").write_text(json.dumps(drafts, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        summary["sets"][name] = stats
        print(f"{name}: {stats['questions']} questions ({len(stats['excluded'])} excluded), {stats['units']} units after the ancestor convention")
    raw = json.dumps(summary, ensure_ascii=False, indent=1)
    if "\u2014" in raw:
        sys.exit("summary contains the em dash")
    (HERE / "summary.json").write_text(raw + "\n", encoding="utf-8", newline="\n")
    for name in SETS:
        for suffix in ("-reviewed.json", "-check-sheet.csv", "-drafts.json"):
            if "\u2014" in (HERE / f"{name}{suffix}").read_text(encoding="utf-8-sig"):
                sys.exit(f"{name}{suffix} contains the em dash")


if __name__ == "__main__":
    main()
