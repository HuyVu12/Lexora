"""Cited answers for one retrieval run (`answer-run-v1`) and their automatic scores.

For every question of a retrieval run, the top-K records (the same `top_k` for DK1-DK4) are packed into evidence
blocks E01.. within a token budget, in rank order, by the retrieval run's `context_packing` (`indexing.packing`: flat
P0, or grouped per Article P1/P2 with the shared header printed once); a block shows what the condition retrieved
(fixed chunk, structural unit with its path, or the unit with its claims). One structured model call
per question returns a status and statements that each cite block IDs; the schema lists only this question's IDs.

Citation gate (the same for every condition): a statement without a citation is removed and counted; an
"answered"/"partial" answer left with no statement becomes "insufficient_evidence". Answers are appended to
`answers.jsonl` as they arrive and an interrupted run resumes; the model has no seed, so the file is the record.

With `relations_in_context` (a legal-chain retrieval run, `retrieval.legal_chain`), the request also lists the typed
relations between the packed blocks ("E03 là chế tài đối với E01"), derived from the graph, never from the model.

`score` computes what needs no human: refusal behavior against `expected_status`, and whether cited records
cover the gold units. Grounding, citation support and correctness are graded by people (see `answer_sheet`).
"""

from datetime import datetime, timezone
import json
from pathlib import Path

from legal_ai.common.io import canonical, digest, read_jsonl, write_json
from legal_ai.evaluation.retrieval_run import adaptive_budget, check_adaptive
from legal_ai.indexing.packing import Packer, evidence_payload
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


def pack(ranked, records, top_k, budget, packer=None):
    """Evidence blocks from the first `top_k` ranked records within `budget` tokens, packed by `packer`
    (`indexing.packing`, the same function the retrieval run scores budgets with; flat P0 by default).
    The first block is always kept so a long record cannot leave the model with nothing.

    Returns the blocks; `pack_with_groups` also returns the Article groups and the total tokens."""
    return pack_with_groups(ranked, records, top_k, budget, packer)[0]


def pack_with_groups(ranked, records, top_k, budget, packer=None):
    # A ranked item keeps the status note the validity filter gave it, as in the retrieval run's own packing.
    shown = [records[item["record_id"]] | ({"status_note": item["status_note"]} if item.get("status_note") else {}) for item in ranked]
    packed = (packer or Packer("P0")).pack(shown, budget, top_k)
    blocks = [{"id": b["id"], "record_id": b["record"]["record_id"], "unit_ids": b["record"]["unit_ids"], "token_count": b["token_count"],
               "text": b["text"], "group": b["group"], **({"sibling": True} if b["sibling"] else {})} for b in packed["blocks"]]
    return blocks, packed


def packer_for(retrieval, records):
    """The packer of a retrieval run (its `context_packing`, P0 for runs made before packing existed), built from the
    bundle the run pinned; the bundle must still hash to the run's inputs."""
    mode = (retrieval.get("context_packing") or {}).get("mode", "P0")
    if mode == "P0":
        return Packer("P0")
    paths = {name: Path(retrieval["inputs"][name]["path"]) for name in ("units", "documents")}
    for name, path in paths.items():
        if digest(path.read_bytes()) != retrieval["inputs"][name]["sha256"]:
            raise ValueError(f"the bundle {name} changed since the retrieval run")
    return Packer(mode, records, read_jsonl(paths["units"]), read_jsonl(paths["documents"]))


