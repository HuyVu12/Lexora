"""Cited answers for one retrieval run (`answer-run-v1`) and their automatic scores.

For every question of a retrieval run, the top-K records (the same `top_k` for DK1-DK4) are packed into evidence
blocks E01.. within a token budget, in rank order; a block shows the record's `index_text`, i.e. exactly what the
condition retrieved (fixed chunk, structural unit with its path, or serialized claim). One structured model call
per question returns a status and statements that each cite block IDs; the schema lists only this question's IDs.

Citation gate (the same for every condition): a statement without a citation is removed and counted; an
"answered"/"partial" answer left with no statement becomes "insufficient_evidence". Answers are appended to
`answers.jsonl` as they arrive and an interrupted run resumes; the model has no seed, so the file is the record.

`score` computes what needs no human: refusal behavior against `expected_status`, and whether cited records
cover the gold units. Grounding, citation support and correctness are graded by people (see `answer_sheet`).
"""

from datetime import datetime, timezone
import json
from pathlib import Path

from legal_ai.common.io import canonical, digest, read_jsonl, write_json
from legal_ai.indexing.records import token_spans
from legal_ai.providers.pilot import ProviderError

RUN_VERSION = "answer-run-v1"
PROMPTS = Path(__file__).resolve().parents[3] / "prompts"
ANSWERED, REFUSED = ("answered", "partial"), ("insufficient_evidence", "out_of_scope")
MAX_STATEMENTS = 8


def system_prompt(name):
    text = (PROMPTS / name).read_text(encoding="utf-8")
    return text, digest(text)


def schema(evidence_ids):
    ids = list(evidence_ids) or ["E00"]
    return {"type": "object", "additionalProperties": False, "required": ["status", "statements", "limitations"], "properties": {
        "status": {"type": "string", "enum": list(ANSWERED + REFUSED)},
        "statements": {"type": "array", "maxItems": MAX_STATEMENTS, "items": {
            "type": "object", "additionalProperties": False, "required": ["text", "evidence_ids"], "properties": {
                "text": {"type": "string", "maxLength": 1500},
                "evidence_ids": {"type": "array", "maxItems": 6, "items": {"type": "string", "enum": ids}}}}},
        "limitations": {"type": "array", "maxItems": 4, "items": {"type": "string", "maxLength": 500}}}}


def pack(ranked, records, top_k, budget):
    """Evidence blocks from the first `top_k` ranked records, skipping repeated text, within `budget` tokens.
    The first block is always kept so a long record cannot leave the model with nothing."""
    blocks, seen, used = [], set(), 0
    for item in ranked[:top_k]:
        record = records[item["record_id"]]
        text = record.get("generator_text") or record["index_text"]  # What the generator reads (compact KB claims).
        if text in seen:
            continue
        cost = len(token_spans(text))
        if blocks and used + cost > budget:
            break
        seen.add(text)
        used += cost
        blocks.append({"id": f"E{len(blocks) + 1:02d}", "record_id": record["record_id"], "unit_ids": record["unit_ids"],
                       "token_count": cost, "text": text})
    return blocks


def gate(output, blocks):
    """Apply the citation gate to one model answer; returns the stored answer fields."""
    by_id = {b["id"]: b for b in blocks}
    statements, removed = [], 0
    raw = output.get("statements")
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):  # A chat model may answer with bare strings; they carry no citation.
            removed += 1
            continue
        ids = item.get("evidence_ids")
        cited = [e for e in dict.fromkeys(ids if isinstance(ids, list) else []) if isinstance(e, str) and e in by_id]
        if not cited or not str(item.get("text", "")).strip():
            removed += 1
            continue
        statements.append({"text": str(item["text"]).strip(), "evidence_ids": cited, "record_ids": [by_id[e]["record_id"] for e in cited],
                           "unit_ids": sorted({u for e in cited for u in by_id[e]["unit_ids"]})})
    status = output.get("status") if output.get("status") in ANSWERED + REFUSED else "insufficient_evidence"
    downgraded = status in ANSWERED and not statements
    if status in REFUSED:
        statements = []
    return {"status": "insufficient_evidence" if downgraded else status, "model_status": output.get("status"), "statements": statements,
            "limitations": [str(x) for x in (output.get("limitations") if isinstance(output.get("limitations"), list) else [])][:4],
            "gate": {"uncited_removed": removed, "downgraded_to_insufficient": downgraded}}


