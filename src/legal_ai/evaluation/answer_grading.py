"""Human grading of cited answers across conditions, and an LLM judge as a supplement (`answer-grading-v1`).

`make_sheet` pools the answers of several answer runs (one per condition) into one CSV in a seeded random order
with opaque item IDs; the key that maps items back to condition and question is written to a separate file.
Graders see the question, the gold units and, for each statement, the full text of the canonical units its
citations point to. They never see what the condition retrieved (a fixed chunk, a structural unit or a
serialized claim), so the shape of the context does not reveal the condition; they grade against the statute.

Rubric (the same one the judge prompt gives the model):
- per statement: `supported` 2 full / 1 partial / 0 none; `citation_correct` 1 if a cited unit holds the basis;
- per answer: `correctness` 0 / 1 / 2; `refusal_appropriate` 1 / 0 for refused answers only.

`score_sheet` reads a filled sheet (people or judge) with the key and reports per condition: citation support,
grounding (fully supported statements / graded statements), mean correctness, strict success (correctness 2)
and appropriate refusals, each with its denominator, and the answers that failed before grading (listed in the key,
never put on the sheet). `agreement` compares two filled sheets (Cohen's kappa).
"""

import csv
import json
from pathlib import Path
import random

from legal_ai.common.io import canonical, digest, read_jsonl, write_json, write_jsonl
from legal_ai.evaluation.answer_run import REFUSED, latest_answers, system_prompt
from legal_ai.providers.pilot import ProviderError
from legal_ai.research.questions import kappa

GRADING_VERSION = "answer-grading-v1"
COLUMNS = ["item_id", "row", "question", "status", "statement", "cited_units", "gold_units",
           "supported", "citation_correct", "correctness", "refusal_appropriate", "note"]


def _units_for(answer_dir):
    retrieval = json.loads((Path(answer_dir) / "manifest.json").read_text(encoding="utf-8"))["retrieval_run"]
    units_path = json.loads((Path(retrieval) / "manifest.json").read_text(encoding="utf-8"))["inputs"]["units"]["path"]
    return {u["unit_id"]: u for u in read_jsonl(units_path)}


def _show(unit_ids, units):
    return "\n\n".join(f"[{uid}]\n{units[uid]['text'].strip()}" for uid in unit_ids if uid in units)


def _collect(answer_dirs, questions_path):
    """Gradable items, failed answers (with their error code) and answers whose question is not in the file."""
    questions = {q["question_id"]: q for q in json.loads(Path(questions_path).read_text(encoding="utf-8"))["questions"]}
    result, failed, outside = [], [], []
    for answer_dir in answer_dirs:
        manifest = json.loads((Path(answer_dir) / "manifest.json").read_text(encoding="utf-8"))
        units = _units_for(answer_dir)
        for qid, answer in sorted(latest_answers(Path(answer_dir) / "answers.jsonl").items()):
            where = {"answer_dir": Path(answer_dir).as_posix(), "condition": manifest["condition"], "question_id": qid}
            if qid not in questions:
                outside.append(where)
                continue
            if answer.get("error") is not None:
                failed.append(where | {"error": answer["error"]})
                continue
            question = questions[qid]
            result.append({"answer_dir": Path(answer_dir).as_posix(), "condition": manifest["condition"], "question_id": qid,
                           "question": question["question"], "status": answer["status"],
                           "gold": _show(question.get("relevant_unit_ids") or [], units),
                           "statements": [{"text": s["text"], "cited": _show(s["unit_ids"], units)} for s in answer["statements"]]})
    return result, failed, outside


def items(answer_dirs, questions_path):
    """One grading item per (answer run, question) with the texts graders need; order follows the inputs. Failed
    answers and answers to questions outside the file are not items; `make_sheet` records them in the key."""
    return _collect(answer_dirs, questions_path)[0]


def _item_id(seed, answer_dir, question_id):
    return "A" + digest(canonical([seed, answer_dir, question_id]))[:10]


def make_sheet(answer_dirs, questions_path, sheet_path, key_path, seed="lexora-grading-v1"):
    """Blinded sheet of the gradable answers and its key. Graders never get an empty answer: failed answers stay off
    the sheet and are listed in the key under `failed` (with their error code, same item ID scheme), and answers to
    questions outside the question file under `not_in_questions`, so every score can count them per condition."""
    pool, failed, outside = _collect(answer_dirs, questions_path)
    random.Random(seed).shuffle(pool)
    key, rows = {}, []
    for item in pool:
        item_id = _item_id(seed, item["answer_dir"], item["question_id"])
        key[item_id] = {k: item[k] for k in ("answer_dir", "condition", "question_id")}
        rows.append({"item_id": item_id, "row": "answer", "question": item["question"], "status": item["status"], "gold_units": item["gold"]})
        rows.extend({"item_id": item_id, "row": f"statement-{n}", "statement": s["text"], "cited_units": s["cited"]}
                    for n, s in enumerate(item["statements"], 1))
    with Path(sheet_path).open("w", encoding="utf-8-sig", newline="") as handle:  # BOM so spreadsheet apps read UTF-8.
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    write_json(key_path, {"grading_version": GRADING_VERSION, "seed": seed, "items": key,
                          "failed": {_item_id(seed, f["answer_dir"], f["question_id"]): f for f in failed}, "not_in_questions": outside})
    return {"items": len(pool), "rows": len(rows), "failed_answers": len(failed), "answers_not_in_questions": len(outside)}


