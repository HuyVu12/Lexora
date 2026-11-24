"""LLM judge of case answers against the real outcome (`outcome-judge-v1`), a supplement to people.

The case set's questions come from real disputes; each carries the legal issues a good answer must settle and a
summary of how the court decided (`issues`, `reference_outcome`). The judge reads a blinded grading sheet made by
`answer_grading.make_sheet` (pooled answer runs in a seeded order, opaque item IDs; the condition is never shown)
and, per item, the question's issues and outcome looked up through the key by question only.

Per statement: `supported` 0/1/2, `citation_correct`, `legal_error` (states or applies the law wrongly).
Per answer: `addressed` 0/1/2 for every issue, `outcome` 0/1/2 (conclusion agrees with the court) and
`correctness` 0/1/2. One call per item; `workers` calls run at once; results are appended to `judged.jsonl`
as they arrive and an interrupted run resumes.

`score` reports per answer model and condition, and paired differences between conditions of the same answer
model (same questions) with a seeded percentile bootstrap over questions. Two runs of one model and condition keep
separate labels; failed answers (listed in the key), unjudged items and questions only one side of a pair has are
counted and listed, never dropped silently.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import threading

from legal_ai.common.io import canonical, digest, read_jsonl, write_json, write_jsonl
from legal_ai.evaluation.answer_grading import call_record, read_sheet, usage_totals
from legal_ai.evaluation.answer_run import REFUSED, system_prompt
from legal_ai.providers.pilot import ProviderError

JUDGE_VERSION = "outcome-judge-v1"
METRICS = ("correctness", "strict_success", "outcome", "issues", "grounding_full", "citation_support", "legal_error_rate", "error_free")


def schema(statements, issues):
    grade = {"type": "integer", "enum": [0, 1, 2]}
    return {"type": "object", "additionalProperties": False, "required": ["statements", "issues", "outcome", "correctness"], "properties": {
        "statements": {"type": "array", "minItems": statements, "maxItems": statements, "items": {
            "type": "object", "additionalProperties": False, "required": ["supported", "citation_correct", "legal_error"],
            "properties": {"supported": grade, "citation_correct": {"type": "boolean"}, "legal_error": {"type": "boolean"}}}},
        "issues": {"type": "array", "minItems": issues, "maxItems": issues, "items": {
            "type": "object", "additionalProperties": False, "required": ["addressed"], "properties": {"addressed": grade}}},
        "outcome": grade, "correctness": grade}}


def _items(sheet_path, key, questions):
    groups = {}
    for row in read_sheet(sheet_path):
        groups.setdefault(row["item_id"], []).append(row)
    items = []
    for item_id, rows in groups.items():
        question = questions[key[item_id]["question_id"]]
        answer, statements = rows[0], rows[1:]
        request = {"question": answer["question"], "issues": question["issues"], "reference_outcome": question["reference_outcome"],
                   "gold_units": answer["gold_units"], "status": answer["status"],
                   "statements": [{"text": s["statement"], "cited_units": s["cited_units"]} for s in statements]}
        items.append({"item_id": item_id, "request": json.dumps(request, ensure_ascii=False), "statements": len(statements),
                      "issues": len(question["issues"])})
    return items


def missing_fields(sheet_path, key, questions):
    """{question_id: [missing field names]} for the questions of the sheet's answers that lack `issues` or `reference_outcome`."""
    missing = {}
    for item_id in {row["item_id"] for row in read_sheet(sheet_path)}:
        qid = key[item_id]["question_id"]
        question = questions.get(qid)
        absent = ["question"] if question is None else [f for f in ("issues", "reference_outcome") if not question.get(f)]
        if absent:
            missing[qid] = absent
    return dict(sorted(missing.items()))


