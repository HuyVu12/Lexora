"""Issue decomposition of a question file (`decompose-run-v1`), shared by every retrieval condition.

A legal-practice question often holds several issues (grounds for dismissal, procedure, protected employee,
consequences). One structured model call per question splits it into at most four issues, each with a short
search query in statutory wording. The result is written once to `subqueries.jsonl` and every condition DK1-DK4
reads the same file (`shared.subqueries` of the retrieval run), so the conditions still differ only in how the
knowledge is represented. The model sees only the question, never the corpus. Answers are appended as they
arrive and an interrupted run resumes; the model has no seed, so the file is the record.
"""

from datetime import datetime, timezone
import json
from pathlib import Path

from legal_ai.common.io import canonical, digest, read_jsonl, write_json
from legal_ai.providers.pilot import ProviderError

RUN_VERSION = "decompose-run-v1"
PROMPTS = Path(__file__).resolve().parents[3] / "prompts"
MAX_ISSUES = 4
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["issues"], "properties": {
    "issues": {"type": "array", "minItems": 1, "maxItems": MAX_ISSUES, "items": {
        "type": "object", "additionalProperties": False, "required": ["issue", "query"], "properties": {
            "issue": {"type": "string", "maxLength": 300}, "query": {"type": "string", "maxLength": 200}}}}}}


def clean(output):
    """The issues of one model answer: non-empty strings only, at most MAX_ISSUES; raises ValueError if none."""
    raw = output.get("issues") if isinstance(output, dict) else None
    issues = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict) and isinstance(item.get("issue"), str) and isinstance(item.get("query"), str):
            issue, query = item["issue"].strip()[:300], item["query"].strip()[:200]
            if issue and query:
                issues.append({"issue": issue, "query": query})
    if not issues:
        raise ValueError("no_issues")
    return issues[:MAX_ISSUES]


def load(folder, questions_path=None):
    """{question_id: [issue, ...]} of a finished decomposition run; checks it was made from this question file."""
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if questions_path is not None and manifest["questions_sha256"] != digest(Path(questions_path).read_bytes()):
        raise ValueError("the decomposition run was made from another question file")
    rows = {r["question_id"]: r["issues"] for r in read_jsonl(folder / "subqueries.jsonl") if r.get("error") is None}
    return rows, manifest


def run(questions_path, provider, output, prompt="decompose-v1.md", log=None):
    output = Path(output)
    system = (PROMPTS / prompt).read_text(encoding="utf-8")
    questions = json.loads(Path(questions_path).read_text(encoding="utf-8"))["questions"]
    manifest = {"run_version": RUN_VERSION, "questions_sha256": digest(Path(questions_path).read_bytes()),
                "provider": getattr(provider, "provider", "claude-code"), "model": provider.model, "effort": getattr(provider, "effort", None),
                "prompt": prompt, "system_sha256": digest(system), "schema_sha256": digest(canonical(SCHEMA)), "max_issues": MAX_ISSUES}
    path = output / "manifest.json"
    if path.exists():
        earlier = json.loads(path.read_text(encoding="utf-8"))
        if {k: v for k, v in earlier.items() if k != "created_at"} != manifest:
            raise ValueError("this decomposition run used other inputs, model or settings; use a new directory")
    else:
        if output.exists() and any(output.iterdir()):
            raise ValueError("output must be empty or an earlier decomposition run with the same inputs")
        write_json(path, manifest | {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    rows_path = output / "subqueries.jsonl"
    done = {r["question_id"] for r in read_jsonl(rows_path) if r.get("error") is None} if rows_path.exists() else set()
    counts = {"questions": len(questions), "already_done": 0, "decomposed": 0, "failed": 0}
    with rows_path.open("a", encoding="utf-8") as handle:
        for number, question in enumerate(questions, 1):
            if question["question_id"] in done:
                counts["already_done"] += 1
                continue
            row = {"question_id": question["question_id"]}
            try:
                answer = provider.structured(system, json.dumps({"question": question["question"]}, ensure_ascii=False), SCHEMA, purpose="decompose")
                row |= {"issues": clean(answer["output"]), "served_by": answer.get("model"), "error": None}
                counts["decomposed"] += 1
            except ProviderError as exc:
                row |= {"error": exc.code}
                counts["failed"] += 1
            except ValueError as exc:
                row |= {"error": str(exc)}
                counts["failed"] += 1
            handle.write(canonical(row) + "\n")
            handle.flush()
            if log:
                log(f"{number}/{len(questions)} {question['question_id']}: {len(row.get('issues', [])) or row['error']}")
            if row.get("error") in ("budget_exhausted", "quota_exhausted"):
                break
    return counts


def merge(rankings, depth):
    """Round-robin merge of several [(index, score)] rankings (the question first, then each issue query):
    rank 1 of every query, then rank 2, ...; a record keeps its first position and best score."""
    merged, seen = [], set()
    for rank in range(max((len(r) for r in rankings), default=0)):
        for ranking in rankings:
            if rank < len(ranking) and ranking[rank][0] not in seen:
                seen.add(ranking[rank][0])
                merged.append(ranking[rank])
                if len(merged) >= depth:
                    return merged
    return merged