def failed_by_condition(key_file):
    """{condition: failed answers} from a key, or None for a key made before failures were recorded."""
    if key_file.get("failed") is None:
        return None
    counts = {}
    for entry in key_file["failed"].values():
        counts[entry["condition"]] = counts.get(entry["condition"], 0) + 1
    return counts


def read_sheet(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _number(value, allowed):
    value = (value or "").strip()
    if value == "":
        return None
    if value not in allowed:
        raise ValueError(f"grade {value!r} is not one of {sorted(allowed)}")
    return int(value)


def grades(sheet_rows):
    """{item_id: {"answer": {...}, "statements": [{...}]}} with grades parsed and range-checked."""
    result = {}
    for row in sheet_rows:
        entry = result.setdefault(row["item_id"], {"answer": {}, "statements": []})
        if row["row"] == "answer":
            entry["answer"] = {"status": row.get("status"), "correctness": _number(row.get("correctness"), {"0", "1", "2"}),
                               "refusal_appropriate": _number(row.get("refusal_appropriate"), {"0", "1"})}
        else:
            entry["statements"].append({"supported": _number(row.get("supported"), {"0", "1", "2"}),
                                        "citation_correct": _number(row.get("citation_correct"), {"0", "1"})})
    return result


def score_sheet(sheet_path, key_path):
    """Per-condition scores of a filled sheet; `failed_answers` (per condition and in total) counts the answers that
    failed before grading, None when the key predates that record."""
    key_file = json.loads(Path(key_path).read_text(encoding="utf-8"))
    key, failed = key_file["items"], failed_by_condition(key_file)
    graded = grades(read_sheet(sheet_path))
    unknown = sorted(set(graded) - set(key))
    if unknown:
        raise ValueError(f"items not in the key: {unknown[:3]}")
    by_condition = {condition: [] for condition in failed or {}}
    for item_id, entry in graded.items():
        by_condition.setdefault(key[item_id]["condition"], []).append(entry)
    mean = lambda values: (sum(values) / len(values) if values else None, len(values))
    report = {}
    for condition, entries in sorted(by_condition.items()):
        statements = [s for e in entries for s in e["statements"]]
        supported = [s["supported"] for s in statements if s["supported"] is not None]
        citations = [s["citation_correct"] for s in statements if s["citation_correct"] is not None]
        correctness = [e["answer"]["correctness"] for e in entries if e["answer"].get("correctness") is not None]
        refusals = [e["answer"]["refusal_appropriate"] for e in entries
                    if e["answer"].get("status") in REFUSED and e["answer"].get("refusal_appropriate") is not None]
        rows = {"citation_support": mean(citations), "grounding_full": mean([v == 2 for v in supported]),
                "grounding_mean": mean([v / 2 for v in supported]), "correctness_mean": mean(correctness),
                "strict_success": mean([v == 2 for v in correctness]), "refusal_appropriate": mean(refusals)}
        report[condition] = {name: {"value": value, "n": n} for name, (value, n) in rows.items()} | {
            "items": len(entries), "failed_answers": None if failed is None else failed.get(condition, 0)}
    outside = key_file.get("not_in_questions")
    return {"grading_version": GRADING_VERSION, "by_condition": report, "failed_answers": None if failed is None else sum(failed.values()),
            "answers_not_in_questions": None if outside is None else len(outside)}


SHEET_METRICS = ("citation_support", "grounding_full", "grounding_mean", "correctness", "strict_success", "refusal_appropriate")


def item_scores(sheet_path):
    """{item_id: metrics} of a filled sheet, for paired statistics; a metric is None when nothing of it is graded.
    Statement metrics are the item's own share of graded statements, so their mean over items differs from
    `score_sheet`, which pools the statements of a condition; `correctness` keeps the 0-2 scale."""
    share = lambda values: sum(values) / len(values) if values else None
    result = {}
    for item_id, entry in grades(read_sheet(sheet_path)).items():
        supported = [s["supported"] for s in entry["statements"] if s["supported"] is not None]
        citations = [s["citation_correct"] for s in entry["statements"] if s["citation_correct"] is not None]
        correctness = entry["answer"].get("correctness")
        refusal = entry["answer"].get("refusal_appropriate") if entry["answer"].get("status") in REFUSED else None
        result[item_id] = {"citation_support": share(citations), "grounding_full": share([v == 2 for v in supported]),
                           "grounding_mean": share([v / 2 for v in supported]), "correctness": correctness,
                           "strict_success": None if correctness is None else float(correctness == 2),
                           "refusal_appropriate": None if refusal is None else float(refusal)}
    return result


def agreement(first_sheet, second_sheet, key_path=None):
    """Cohen's kappa between two filled sheets of the same items (e.g. a person and the judge). Items only one sheet
    holds are listed in `unpaired_items`; with the key, `failed_answers` gives the answers never graded per condition."""
    a, b = grades(read_sheet(first_sheet)), grades(read_sheet(second_sheet))
    pairs = {"supported": [], "citation_correct": [], "correctness": []}
    for item_id in sorted(set(a) & set(b)):
        for x, y in zip(a[item_id]["statements"], b[item_id]["statements"]):
            for name in ("supported", "citation_correct"):
                if x[name] is not None and y[name] is not None:
                    pairs[name].append((x[name], y[name]))
        x, y = a[item_id]["answer"].get("correctness"), b[item_id]["answer"].get("correctness")
        if x is not None and y is not None:
            pairs["correctness"].append((x, y))
    result = {name: {"kappa": kappa([p[0] for p in values], [p[1] for p in values]) if values else None, "n": len(values)}
              for name, values in pairs.items()}
    result["unpaired_items"] = {"first_only": sorted(set(a) - set(b)), "second_only": sorted(set(b) - set(a))}
    if key_path:
        result["failed_answers"] = failed_by_condition(json.loads(Path(key_path).read_text(encoding="utf-8")))
    return result


JUDGE_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["statements", "correctness", "refusal_appropriate"], "properties": {
    "statements": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["supported", "citation_correct"],
                                              "properties": {"supported": {"type": "integer", "enum": [0, 1, 2]}, "citation_correct": {"type": "boolean"}}}},
    "correctness": {"type": "integer", "enum": [0, 1, 2]},
    "refusal_appropriate": {"type": ["boolean", "null"]}}}


