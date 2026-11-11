"""A model picks which graph neighbours a question needs (`neighbor-select-v1`), on top of one retrieval run.

The legal-chain graph (`retrieval.legal_chain`) reaches many provisions next to the retrieved ones: about 35 per
question in the dry runs, among which a fifth to a third of the missing gold units lie. Rules (role order, dense
closeness) could not tell which of them a case needs. Here one structured model call per question sees the question
(and its issues, when the retrieval run was decomposed), the first retrieved records and the candidate neighbours,
each labelled with its typed relation ("chế tài đối với S1"), and returns the candidates the answer needs, possibly
none. The candidates come only from the graph and the shown text only from the records; the model chooses, it
writes nothing that reaches the answer.

`select` appends one row per question to `raw.jsonl` as answers arrive (resumable, keyed by the request hash).
`materialize` writes, offline, a retrieval run directory (`run/`) the answer run accepts: the base ranking with the
selected records moved right after the record that reached them, the list length kept, so every condition still
hands over the same number of records and the same token budgets; Recall@K and Recall at token budgets are
recomputed as `run-retrieval` does.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import threading

from legal_ai.common.io import canonical, digest, read_jsonl, write_json, write_jsonl
from legal_ai.evaluation import decompose
from legal_ai.evaluation.retrieval_run import adaptive_budget, check_adaptive, score_top, summarize
from legal_ai.providers.pilot import ProviderError
from legal_ai.retrieval import legal_chain

RUN_VERSION = "neighbor-select-v1"
PROMPT = "neighbor-select-v1.md"
# Grouping by issue (`neighbor-select-v2`): seeds and candidates per decomposed issue, shown grouped, capped per issue.
VERSIONS = {"question": ("neighbor-select-v1", "neighbor-select-v1.md"), "issue": ("neighbor-select-v2", "neighbor-select-v2.md")}
SEEDS_PER_ISSUE, CANDIDATES_PER_ISSUE, SELECT_PER_ISSUE = 2, 8, 2
PROMPTS = Path(__file__).resolve().parents[3] / "prompts"
SEEDS, MAX_CANDIDATES, MAX_SELECT, SKIP_TOP = 5, 30, 4, 10
SEED_CHARS, CANDIDATE_CHARS = 700, 450
FOLLOWED = ("exception", "sanction", "base", "detail", "condition", "procedure", "consequence", "reference")
RELATION_TEXT = {"exception": "ngoại lệ của", "sanction": "chế tài đối với", "base": "quy định gốc mà {seed} hướng dẫn, ngoại lệ hoặc xử phạt",
                 "detail": "hướng dẫn chi tiết của", "condition": "điều kiện, khái niệm dùng cho", "procedure": "thủ tục thực hiện",
                 "consequence": "hệ quả của", "reference": "có dẫn chiếu liên quan tới"}


def _text(record, limit):
    text = record.get("generator_text") or record["index_text"]
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " ..."


def relation_label(role, seed_id):
    label = RELATION_TEXT[role]
    return label.format(seed=seed_id) if "{seed}" in label else f"{label} {seed_id}"


def candidates(prediction, records, by_id, edges, seeds=SEEDS, max_candidates=MAX_CANDIDATES, skip_top=SKIP_TOP, seed_ids=None,
               exclude=()):
    """(seed record ids, [{record_id, seed, role}]): neighbours of the first `seeds` ranked records (or of the given
    `seed_ids`) over the typed graph, one record per neighbour Article and seed (the best ranked, else the first in
    source order), none of the first `skip_top` ranked records, of `exclude` or of the seeds, taken round-robin over
    the seeds in role order, at most `max_candidates`."""
    ranked = [r["record_id"] for r in prediction["ranked"]]
    position = {rid: n for n, rid in enumerate(ranked)}
    index = {r["record_id"]: i for i, r in enumerate(records)}
    under = legal_chain._record_index(records)
    seed_ids = list(dict.fromkeys(ranked))[:seeds] if seed_ids is None else list(seed_ids)
    skip = set(ranked[:skip_top]) | set(exclude) | set(seed_ids)
    per_seed = []
    for seed in seed_ids:
        chosen, articles = [], set()
        groups = {}
        for i, role, target in legal_chain.neighbours(index[seed], records, edges, under, FOLLOWED):
            article = legal_chain._article_of(target) or target
            groups.setdefault((article, role), []).append(records[i]["record_id"])
        for (article, role), rids in groups.items():
            if article in articles:
                continue
            free = [rid for rid in rids if rid not in skip]
            if free:
                best = min(free, key=lambda rid: (position.get(rid, len(position)), index[rid]))
                chosen.append({"record_id": best, "seed": seed, "role": role})
                articles.add(article)
        per_seed.append(chosen)
    pool, seen = [], set()
    for step in range(max(map(len, per_seed), default=0)):
        for chosen in per_seed:
            if step < len(chosen) and chosen[step]["record_id"] not in seen and len(pool) < max_candidates:
                pool.append(chosen[step])
                seen.add(chosen[step]["record_id"])
    return seed_ids, pool


def request(question, issues, seed_ids, pool, by_id):
    seeds = {rid: f"S{n}" for n, rid in enumerate(seed_ids, 1)}
    body = {"question": question}
    if issues:
        body["issues"] = issues
    body["found"] = [{"id": seeds[rid], "text": _text(by_id[rid], SEED_CHARS)} for rid in seed_ids]
    body["candidates"] = [{"id": f"C{n}", "relation": relation_label(c["role"], seeds[c["seed"]]), "text": _text(by_id[c["record_id"]], CANDIDATE_CHARS)}
                          for n, c in enumerate(pool, 1)]
    return body


def request_by_issue(question, groups, by_id):
    """`groups`: [(issue text, seed ids, pool)]; issues V1.., seeds S1.. and candidates C1.. numbered across groups."""
    body = {"question": question, "issues": [], "found": [], "candidates": []}
    seeds, n_seed, n_cand = {}, 0, 0
    for g, (issue, seed_ids, pool) in enumerate(groups, 1):
        body["issues"].append({"id": f"V{g}", "issue": issue})
        for rid in seed_ids:
            if rid not in seeds:
                n_seed += 1
                seeds[rid] = f"S{n_seed}"
                body["found"].append({"id": seeds[rid], "issue": f"V{g}", "text": _text(by_id[rid], SEED_CHARS)})
        for c in pool:
            n_cand += 1
            body["candidates"].append({"id": f"C{n_cand}", "issue": f"V{g}", "relation": relation_label(c["role"], seeds[c["seed"]]),
                                       "text": _text(by_id[c["record_id"]], CANDIDATE_CHARS)})
    return body


def schema(n, max_select=MAX_SELECT):
    ids = [f"C{i}" for i in range(1, n + 1)] or ["C0"]
    return {"type": "object", "additionalProperties": False, "required": ["selected"], "properties": {
        "selected": {"type": "array", "maxItems": max_select, "items": {"type": "string", "enum": ids}}}}


def start(retrieval_dir, relation_run, output, model, effort, seeds=SEEDS, max_candidates=MAX_CANDIDATES, max_select=MAX_SELECT,
          grouping="question"):
    output = Path(output)
    base = json.loads((Path(retrieval_dir) / "manifest.json").read_text(encoding="utf-8"))
    if grouping not in VERSIONS:
        raise ValueError(f"grouping must be one of {sorted(VERSIONS)}")
    if grouping == "issue" and not base.get("subqueries"):
        raise ValueError("grouping by issue needs a retrieval run with shared.subqueries")
    version, prompt = VERSIONS[grouping]
    system = (PROMPTS / prompt).read_text(encoding="utf-8")
    manifest = {"run_version": version, "retrieval_run": Path(retrieval_dir).as_posix(), "retrieval_records_sha256": base["records_sha256"],
                "relation_run": Path(relation_run).as_posix(), "relations_sha256": digest((Path(relation_run) / "relations.jsonl").read_bytes()),
                "graph_version": legal_chain.CHAIN_VERSION, "provider": "claude-code", "model": model, "effort": effort, "prompt": prompt,
                "system_sha256": digest(system), "seeds": seeds, "max_candidates": max_candidates, "max_select": max_select, "skip_top": SKIP_TOP,
                **({"grouping": "issue", "seeds_per_issue": SEEDS_PER_ISSUE, "candidates_per_issue": CANDIDATES_PER_ISSUE,
                    "select_per_issue": SELECT_PER_ISSUE} if grouping == "issue" else {}),
                "limitations": ["Candidates are the graph neighbours of the first retrieved records only; a provision the graph does not link is never offered",
                                "The model sees shortened record texts; its choice is not legal advice and is not checked by a person"]}
    path = output / "manifest.json"
    if path.exists():
        earlier = json.loads(path.read_text(encoding="utf-8"))
        if {k: v for k, v in earlier.items() if k != "created_at"} != manifest:
            raise ValueError("this selection run used other inputs or settings; use a new directory")
    else:
        if output.exists() and any(output.iterdir()):
            raise ValueError("output must be empty or an earlier selection run with the same inputs")
        output.mkdir(parents=True, exist_ok=True)
        write_json(path, manifest | {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    return manifest


def _context(output):
    manifest = json.loads((Path(output) / "manifest.json").read_text(encoding="utf-8"))
    retrieval_dir = Path(manifest["retrieval_run"])
    base = json.loads((retrieval_dir / "manifest.json").read_text(encoding="utf-8"))
    records = read_jsonl(retrieval_dir / "records.jsonl")
    by_id = {r["record_id"]: r for r in records}
    units_path, documents_path = Path(base["inputs"]["units"]["path"]), Path(base["inputs"]["documents"]["path"])
    aliases = (base.get("graph") or {}).get("source_aliases") or {"Bộ luật Lao động": "45-2019-qh14"}
    edges = legal_chain.typed_edges(read_jsonl(units_path), read_jsonl(Path(manifest["relation_run"]) / "relations.jsonl"),
                                    read_jsonl(documents_path), aliases)
    questions = {q["question_id"]: q for q in json.loads(Path(base["inputs"]["questions"]["path"]).read_text(encoding="utf-8"))["questions"]}
    issues = decompose.load(base["subqueries"]["path"])[0] if base.get("subqueries") else {}
    predictions = read_jsonl(retrieval_dir / "predictions.jsonl")
    return manifest, base, records, by_id, edges, questions, issues, predictions, aliases


def _ranker(base, records):
    """The base run's own ranking function (same method, BM25 parameters, embedding model and fusion)."""
    from legal_ai.retrieval.bm25 import BM25, tokens
    retrieval = base["retrieval"]
    method = retrieval["method"]
    lexical = BM25([tokens(r["index_text"]) for r in records], k1=retrieval["k1"], b=retrieval["b"]) if method != "dense" else None
    dense = None
    if method != "bm25":
        from legal_ai.retrieval.embeddings import DenseIndex, LocalEmbedder, rrf
        model = base["shared"]["embedding_model"]
        embedder = LocalEmbedder(model["path"], model["name"], model["revision"], model.get("max_seq_length", 1024), cache=model.get("cache"))
        dense = DenseIndex(embedder, [r["index_text"] for r in records])

    def rank(text):
        if method == "bm25":
            return lexical.rank(tokens(text))
        if method == "dense":
            return dense.rank(text)
        return rrf([lexical.rank(tokens(text)), dense.rank(text)], retrieval.get("rrf_c", 60), retrieval.get("rrf_candidates", 30))
    return rank