def chain_edges(retrieval):
    """Typed edges of a legal-chain retrieval run, rebuilt from its pinned bundle and relation run, so the answer
    run can tell the generator how its evidence blocks relate (`relations_in_context`)."""
    from legal_ai.retrieval import legal_chain
    chain = (retrieval.get("graph") or {}).get("chain")
    if not chain:
        raise ValueError("relations_in_context needs a retrieval run with graph.chain (legal-chain-v1)")
    units_path, documents_path = Path(retrieval["inputs"]["units"]["path"]), Path(retrieval["inputs"]["documents"]["path"])
    relations_path = Path(chain["relation_run"]) / "relations.jsonl"
    if digest(units_path.read_bytes()) != retrieval["inputs"]["units"]["sha256"] or digest(relations_path.read_bytes()) != retrieval["graph"]["relations_sha256"]:
        raise ValueError("the bundle or relation run changed since the retrieval run")
    return legal_chain.typed_edges(read_jsonl(units_path), read_jsonl(relations_path), read_jsonl(documents_path),
                                   retrieval["graph"].get("source_aliases"), chain.get("references", True))


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
    edges = chain_edges(retrieval) if config.get("relations_in_context") else None
    record_list = list(records.values())
    packer = packer_for(retrieval, record_list)
    # P2 siblings pass the validity rule of the retrieval run at each question's date (`kb.validity.RecordFilter`).
    from legal_ai.evaluation.retrieval_run import validity_of_run
    rfilter = validity_of_run(retrieval, record_list) if packer.mode == "P2" else None
    issues = {}
    if retrieval.get("subqueries"):
        from legal_ai.evaluation.decompose import load
        issues = load(retrieval["subqueries"]["path"])[0]
    manifest = {"run_version": RUN_VERSION, "condition": retrieval["condition"]["condition"], "retrieval_run": retrieval_dir.as_posix(),
                "retrieval_records_sha256": retrieval["records_sha256"], "questions_sha256": digest(Path(questions_path).read_bytes()),
                "split": split, "provider": getattr(provider, "provider", "claude-code"), "model": provider.model,
                "effort": getattr(provider, "effort", None), "prompt": config["prompt"],
                "system_sha256": system_sha, "top_k": config["top_k"], "context_token_budget": config["context_token_budget"],
                "token_counter": "lexora-syllable-v1",
                **({"relations_in_context": retrieval["graph"]["version"]} if edges is not None else {}),
                # Recorded only when not flat, so runs made before packing existed still resume.
                **({"context_packing": retrieval["context_packing"]} if packer.mode != "P0" else {})}
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
            budget = config["context_token_budget"]
            if isinstance(budget, dict):  # Adaptive: grows with the shared decomposition's issue count, as in run-retrieval.
                budget = adaptive_budget(check_adaptive(budget), len(issues.get(question["question_id"], [])))
            question_packer = packer
            if rfilter is not None and rfilter.level == "unit":
                question_packer = packer.bind(lambda record, day=prediction["validity"]["as_of"]: rfilter.admit_record(record, day))
            blocks, packed = pack_with_groups(prediction["ranked"], records, config["top_k"], budget, question_packer)
            request = {"question": question["question"]}
            if issues.get(question["question_id"]):
                request["issues"] = [i["issue"] for i in issues[question["question_id"]]]
            relations = []
            if edges is not None:
                from legal_ai.retrieval.legal_chain import block_relations, relation_lines
                relations = block_relations(blocks, record_list, edges)
                if relations:
                    request["relations"] = relation_lines(relations)
            prompt = json.dumps(request | {"evidence": evidence_payload(packed)}, ensure_ascii=False)
            grouped = packer.mode != "P0"
            row = {"question_id": question["question_id"], "condition": manifest["condition"],
                   "context": [{k: b[k] for k in ("id", "record_id", "unit_ids", "token_count", *(("group", "sibling") if grouped else ())) if k in b}
                               for b in blocks],
                   **({"context_groups": [{"header_tokens": g["header_tokens"]} for g in packed["groups"]]} if grouped else {}),
                   "context_tokens": packed["tokens"], "context_token_budget": budget, "prompt_sha256": digest(prompt),
                   **({"relations": relations} if edges is not None else {})}
            try:
                answer = provider.structured(system, prompt, schema(b["id"] for b in blocks), purpose="answer")
                row |= gate(answer["output"], blocks) | {"usage": answer.get("usage"), "cost_usd": answer.get("cost_usd"),
                                                         "duration_ms": answer.get("duration_ms"), "served_by": answer.get("model"), "error": None}
                if answer.get("raw_content") is not None:
                    row["raw_content"] = answer["raw_content"]  # Chat models: keep the exact text the answer was parsed from.
                counts["answered"] += 1
            except ProviderError as exc:
                row |= {"error": exc.code}
                if getattr(exc, "detail", ""):
                    row["error_detail"] = str(exc.detail)[-300:]  # e.g. the CLI's stderr, to tell a usage limit from a bad answer.
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


def cites_stale(answer, stale_unit_ids):
    """True when a statement of the answer cites a record overlapping a stale unit (the unit, a part or a whole of it)."""
    cited = {u for s in answer.get("statements", []) for u in s["unit_ids"]}
    return any(u == s or u.startswith(s + "/") or s.startswith(u + "/") for u in cited for s in stale_unit_ids)