def usage_totals(rows):
    """Calls, ok/error counts, cost and token totals of ledger rows (`usage`, `cost_usd`, `duration_ms`, `status` per call);
    a missing cost counts as zero and is listed in `calls_without_cost`."""
    totals = {"calls": len(rows), "ok": sum(r.get("status") == "ok" for r in rows), "error": sum(r.get("status") != "ok" for r in rows),
              "cost_usd": round(sum(r.get("cost_usd") or 0 for r in rows), 6), "calls_without_cost": sum(r.get("cost_usd") is None for r in rows),
              "duration_ms": sum(r.get("duration_ms") or 0 for r in rows)}
    for name in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
        totals[name] = sum((r.get("usage") or {}).get(name) or 0 for r in rows)
    return totals


def call_record(answer, error=None):
    """The accounting fields of one provider answer (or of a failed call): status, usage, cost, duration, serving model."""
    answer = answer or {}
    return {"status": "ok" if error is None else "error", "usage": answer.get("usage"), "cost_usd": answer.get("cost_usd"),
            "duration_ms": answer.get("duration_ms"), "served_by": answer.get("model")}


def judge_sheet(sheet_path, provider, output_path, prompt="judge-v1.md", log=None):
    """Fill a copy of a grading sheet with a model's grades (one call per item); rows keep the sheet's order."""
    system, system_sha = system_prompt(prompt)
    rows = read_sheet(sheet_path)
    by_item = {}
    for row in rows:
        by_item.setdefault(row["item_id"], []).append(row)
    filled, failures, ledger = [], 0, []
    for number, (item_id, group) in enumerate(by_item.items(), 1):
        answer, statements = group[0], group[1:]
        request = json.dumps({"question": answer["question"], "gold_units": answer["gold_units"], "status": answer["status"],
                              "statements": [{"text": s["statement"], "cited_units": s["cited_units"]} for s in statements]}, ensure_ascii=False)
        judged, reply = None, None
        try:
            reply = provider.structured(system, request, JUDGE_SCHEMA, purpose="judge")
            judged = reply["output"]
            if len(judged["statements"]) != len(statements):
                judged, error = None, "statement_count_mismatch"
            else:
                error = None
        except ProviderError as exc:
            error = exc.code
        failures += judged is None
        ledger.append({"item_id": item_id, "error": error, "request_sha256": digest(request)}
                      | call_record(reply, error))
        answer = dict(answer)
        if judged:
            answer.update(correctness=str(judged["correctness"]),
                          refusal_appropriate="" if judged["refusal_appropriate"] is None else str(int(judged["refusal_appropriate"])))
        filled.append(answer)
        for row, grade in zip(statements, judged["statements"] if judged else [None] * len(statements)):
            row = dict(row)
            if grade:
                row.update(supported=str(grade["supported"]), citation_correct=str(int(grade["citation_correct"])))
            filled.append(row)
        if log:
            log(f"{number}/{len(by_item)} {item_id}: {'ok' if judged else error}")
    with Path(output_path).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(filled)
    write_json(Path(output_path).with_suffix(".manifest.json"), {"grading_version": GRADING_VERSION, "judge_model": provider.model,
                                                                 "effort": getattr(provider, "effort", None), "prompt": prompt,
                                                                 "system_sha256": system_sha, "sheet_sha256": digest(Path(sheet_path).read_bytes()),
                                                                 "items": len(by_item), "failures": failures, "usage": usage_totals(ledger), "calls": ledger})
    write_jsonl(Path(output_path).with_suffix(".ledger.jsonl"), ledger)
    return {"items": len(by_item), "failures": failures, "usage": usage_totals(ledger)}