def judge(sheet_path, key_path, questions_path, provider, output, prompt="judge-v2.md", workers=1, log=None):
    """Judge every item of the sheet. Fails before any call (and before touching `output`) when a question lacks `issues`
    or `reference_outcome`; such sets (e.g. complex) are graded with `answer-judge`, which needs only the gold units."""
    output = Path(output)
    key_file = json.loads(Path(key_path).read_text(encoding="utf-8"))
    key = key_file["items"]
    questions = {q["question_id"]: q for q in json.loads(Path(questions_path).read_text(encoding="utf-8"))["questions"]}
    missing = missing_fields(sheet_path, key, questions)
    if missing:
        listed = ", ".join(f"{q} ({'/'.join(f)})" for q, f in missing.items())
        raise ValueError(f"answer-outcome-judge needs issues and reference_outcome on every graded question; missing on {len(missing)}: {listed}. "
                         "For question sets without them (e.g. complex) use answer-judge instead; nothing was called and nothing was written")
    system, system_sha = system_prompt(prompt)
    manifest = {"judge_version": JUDGE_VERSION, "judge_model": provider.model, "effort": getattr(provider, "effort", None), "prompt": prompt,
                "system_sha256": system_sha, "sheet_sha256": digest(Path(sheet_path).read_bytes()),
                "key_sha256": digest(Path(key_path).read_bytes()), "questions_sha256": digest(Path(questions_path).read_bytes())}
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        earlier = json.loads(manifest_path.read_text(encoding="utf-8"))
        if {k: v for k, v in earlier.items() if k != "created_at"} != manifest:
            raise ValueError("this judge run used other inputs, model or settings; use a new directory")
    else:
        if output.exists() and any(output.iterdir()):
            raise ValueError("output must be empty or an earlier judge run with the same inputs")
        output.mkdir(parents=True, exist_ok=True)
        write_json(manifest_path, manifest | {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    path = output / "judged.jsonl"
    done = {row["item_id"] for row in read_jsonl(path) if row.get("error") is None} if path.exists() else set()
    todo = [item for item in _items(sheet_path, key, questions) if item["item_id"] not in done]
    # failed: judge calls that failed; failed_answers: answers that failed before grading, never sent (None for old keys).
    counts = {"items": len(todo) + len(done), "already_done": len(done), "judged": 0, "failed": 0,
              "failed_answers": None if key_file.get("failed") is None else len(key_file["failed"])}
    lock, stop = threading.Lock(), threading.Event()

    def one(item):
        if stop.is_set():
            return
        row = {"item_id": item["item_id"], "request_sha256": digest(item["request"])}
        try:
            answer = provider.structured(system, item["request"], schema(item["statements"], item["issues"]), purpose="judge")
            row |= {"output": answer["output"], "error": None} | call_record(answer)
        except ProviderError as exc:
            row |= {"error": exc.code, "error_detail": str(getattr(exc, "detail", ""))[-300:]} | call_record(None, exc.code)
            if exc.code == "budget_exhausted":
                stop.set()
        with lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(canonical(row) + "\n")
            counts["judged" if row["error"] is None else "failed"] += 1
            if log:
                log(f"{counts['judged'] + counts['failed']}/{len(todo)} {item['item_id']}: {row['error'] or 'ok'}")

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        list(pool.map(one, todo))
    # Accounting over every call this directory has recorded (earlier sessions included); scores never read it.
    calls = list(read_jsonl(path)) if path.exists() else []
    calls = [r | {"status": r.get("status") or ("ok" if r.get("error") is None else "error")} for r in calls]  # Rows of older runs have no status.
    write_jsonl(output / "ledger.jsonl", [{k: r.get(k) for k in ("item_id", "request_sha256", "error", "status", "usage", "cost_usd", "duration_ms", "served_by")}
                                         for r in calls])
    return counts | {"usage": usage_totals(calls)}


def _latest(path):
    rows = {}
    for row in read_jsonl(path):
        if row.get("error") is None or row["item_id"] not in rows:
            rows[row["item_id"]] = row
    return {k: v for k, v in rows.items() if v.get("error") is None}


def item_scores(output, sheet_path):
    """{item_id: metrics} from the judged outputs; refused answers count with zero statements."""
    status = {row["item_id"]: row["status"] for row in read_sheet(sheet_path) if row["row"] == "answer"}
    scores = {}
    for item_id, row in _latest(Path(output) / "judged.jsonl").items():
        out = row["output"]
        statements = out["statements"]
        errors = sum(s["legal_error"] for s in statements)
        scores[item_id] = {"correctness": out["correctness"] / 2, "strict_success": float(out["correctness"] == 2),
                           "outcome": out["outcome"] / 2,
                           "issues": sum(i["addressed"] for i in out["issues"]) / (2 * len(out["issues"])),
                           "grounding_full": sum(s["supported"] == 2 for s in statements) / len(statements) if statements else None,
                           "citation_support": sum(s["citation_correct"] for s in statements) / len(statements) if statements else None,
                           "legal_error_rate": errors / len(statements) if statements else None,
                           "error_free": float(errors == 0),
                           "refused": status.get(item_id) in REFUSED}
    return scores


def _bootstrap(diffs, rounds=5000, seed="lexora-outcome-v1"):
    rng = random.Random(seed)
    n = len(diffs)
    means = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(rounds))
    return means[int(0.025 * rounds)], means[int(0.975 * rounds) - 1]


def run_labels(entries):
    """{answer_dir: (model, label)} for the answer runs of a key: the label is the condition, or, when several runs of
    the same answer model share a condition (e.g. two generations pooled in one sheet), the condition and the run's
    directory name (its full path if the names collide), so no run overwrites another."""
    runs = {}
    for entry in entries:
        if entry["answer_dir"] not in runs:
            model = json.loads((Path(entry["answer_dir"]) / "manifest.json").read_text(encoding="utf-8"))["model"]
            runs[entry["answer_dir"]] = (model, entry["condition"])
    groups = {}
    for answer_dir, (model, condition) in runs.items():
        groups.setdefault((model, condition), []).append(answer_dir)
    labels = {}
    for (model, condition), dirs in groups.items():
        names = [Path(d).name for d in dirs]
        for answer_dir, name in zip(dirs, names):
            suffix = name if names.count(name) == 1 else Path(answer_dir).as_posix()
            labels[answer_dir] = (model, condition if len(dirs) == 1 else f"{condition}:{suffix}")
    return labels


def score(output, sheet_path, key_path, pairs=(("DK1", "DK2"), ("DK2", "DK3"), ("DK3", "DK4"), ("DK1", "DK4"), ("DK2", "DK4"))):
    """Per answer run (labelled by condition, see `run_labels`) and paired differences between conditions of the same
    answer model. Each condition also reports its answer run, the answers that failed before grading (from the key) and
    the items the judge has not graded; each pair lists the questions only one side has, which the pairing leaves out."""
    key_file = json.loads(Path(key_path).read_text(encoding="utf-8"))
    key, failed = key_file["items"], key_file.get("failed")  # Keys made before failures were recorded: unknown (None).
    scores = item_scores(output, sheet_path)
    labels = run_labels(list(key.values()) + list((failed or {}).values()))
    table = {}  # (model, label) -> {question_id: metrics}
    for item_id, metrics in scores.items():
        entry = key[item_id]
        table.setdefault(labels[entry["answer_dir"]], {})[entry["question_id"]] = metrics
    run_of = {label: answer_dir for answer_dir, label in labels.items()}
    count = lambda entries, answer_dir, test=lambda item_id: True: sum(e["answer_dir"] == answer_dir and test(i) for i, e in entries.items())
    report = {"judge_version": JUDGE_VERSION, "items": len(scores), "unjudged": len(set(key) - set(scores)),
              "failed_answers": None if failed is None else len(failed),
              "by_model": {}}
    for model in sorted({m for m, _ in table}):
        block = {"conditions": {}, "paired": {}, "unpaired": {}}
        for (m, label), rows in sorted(table.items()):
            if m != model:
                continue
            answer_dir = run_of[(m, label)]
            block["conditions"][label] = {"n": len(rows)} | {
                name: (lambda v: round(sum(v) / len(v), 4) if v else None)([r[name] for r in rows.values() if r[name] is not None])
                for name in METRICS} | {"answer_dir": answer_dir, "failed_answers": None if failed is None else count(failed, answer_dir),
                                        "unjudged": count(key, answer_dir, lambda item_id: item_id not in scores)}
        for a, b in pairs:
            for la in [l for m, l in table if m == model and l.split(":", 1)[0] == a]:
                for lb in [l for m, l in table if m == model and l.split(":", 1)[0] == b]:
                    if la == lb:
                        continue
                    first, second = table[(model, la)], table[(model, lb)]
                    common = sorted(set(first) & set(second))
                    only = {la: sorted(set(first) - set(second)), lb: sorted(set(second) - set(first))}
                    block["unpaired"][f"{lb}-{la}"] = {"count": sum(len(v) for v in only.values()), "only_in": only}
                    block["paired"][f"{lb}-{la}"] = {}
                    for name in METRICS:
                        qs = [q for q in common if first[q][name] is not None and second[q][name] is not None]
                        if not qs:
                            continue
                        diffs = [second[q][name] - first[q][name] for q in qs]
                        low, high = _bootstrap(diffs)
                        block["paired"][f"{lb}-{la}"][name] = {"n": len(qs), "diff": round(sum(diffs) / len(qs), 4), "ci95": [round(low, 4), round(high, 4)],
                                                               "wins": sum(d > 0 for d in diffs), "losses": sum(d < 0 for d in diffs)}
        report["by_model"][model] = block
    return report