def verification_load(answers, records, units):
    """What a reader pays to check the citations of the answered statements: cited tokens per statement, and the
    share of citations that point at a single leaf unit (so the claim can be checked against one Clause or Point)."""
    parents = {u["parent_id"] for u in units.values() if u.get("parent_id")}
    leaves = {uid for uid in units if uid not in parents}
    statements = cited_tokens = citations = single = 0
    for answer in answers:
        if answer.get("status") not in ANSWERED:
            continue
        blocks = {b["id"]: b for b in answer.get("context", [])}
        headers = answer.get("context_groups")
        for statement in answer.get("statements", []):
            cited = [blocks[e] for e in statement["evidence_ids"] if e in blocks]
            statements += 1
            cited_tokens += sum(b["token_count"] for b in cited)
            if headers:
                cited_tokens += sum(headers[g]["header_tokens"] for g in {b["group"] for b in cited})
            for block in cited:
                citations += 1
                record_units = (records.get(block["record_id"]) or {}).get("unit_ids", block["unit_ids"])
                single += len([u for u in record_units if u in leaves]) == 1 if leaves else len(record_units) == 1
    return {"cited_tokens_per_statement": cited_tokens / statements if statements else None,
            "single_leaf_citation_rate": single / citations if citations else None, "citations": citations}


def _joined(answer_dir, questions_path):
    """The latest answers of a run joined with their questions, the records and units its retrieval run pinned, and
    the IDs of answers whose question is not in the file (left out of every metric, so callers report them)."""
    answer_dir = Path(answer_dir)
    answers = latest_answers(answer_dir / "answers.jsonl")
    questions = {q["question_id"]: q for q in json.loads(Path(questions_path).read_text(encoding="utf-8"))["questions"]}
    rows = [(questions[qid], a) for qid, a in answers.items() if qid in questions]
    outside = sorted(qid for qid in answers if qid not in questions)
    manifest = json.loads((answer_dir / "manifest.json").read_text(encoding="utf-8"))
    retrieval = Path(manifest["retrieval_run"])
    records = {r["record_id"]: r for r in read_jsonl(retrieval / "records.jsonl")} if (retrieval / "records.jsonl").exists() else {}
    units_path = Path(json.loads((retrieval / "manifest.json").read_text(encoding="utf-8"))["inputs"]["units"]["path"]) if records else None
    units = {u["unit_id"]: u for u in read_jsonl(units_path)} if units_path and units_path.exists() else {}
    return rows, records, units, outside


def _question_metrics(q, a, records, units):
    """Automatic metrics of one successful answer; None where a metric does not apply to the question."""
    refused = float(a["status"] in REFUSED)
    row = {"answered": float(a["status"] in ANSWERED), "refused": refused,
           "refusal_when_expected": refused if q.get("expected_status") == "refuse" else None,
           "false_refusal": refused if q.get("expected_status") == "answer" else None,
           "citation_gold_precision": None, "citation_gold_recall": None, "citation_gold_char_precision": None,
           "statements": len(a["statements"]), "context_tokens": a["context_tokens"],
           "uncited_statements_removed": a["gate"]["uncited_removed"], "downgraded_to_insufficient": float(a["gate"]["downgraded_to_insufficient"]),
           "cost_usd": a.get("cost_usd") or 0,
           # Validity questions: does an answer cite a unit that is outdated at the question's date (H3)?
           "stale_citation": float(cites_stale(a, q["stale_unit_ids"])) if q.get("stale_unit_ids") else None,
           # Supplementary: a cited unit of the wrong version, stale or not yet in force at the date (a past event).
           "wrong_version_citation": (float(cites_stale(a, (q.get("stale_unit_ids") or []) + (q.get("not_yet_effective_unit_ids") or [])))
                                      if q.get("stale_unit_ids") or q.get("not_yet_effective_unit_ids") else None)}
    gold = q.get("relevant_unit_ids") or []
    cited = [s["unit_ids"] for s in a["statements"]]
    if q.get("expected_status") == "answer" and a["status"] in ANSWERED and gold and cited:
        row["citation_gold_precision"] = sum(any(_covers(units, g) for g in gold) for units in cited) / len(cited)
        row["citation_gold_recall"] = sum(any(_covers(units, g) for units in cited) for g in gold) / len(gold)
        ids = {r for s in a["statements"] for r in s.get("record_ids", [])}
        if units and ids <= records.keys() and all(g in units for g in gold):
            row["citation_gold_char_precision"] = char_precision([records[r] for r in ids], [units[g] for g in gold])
    return row


ANSWER_METRICS = ("answered", "refused", "refusal_when_expected", "false_refusal", "citation_gold_precision", "citation_gold_recall",
                  "citation_gold_char_precision", "statements", "context_tokens", "uncited_statements_removed",
                  "downgraded_to_insufficient", "cost_usd", "stale_citation", "wrong_version_citation", "cited_tokens_per_statement",
                  "single_leaf_citation_rate")


