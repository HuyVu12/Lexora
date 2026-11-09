"""Retrieval run for one condition (DK1-DK4): build its index records, rank them with BM25 for every
question and score Recall@K against gold canonical units. No network, no model, no generated answers.

A run directory holds `manifest.json` (inputs, hashes, parameters, environment), `records.jsonl` (the
index), `predictions.jsonl` (ranked records per question), `metrics.json` and `errors.jsonl`.

Recall@K for one question = gold units covered by the top-K records / gold units. A record covers a gold
unit when one of its `unit_ids` is that unit or lies inside it (a Clause of a gold Article). Questions
without gold units (expected refusals) are excluded from the mean and counted. Because a DK1 chunk can
span several units, every K also reports the mean number of index tokens behind the top-K records, so a
higher recall bought with more context stays visible, and Recall at fixed token budgets (`token_budgets`, default
500/1000/2000) takes ranked records while the tokens the generator would read (`index_text`, as the answer run
counts them) fit the budget, so conditions are compared on equal context too.

DK3/DK4 records are either one serialized claim each (`record: claims`, the first design, kept as an ablation) or
the DK2 record of each unit with its claims attached (`record: unit_with_claims`). With a `graph` block the ranking
is expanded over the knowledge base's cross-reference edges (`retrieval.graph`), keeping the list length.

With `shared.subqueries` (a decomposition run, the same for every condition) each question is ranked once as
written and once per issue query, and the rankings are merged round-robin, so every issue gets early records.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess

from legal_ai.common.io import canonical, digest, read_jsonl, write_json, write_jsonl
from legal_ai.indexing.records import RECORD_VERSION, TOKENIZER, check_records, claim_records, fixed_chunks, kb_unit_records, structural_records, token_spans
from legal_ai.evaluation import decompose
from legal_ai.retrieval import graph as kb_graph
from legal_ai.retrieval.bm25 import BM25, tokens
from legal_ai.validation.bundle import validate_bundle

RUN_VERSION = "retrieval-run-v1"
BUILDERS = {"fixed_chunks": "DK1", "structural_units": "DK2", "llm_kb_raw": "DK3", "llm_kb_validated": "DK4"}
KB_FILES = {"llm_kb_raw": "dk3.jsonl", "llm_kb_validated": "dk4.jsonl"}
RECORD_MODES = ("claims", "unit_with_claims")
TOKEN_BUDGETS = (500, 1000, 2000)


def load_bundle(folder):
    folder = Path(folder)
    documents, units, evidence, claims = [read_jsonl(folder / f"{name}.jsonl") for name in ("documents", "units", "evidence", "claims")]
    validate_bundle(documents, units, evidence, claims)
    texts = {}
    for document in documents:
        normalized = json.loads((folder / document["document_id"] / "normalized.json").read_text(encoding="utf-8"))
        texts[document["document_id"]] = normalized["text"]
    return documents, units, texts


def kb_claims(condition, units_path):
    """The DK3 or DK4 claims of the knowledge-base run named by the condition, checked against this bundle."""
    folder = Path(condition["kb_run"])
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest["units_sha256"] != digest(Path(units_path).read_bytes()):
        raise ValueError("the knowledge-base run was extracted from another corpus bundle")
    return read_jsonl(folder / KB_FILES[condition["representation"]])


def build_records(condition, documents, units, texts, units_path=None):
    representation = condition["representation"]
    if BUILDERS.get(representation) != condition["condition"]:
        raise ValueError(f"unsupported condition/representation: {condition['condition']}/{representation}")
    if representation == "fixed_chunks":
        records = fixed_chunks(documents, units, texts, condition["chunk_tokens"], condition["overlap_tokens"])
    elif representation == "structural_units":
        records = structural_records(documents, units, texts, condition["max_tokens"])
    else:
        mode = condition.get("record", "claims")
        if mode not in RECORD_MODES:
            raise ValueError(f"record must be one of {RECORD_MODES}")
        claims = kb_claims(condition, units_path)
        records = (claim_records(condition["condition"], documents, units, texts, claims) if mode == "claims" else
                   kb_unit_records(condition["condition"], documents, units, texts, claims, condition.get("max_tokens", 384),
                                   condition.get("claims_view", "full")))
    if condition.get("graph") and representation not in KB_FILES:
        raise ValueError("graph expansion uses the knowledge base and applies to DK3/DK4 only")
    return check_records(records, texts)


def within_budget(top, budget):
    """The leading records whose generator tokens fit `budget`; the first is always kept, as the answer run does."""
    kept, used = [], 0
    for row in top:
        cost = len(token_spans(row.get("generator_text") or row["index_text"]))
        if kept and used + cost > budget:
            break
        kept.append(row)
        used += cost
    return kept


def _covers(record_units, gold):
    return any(unit == gold or unit.startswith(gold + "/") for unit in record_units)


def _git_state(root):
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root, capture_output=True, text=True, check=True).stdout.strip())
        return {"commit": commit, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


METHODS = ("bm25", "dense", "hybrid")


def run(bundle, questions_path, condition_path, shared_path, output, embedder=None):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("output must be empty: use a new run directory")
    condition = json.loads(Path(condition_path).read_text(encoding="utf-8"))
    shared = json.loads(Path(shared_path).read_text(encoding="utf-8"))
    question_file = json.loads(Path(questions_path).read_text(encoding="utf-8"))
    questions = question_file["questions"]
    retrieval = shared["retrieval"]
    method = retrieval.get("method")
    if method not in METHODS:
        raise ValueError(f"retrieval method must be one of {METHODS}")
    if method != "dense" and retrieval.get("tokenizer") != TOKENIZER:
        raise ValueError(f"BM25 needs tokenizer {TOKENIZER}")
    if method != "bm25" and embedder is None:
        raise ValueError("dense and hybrid retrieval need an embedder (the embeddings extra and the local model)")
    ks = sorted(set(retrieval["recall_k"]) | {shared["top_k"]})
    budgets = sorted(shared.get("token_budgets", TOKEN_BUDGETS))
    graph = kb_graph.check_config(condition["graph"]) if condition.get("graph") else None

    documents, units, texts = load_bundle(bundle)
    known = {unit["unit_id"] for unit in units}
    ids = [q["question_id"] for q in questions]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate question_id")
    missing = sorted({gold for q in questions for gold in q["relevant_unit_ids"] if gold not in known})
    if missing:
        raise ValueError(f"gold units missing from the bundle: {missing[:5]}")

    records = build_records(condition, documents, units, texts, Path(bundle) / "units.jsonl")
    lexical = BM25([tokens(row["index_text"]) for row in records], k1=retrieval["k1"], b=retrieval["b"]) if method != "dense" else None
    dense = None
    if method != "bm25":
        from legal_ai.retrieval.embeddings import DenseIndex, rrf
        dense = DenseIndex(embedder, [row["index_text"] for row in records])
    edges = kb_graph.graph_edges(units, graph["edges"], graph.get("source_aliases")) if graph else None
    subqueries = decompose.load(shared["subqueries"], questions_path)[0] if shared.get("subqueries") else None
    # Deep enough for the largest token budget of the smallest records; predictions keep this depth.
    depth = max(max(ks), 50)
    predictions, errors = [], []
    def rank(text):
        if method == "bm25":
            return lexical.rank(tokens(text))[:depth]
        if method == "dense":
            return dense.rank(text)[:depth]
        return rrf([lexical.rank(tokens(text)), dense.rank(text)], retrieval.get("rrf_c", 60), retrieval.get("rrf_candidates", 30))[:depth]

    for question in questions:
        issues = subqueries.get(question["question_id"]) if subqueries is not None else None
        if subqueries is not None and issues is None:
            errors.append({"question_id": question["question_id"], "code": "no_decomposition"})
        ranked = rank(question["question"])
        if issues:
            ranked = decompose.merge([ranked] + [rank(i["query"]) for i in issues], depth)
        via = {}
        if graph:
            expanded = kb_graph.expand(ranked, records, edges, depth, graph.get("max_neighbors", 2), graph.get("require_match", False))
            via = {i: v for i, _, v in expanded if v is not None}
            ranked = [(i, s) for i, s, _ in expanded]
        top = [records[i] for i, _ in ranked]
        gold = question["relevant_unit_ids"]
        row = {"question_id": question["question_id"], "family_id": question.get("family_id"), "split": question.get("split"),
               "expected_status": question.get("expected_status"), "gold_unit_ids": gold,
               "ranked": [{"rank": n, "record_id": records[i]["record_id"], "score": round(score, 9), "unit_ids": records[i]["unit_ids"],
                           "token_count": records[i]["token_count"],
                           **({"via_reference_from": records[via[i]]["record_id"]} if i in via else {})} for n, (i, score) in enumerate(ranked, 1)],
               "recall": {}, "context_tokens": {}, "recall_at_tokens": {}}
        for k in ks:
            covered = [g for g in gold if any(_covers(r["unit_ids"], g) for r in top[:k])]
            row["recall"][str(k)] = len(covered) / len(gold) if gold else None
            row["context_tokens"][str(k)] = sum(r["token_count"] for r in top[:k])
        for budget in budgets:
            kept = within_budget(top, budget)
            row["recall_at_tokens"][str(budget)] = len([g for g in gold if any(_covers(r["unit_ids"], g) for r in kept)]) / len(gold) if gold else None
        if not ranked:
            errors.append({"question_id": question["question_id"], "code": "no_match"})
        predictions.append(row)

    scored = [row for row in predictions if row["gold_unit_ids"]]
    metrics = {
        "run_version": RUN_VERSION, "condition": condition["condition"], "scored_questions": len(scored),
        "excluded_without_gold": len(predictions) - len(scored), "headline_k": shared["top_k"],
        "mean_recall": {str(k): (sum(r["recall"][str(k)] for r in scored) / len(scored) if scored else None) for k in ks},
        # Share of questions whose gold units are all retrieved: what a multi-provision question needs.
        "mean_complete": {str(k): (sum(r["recall"][str(k)] == 1.0 for r in scored) / len(scored) if scored else None) for k in ks},
        "mean_recall_at_tokens": {str(b): (sum(r["recall_at_tokens"][str(b)] for r in scored) / len(scored) if scored else None) for b in budgets},
        "mean_context_tokens": {str(k): (sum(r["context_tokens"][str(k)] for r in predictions) / len(predictions) if predictions else None) for k in ks},
        "record_count": len(records),
        "mean_record_tokens": sum(r["token_count"] for r in records) / len(records) if records else None,
    }
    root = Path(__file__).resolve().parents[3]
    files = {"units": Path(bundle) / "units.jsonl", "documents": Path(bundle) / "documents.jsonl", "questions": Path(questions_path),
             "condition": Path(condition_path), "shared": Path(shared_path)}
    manifest = {
        "run_version": RUN_VERSION, "record_version": RECORD_VERSION, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "condition": condition, "shared": shared, "tokenizer": TOKENIZER, "retrieval": retrieval, "recall_k": ks,
        "inputs": {name: {"path": path.as_posix(), "sha256": digest(path.read_bytes())} for name, path in files.items()},
        "question_set": {"description": question_file.get("description"), "count": len(questions)},
        "records_sha256": digest("".join(canonical(r) + "\n" for r in records)),
        "status": "exploratory" if shared.get("status") != "frozen" or condition.get("status") != "frozen" else "frozen",
        "subqueries": ({"path": Path(shared["subqueries"]).as_posix(),
                        "sha256": digest((Path(shared["subqueries"]) / "subqueries.jsonl").read_bytes())} if shared.get("subqueries") else None),
        "graph": ({"version": kb_graph.GRAPH_VERSION, **graph, "edge_count": sum(len(v) for v in edges.values())} if graph else None),
        "method": method, "dense": ({**embedder.describe(), "texts_sha256": dense.texts_sha256} if dense else None),
        "network": False, "model_calls": 0,
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "git": _git_state(root)},
        "limitations": ["Retrieval only: no context packing, generation, citation or abstention behavior is scored",
                        "Recall depends on the gold units of the question file; draft questions are not independent gold"],
    }
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "records.jsonl", records)
    write_jsonl(output / "predictions.jsonl", predictions)
    write_jsonl(output / "errors.jsonl", errors)
    write_json(output / "metrics.json", metrics)
    write_json(output / "manifest.json", manifest)
    return metrics