def plan(output):
    """Per question: seeds, candidate pool and the exact request; shared by `select`, `estimate` and `materialize`.
    Grouped by issue, each issue's own ranking (its search query, ranked as the base run ranks) gives its seeds and
    its candidates are the graph neighbours of those seeds; a question without issues falls back to the first
    records of the merged ranking."""
    manifest, base, records, by_id, edges, questions, issues, predictions, _ = _context(output)
    by_issue = manifest.get("grouping") == "issue"
    rank = _ranker(base, records) if by_issue else None
    rows = []
    for prediction in predictions:
        qid = prediction["question_id"]
        question_issues = issues.get(qid, [])
        if by_issue and question_issues:
            groups, offered, seed_ids, pool = [], set(), [], []
            for number, issue in enumerate(question_issues, 1):
                own_seeds = [records[i]["record_id"] for i, _ in rank(issue["query"])[:SEEDS_PER_ISSUE]]
                _, own = candidates(prediction, records, by_id, edges, max_candidates=CANDIDATES_PER_ISSUE, seed_ids=own_seeds, exclude=offered)
                offered |= {c["record_id"] for c in own}
                groups.append((issue["issue"], own_seeds, own))
                seed_ids += [rid for rid in own_seeds if rid not in seed_ids]
                pool += [c | {"issue": number} for c in own]
            body = request_by_issue(questions[qid]["question"], groups, by_id)
        else:
            seed_ids, pool = candidates(prediction, records, by_id, edges, manifest["seeds"], manifest["max_candidates"])
            body = request(questions[qid]["question"], [i["issue"] for i in question_issues], seed_ids, pool, by_id)
        prompt = json.dumps(body, ensure_ascii=False)
        rows.append({"question_id": qid, "seed_ids": seed_ids, "pool": pool, "prompt": prompt, "key": digest(prompt + manifest["system_sha256"])})
    return rows