def question_scores(answer_dir, questions_path):
    """Per-question automatic metrics of one answer run, for paired statistics; reads only, writes nothing.

    {question_id: {"expected_status", "status", "error", <ANSWER_METRICS>}}: a failed answer keeps its error code and
    has every metric None. The verification load is the answer's own (cited tokens over its statements), so its mean
    over questions differs from `score`'s, which pools all statements of the run. Answers to questions outside the file
    are not in the result; `answers_not_in_questions` lists them."""
    rows, records, units, _ = _joined(answer_dir, questions_path)
    result = {}
    for q, a in rows:
        base = {"expected_status": q.get("expected_status"), "status": a.get("status"), "error": a.get("error")}
        if a.get("error") is not None:
            result[q["question_id"]] = base | dict.fromkeys(ANSWER_METRICS)
            continue
        load = verification_load([a], records, units)
        result[q["question_id"]] = base | _question_metrics(q, a, records, units) | {
            "cited_tokens_per_statement": load["cited_tokens_per_statement"], "single_leaf_citation_rate": load["single_leaf_citation_rate"]}
    return result


def answers_not_in_questions(answer_dir, questions_path):
    """IDs of the run's answers whose question is not in the question file."""
    questions = {q["question_id"] for q in json.loads(Path(questions_path).read_text(encoding="utf-8"))["questions"]}
    return sorted(qid for qid in latest_answers(Path(answer_dir) / "answers.jsonl") if qid not in questions)


def score(answer_dir, questions_path):
    """Automatic metrics of one answer run; writes and returns metrics.json (`question_scores` gives them per question).
    Failed answers count in `errors`; answers to questions outside the file in `answers_not_in_questions`."""
    answer_dir = Path(answer_dir)
    rows, records, units, outside = _joined(answer_dir, questions_path)
    ok = [(q, a) for q, a in rows if a.get("error") is None]
    scored = [_question_metrics(q, a, records, units) for q, a in ok]
    values = lambda name: [row[name] for row in scored if row[name] is not None]
    mean = lambda values: sum(values) / len(values) if values else None
    load = verification_load([a for _, a in ok], records, units)
    if values("stale_citation"):
        load |= {"stale_citation_rate": mean(values("stale_citation")), "questions_with_stale_units": len(values("stale_citation"))}
    if values("wrong_version_citation"):
        load |= {"wrong_version_citation_rate": mean(values("wrong_version_citation")),
                 "questions_with_wrong_version_units": len(values("wrong_version_citation"))}
    metrics = {
        "run_version": RUN_VERSION, "questions": len(rows), "errors": len(rows) - len(ok),
        "answers_not_in_questions": len(outside), "answers_not_in_questions_ids": outside,
        "refusal_rate_when_expected": mean(values("refusal_when_expected")), "expected_refusals": len(values("refusal_when_expected")),
        "false_refusal_rate": mean(values("false_refusal")), "expected_answers": len(values("false_refusal")),
        "answered_rate": mean(values("answered")),
        "citation_gold_precision": mean(values("citation_gold_precision")), "citation_gold_recall": mean(values("citation_gold_recall")),
        "citation_scored_answers": len(values("citation_gold_precision")),
        "citation_gold_char_precision": mean(values("citation_gold_char_precision")),
        "uncited_statements_removed": sum(a["gate"]["uncited_removed"] for _, a in ok),
        "downgraded_to_insufficient": sum(a["gate"]["downgraded_to_insufficient"] for _, a in ok),
        "mean_statements": mean([len(a["statements"]) for _, a in ok]), "mean_context_tokens": mean([a["context_tokens"] for _, a in ok]),
        "cost_usd": round(sum(a.get("cost_usd") or 0 for _, a in ok), 4),
        **load,
        "notes": ["cited_tokens_per_statement: tokens a reader must check per statement (the cited blocks, plus their Article "
                  "header once when the context is grouped); single_leaf_citation_rate: share of citations whose record maps "
                  "to exactly one leaf unit (Article without Clauses, Clause without Points, or Point)","citation_gold_* compares cited records with gold units; it is a proxy, not human-judged citation support",
                  "citation_gold_precision counts a record as right when it contains a gold unit, which favours long records; "
                  "citation_gold_char_precision is the share of cited source characters inside gold units",
                  "grounding and correctness come from the human answer sheet"],
    }
    write_json(answer_dir / "metrics.json", metrics)
    return metrics
