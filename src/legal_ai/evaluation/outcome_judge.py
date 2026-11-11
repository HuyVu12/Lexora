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
model (same questions) with a seeded percentile bootstrap over questions.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import threading

from legal_ai.common.io import canonical, digest, read_jsonl, write_json
from legal_ai.evaluation.answer_grading import read_sheet
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
        if not question.get("issues") or not question.get("reference_outcome"):
            raise ValueError(f"question without issues or reference_outcome: {question['question_id']}")
        answer, statements = rows[0], rows[1:]
        request = {"question": answer["question"], "issues": question["issues"], "reference_outcome": question["reference_outcome"],
                   "gold_units": answer["gold_units"], "status": answer["status"],
                   "statements": [{"text": s["statement"], "cited_units": s["cited_units"]} for s in statements]}
        items.append({"item_id": item_id, "request": json.dumps(request, ensure_ascii=False), "statements": len(statements),
                      "issues": len(question["issues"])})
    return items


def judge(sheet_path, key_path, questions_path, provider, output, prompt="judge-v2.md", workers=1, log=None):
    output = Path(output)
    key = json.loads(Path(key_path).read_text(encoding="utf-8"))["items"]
    questions = {q["question_id"]: q for q in json.loads(Path(questions_path).read_text(encoding="utf-8"))["questions"]}
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
    counts = {"items": len(todo) + len(done), "already_done": len(done), "judged": 0, "failed": 0}
    lock, stop = threading.Lock(), threading.Event()

    def one(item):
        if stop.is_set():
            return
        row = {"item_id": item["item_id"], "request_sha256": digest(item["request"])}
        try:
            answer = provider.structured(system, item["request"], schema(item["statements"], item["issues"]), purpose="judge")
            row |= {"output": answer["output"], "usage": answer.get("usage"), "served_by": answer.get("model"), "error": None}
        except ProviderError as exc:
            row |= {"error": exc.code, "error_detail": str(getattr(exc, "detail", ""))[-300:]}
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
    return counts


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


def score(output, sheet_path, key_path, pairs=(("DK1", "DK2"), ("DK2", "DK3"), ("DK3", "DK4"), ("DK1", "DK4"), ("DK2", "DK4"))):
    key = json.loads(Path(key_path).read_text(encoding="utf-8"))["items"]
    scores = item_scores(output, sheet_path)
    models = {}
    table = {}  # (model, condition) -> {question_id: metrics}
    for item_id, metrics in scores.items():
        entry = key[item_id]
        if entry["answer_dir"] not in models:
            models[entry["answer_dir"]] = json.loads((Path(entry["answer_dir"]) / "manifest.json").read_text(encoding="utf-8"))["model"]
        table.setdefault((models[entry["answer_dir"]], entry["condition"]), {})[entry["question_id"]] = metrics
    report = {"judge_version": JUDGE_VERSION, "items": len(scores), "by_model": {}}
    for model in sorted({m for m, _ in table}):
        block = {"conditions": {}, "paired": {}}
        for (m, condition), rows in sorted(table.items()):
            if m != model:
                continue
            block["conditions"][condition] = {"n": len(rows)} | {
                name: (lambda v: round(sum(v) / len(v), 4) if v else None)([r[name] for r in rows.values() if r[name] is not None])
                for name in METRICS}
        for a, b in pairs:
            first, second = table.get((model, a)), table.get((model, b))
            if not first or not second:
                continue
            common = sorted(set(first) & set(second))
            block["paired"][f"{b}-{a}"] = {}
            for name in METRICS:
                qs = [q for q in common if first[q][name] is not None and second[q][name] is not None]
                if not qs:
                    continue
                diffs = [second[q][name] - first[q][name] for q in qs]
                low, high = _bootstrap(diffs)
                block["paired"][f"{b}-{a}"][name] = {"n": len(qs), "diff": round(sum(diffs) / len(qs), 4), "ci95": [round(low, 4), round(high, 4)],
                                                     "wins": sum(d > 0 for d in diffs), "losses": sum(d < 0 for d in diffs)}
        report["by_model"][model] = block
    return report