def estimate(output):
    rows = plan(output)
    return {"questions": len(rows), "calls": sum(1 for r in rows if r["pool"]), "without_candidates": sum(1 for r in rows if not r["pool"]),
            "mean_candidates": sum(len(r["pool"]) for r in rows) / len(rows) if rows else 0,
            "prompt_chars": sum(len(r["prompt"]) for r in rows)}


def select(output, provider, log=None, workers=1):
    manifest = json.loads((Path(output) / "manifest.json").read_text(encoding="utf-8"))
    system = (PROMPTS / manifest["prompt"]).read_text(encoding="utf-8")
    path = Path(output) / "raw.jsonl"
    done = {r["key"] for r in read_jsonl(path) if r.get("error") is None} if path.exists() else set()
    todo = [r for r in plan(output) if r["pool"] and r["key"] not in done]
    lock, counts = threading.Lock(), {"planned": len(todo), "answered": 0, "failed": 0}

    def one(item):
        row = {"key": item["key"], "question_id": item["question_id"], "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        try:
            answer = provider.structured(system, item["prompt"], schema(len(item["pool"]), manifest["max_select"]), purpose="neighbor_select")
            row |= {"output": answer["output"], "usage": answer.get("usage"), "cost_usd": answer.get("cost_usd"), "error": None}
        except ProviderError as exc:
            row |= {"error": exc.code}
        with lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(canonical(row) + "\n")
            counts["answered" if row["error"] is None else "failed"] += 1
            if log:
                log(f"{item['question_id']}: {row.get('output', {}).get('selected') if row['error'] is None else row['error']}")
        return row

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        list(pool.map(one, todo))
    return counts


def materialize(output):
    """Write `output/run/` as a retrieval run with the selected neighbours moved after their seeds; offline."""
    output = Path(output)
    manifest, base, records, by_id, edges, questions, issues, predictions, aliases = _context(output)
    answers = {}
    raw = output / "raw.jsonl"
    for row in read_jsonl(raw) if raw.exists() else []:
        if row.get("error") is None:
            answers[row["key"]] = row["output"]
    ks = base["recall_k"]
    budgets = sorted(int(b) for b in json.loads((Path(manifest["retrieval_run"]) / "metrics.json").read_text(encoding="utf-8"))["mean_recall_at_tokens"])
    plans = {p["question_id"]: p for p in plan(output)}
    rule = check_adaptive(base["shared"]["adaptive_budget"]) if base["shared"].get("adaptive_budget") else None
    out, stats = [], {"questions": 0, "with_answer": 0, "selected": 0, "missing_answer": 0, "by_role": {}}
    for prediction in predictions:
        p = plans[prediction["question_id"]]
        stats["questions"] += 1
        chosen = []
        if p["pool"]:
            if p["key"] in answers:
                stats["with_answer"] += 1
                ids = list(dict.fromkeys(answers[p["key"]].get("selected", [])))
                chosen = [p["pool"][int(i[1:]) - 1] for i in ids if i[1:].isdigit() and 1 <= int(i[1:]) <= len(p["pool"])]
                if manifest.get("grouping") == "issue":  # At most select_per_issue per issue, in the model's order.
                    per, capped = {}, []
                    for c in chosen:
                        per[c.get("issue")] = per.get(c.get("issue"), 0) + 1
                        if c.get("issue") is None or per[c["issue"]] <= manifest["select_per_issue"]:
                            capped.append(c)
                    stats["dropped_over_issue_cap"] = stats.get("dropped_over_issue_cap", 0) + len(chosen) - len(capped)
                    chosen = capped
            else:
                stats["missing_answer"] += 1
        stats["selected"] += len(chosen)
        for c in chosen:
            stats["by_role"][c["role"]] = stats["by_role"].get(c["role"], 0) + 1
        moved = {c["record_id"]: c for c in chosen}
        after = {}
        present = {r["record_id"] for r in prediction["ranked"]}
        for c in chosen:  # A seed outside the base list (rare, issue seeds): the neighbour follows the first record.
            anchor = c["seed"] if c["seed"] in present else prediction["ranked"][0]["record_id"]
            if anchor != c["seed"]:
                stats["seed_outside_list"] = stats.get("seed_outside_list", 0) + 1
            after.setdefault(anchor, []).append(c)
        base_rows = {r["record_id"]: r for r in prediction["ranked"]}
        ranked, depth = [], len(prediction["ranked"])
        for r in prediction["ranked"]:
            if r["record_id"] in moved:
                continue
            ranked.append({k: v for k, v in r.items() if k not in ("rank", "via_reference_from", "via_role")})
            for c in after.get(r["record_id"], []):
                rec = by_id[c["record_id"]]
                kept = base_rows.get(c["record_id"], {"score": 0.0})
                ranked.append({"record_id": rec["record_id"], "score": kept["score"], "unit_ids": rec["unit_ids"], "token_count": rec["token_count"],
                               "via_reference_from": c["seed"], "via_role": c["role"]})
        ranked = ranked[:depth]
        for n, r in enumerate(ranked, 1):
            r["rank"] = n
        top = [by_id[r["record_id"]] for r in ranked]
        row = {k: prediction[k] for k in ("question_id", "family_id", "split", "expected_status", "gold_unit_ids")}
        out.append(row | {"ranked": ranked} | score_top(top, prediction["gold_unit_ids"], ks, budgets,
                                                     adaptive_budget(rule, len(issues.get(prediction["question_id"], []))) if rule else None))
    run = output / "run"
    run.mkdir(exist_ok=True)
    write_jsonl(run / "records.jsonl", records)
    write_jsonl(run / "predictions.jsonl", out)
    write_jsonl(run / "errors.jsonl", [])
    metrics = summarize(out, ks, budgets, records, base["condition"]["condition"], base["shared"]["top_k"])
    write_json(run / "metrics.json", metrics)
    graph = {"version": manifest["run_version"], "chain": {"relation_run": manifest["relation_run"], "references": True}, "source_aliases": aliases,
             "relations_sha256": manifest["relations_sha256"], "selection_run": output.as_posix(), "model": manifest["model"]}
    write_json(run / "manifest.json", base | {"graph": graph, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                               "status": "exploratory", "model_calls": len(answers), "network": False,
                                               "neighbor_selection": stats})
    write_json(output / "report.json", stats | {"metrics": metrics})
    return stats | {"mean_recall_at_tokens": metrics["mean_recall_at_tokens"], "mean_recall": metrics["mean_recall"]}