def run(retrieval_dir, questions_path, config_path, provider, output, *, split=None, log=None):
    """Answer every question of the retrieval run (optionally one split) not yet in `output/answers.jsonl`."""
    retrieval_dir, output = Path(retrieval_dir), Path(output)
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    retrieval = json.loads((retrieval_dir / "manifest.json").read_text(encoding="utf-8"))
    records = {r["record_id"]: r for r in read_jsonl(retrieval_dir / "records.jsonl")}
    predictions = {p["question_id"]: p for p in read_jsonl(retrieval_dir / "predictions.jsonl")}
    questions = json.loads(Path(questions_path).read_text(encoding="utf-8"))["questions"]
    if split:
        questions = [q for q in questions if q.get("split") == split]
    system, system_sha = system_prompt(config["prompt"])
    # Issues of a decomposed retrieval run go to the generator with the question, the same for every condition.
    issues = {}
    if retrieval.get("subqueries"):
        from legal_ai.evaluation.decompose import load
        issues = load(retrieval["subqueries"]["path"])[0]
    manifest = {"run_version": RUN_VERSION, "condition": retrieval["condition"]["condition"], "retrieval_run": retrieval_dir.as_posix(),
                "retrieval_records_sha256": retrieval["records_sha256"], "questions_sha256": digest(Path(questions_path).read_bytes()),
                "split": split, "provider": getattr(provider, "provider", "claude-code"), "model": provider.model,
                "effort": getattr(provider, "effort", None), "prompt": config["prompt"],
                "system_sha256": system_sha, "top_k": config["top_k"], "context_token_budget": config["context_token_budget"],
                "token_counter": "lexora-syllable-v1"}
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        earlier = json.loads(manifest_path.read_text(encoding="utf-8"))
        if {k: v for k, v in earlier.items() if k != "created_at"} != manifest:
            raise ValueError("this answer run used other inputs, model or settings; use a new directory")
    else:
        if output.exists() and any(output.iterdir()):
            raise ValueError("output must be empty or an earlier answer run with the same inputs")
        write_json(manifest_path, manifest | {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    path = output / "answers.jsonl"
    done = {row["question_id"] for row in read_jsonl(path) if row.get("error") is None} if path.exists() else set()
    counts = {"questions": len(questions), "already_done": 0, "answered": 0, "failed": 0}
    with path.open("a", encoding="utf-8") as handle:
        for number, question in enumerate(questions, 1):
            if question["question_id"] in done:
                counts["already_done"] += 1
                continue
            prediction = predictions.get(question["question_id"])
            if prediction is None:
                raise ValueError(f"question not in the retrieval run: {question['question_id']}")
            blocks = pack(prediction["ranked"], records, config["top_k"], config["context_token_budget"])
            request = {"question": question["question"]}
            if issues.get(question["question_id"]):
                request["issues"] = [i["issue"] for i in issues[question["question_id"]]]
            prompt = json.dumps(request | {"evidence": [{"id": b["id"], "text": b["text"]} for b in blocks]}, ensure_ascii=False)
            row = {"question_id": question["question_id"], "condition": manifest["condition"],
                   "context": [{k: b[k] for k in ("id", "record_id", "unit_ids", "token_count")} for b in blocks],
                   "context_tokens": sum(b["token_count"] for b in blocks), "prompt_sha256": digest(prompt)}
            try:
                answer = provider.structured(system, prompt, schema(b["id"] for b in blocks), purpose="answer")
                row |= gate(answer["output"], blocks) | {"usage": answer.get("usage"), "cost_usd": answer.get("cost_usd"),
                                                         "duration_ms": answer.get("duration_ms"), "served_by": answer.get("model"), "error": None}
                if answer.get("raw_content") is not None:
                    row["raw_content"] = answer["raw_content"]  # Chat models: keep the exact text the answer was parsed from.
                counts["answered"] += 1
            except ProviderError as exc:
                row |= {"error": exc.code}
                counts["failed"] += 1
            handle.write(canonical(row) + "\n")
            handle.flush()
            if log:
                log(f"{number}/{len(questions)} {question['question_id']}: {row.get('status') or row['error']}")
            if row.get("error") == "budget_exhausted":
                break
    return counts


def _covers(unit_ids, gold):
    return any(unit == gold or unit.startswith(gold + "/") for unit in unit_ids)


def _merge(spans):
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def char_precision(cited_records, gold_units):
    """Share of the cited source text (characters, overlaps counted once) that lies inside gold units. Unlike
    "a cited record covers a gold unit", it does not reward a long chunk for containing the answer somewhere."""
    cited, gold = {}, {}
    for row in cited_records:
        cited.setdefault(row["document_id"], []).append((row["source_start"], row["source_end"]))
    for unit in gold_units:
        gold.setdefault(unit["document_id"], []).append((unit["source_start"], unit["source_end"]))
    total = inside = 0
    for document, spans in cited.items():
        for start, end in _merge(spans):
            total += end - start
            inside += sum(max(0, min(end, g_end) - max(start, g_start)) for g_start, g_end in _merge(gold.get(document, [])))
    return inside / total if total else None


def latest_answers(path):
    """The last successful answer per question (a resumed run may hold earlier failed attempts)."""
    rows = {}
    for row in read_jsonl(path):
        if row.get("error") is None or row["question_id"] not in rows:
            rows[row["question_id"]] = row
    return rows


def score(answer_dir, questions_path):
    """Automatic metrics of one answer run; writes and returns metrics.json."""
    answer_dir = Path(answer_dir)
    answers = latest_answers(answer_dir / "answers.jsonl")
    questions = {q["question_id"]: q for q in json.loads(Path(questions_path).read_text(encoding="utf-8"))["questions"]}
    rows = [(questions[qid], a) for qid, a in answers.items() if qid in questions]
    ok = [(q, a) for q, a in rows if a.get("error") is None]
    refuse = [(q, a) for q, a in ok if q.get("expected_status") == "refuse"]
    answer = [(q, a) for q, a in ok if q.get("expected_status") == "answer"]
    manifest = json.loads((answer_dir / "manifest.json").read_text(encoding="utf-8"))
    retrieval = Path(manifest["retrieval_run"])
    records = {r["record_id"]: r for r in read_jsonl(retrieval / "records.jsonl")} if (retrieval / "records.jsonl").exists() else {}
    units_path = Path(json.loads((retrieval / "manifest.json").read_text(encoding="utf-8"))["inputs"]["units"]["path"]) if records else None
    units = {u["unit_id"]: u for u in read_jsonl(units_path)} if units_path and units_path.exists() else {}
    precision, recall, chars = [], [], []
    for q, a in answer:
        gold = q.get("relevant_unit_ids") or []
        cited = [s["unit_ids"] for s in a["statements"]]
        if a["status"] in ANSWERED and gold and cited:
            precision.append(sum(any(_covers(units, g) for g in gold) for units in cited) / len(cited))
            recall.append(sum(any(_covers(units, g) for units in cited) for g in gold) / len(gold))
            ids = {r for s in a["statements"] for r in s.get("record_ids", [])}
            if units and ids <= records.keys() and all(g in units for g in gold):
                chars.append(char_precision([records[r] for r in ids], [units[g] for g in gold]))
    mean = lambda values: sum(values) / len(values) if values else None
    metrics = {
        "run_version": RUN_VERSION, "questions": len(rows), "errors": len(rows) - len(ok),
        "refusal_rate_when_expected": mean([a["status"] in REFUSED for _, a in refuse]), "expected_refusals": len(refuse),
        "false_refusal_rate": mean([a["status"] in REFUSED for _, a in answer]), "expected_answers": len(answer),
        "answered_rate": mean([a["status"] in ANSWERED for _, a in ok]),
        "citation_gold_precision": mean(precision), "citation_gold_recall": mean(recall), "citation_scored_answers": len(precision),
        "citation_gold_char_precision": mean([c for c in chars if c is not None]),
        "uncited_statements_removed": sum(a["gate"]["uncited_removed"] for _, a in ok),
        "downgraded_to_insufficient": sum(a["gate"]["downgraded_to_insufficient"] for _, a in ok),
        "mean_statements": mean([len(a["statements"]) for _, a in ok]), "mean_context_tokens": mean([a["context_tokens"] for _, a in ok]),
        "cost_usd": round(sum(a.get("cost_usd") or 0 for _, a in ok), 4),
        "notes": ["citation_gold_* compares cited records with gold units; it is a proxy, not human-judged citation support",
                  "citation_gold_precision counts a record as right when it contains a gold unit, which favours long records; "
                  "citation_gold_char_precision is the share of cited source characters inside gold units",
                  "grounding and correctness come from the human answer sheet"],
    }
    write_json(answer_dir / "metrics.json", metrics)
    return metrics
