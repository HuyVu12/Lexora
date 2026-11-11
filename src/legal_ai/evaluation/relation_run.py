"""Typed relations between articles of a frozen corpus bundle (`relation-run-v1`), for the knowledge-base graph.

A legal answer joins provisions that rarely cite each other: a rule, its exception, its procedure, its consequence.
For every article (or a seeded sample), `extract` picks candidate articles automatically from the whole corpus
(explicit references first, then the most similar articles by BM25 over the article text, plus, with `dense`, the
nearest articles by a local embedding model, which finds provisions on the same matter worded differently; never
from questions or gold labels) and asks one model which candidates relate to the source and how: exception, procedure,
consequence, condition or detail, each with a short verbatim quote on both sides. Answers are appended to
`raw.jsonl` as they arrive (keyed by the request hash) and an interrupted run resumes.

`materialize` validates offline and deterministically: the target must be one of the offered candidates, the
type one of the five, and both quotes must occur verbatim (whitespace aside) in the source and target articles.
Accepted relations go to `relations.jsonl`; `report.json` counts types and rejection reasons. Accepted means
passing these checks, not a legally verified relation.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import threading
import random
import re
from pathlib import Path

from legal_ai.common.io import canonical, digest, read_jsonl, write_json, write_jsonl
from legal_ai.providers.pilot import ProviderError
from legal_ai.retrieval.bm25 import BM25, tokens
from legal_ai.retrieval.graph import reference_edges

RUN_VERSION = "relation-run-v1"
PROMPT = "relation-llm-v1.md"
PROMPTS = Path(__file__).resolve().parents[3] / "prompts"
TYPES = ("exception", "procedure", "consequence", "condition", "detail")
MAX_CANDIDATES = 10
SOURCE_CHARS, CANDIDATE_CHARS, QUERY_TOKENS = 2400, 900, 300
SEED = "lexora-relations-v1"
DENSE_TEXT_CHARS = 1500  # What the embedding model reads of each article.


def articles(units):
    """[{id, document_id, heading, text}] in corpus order; text is the article with all its clauses and points."""
    by_article, order = {}, []
    for unit in sorted(units, key=lambda u: (u["document_id"], u["source_start"])):
        parts = unit["unit_id"].split("/")
        at = next((n for n, part in enumerate(parts) if part.startswith("article-")), None)
        if at is None:
            continue
        article = "/".join(parts[:at + 1])
        if article not in by_article:
            by_article[article] = {"id": article, "document_id": unit["document_id"], "texts": []}
            order.append(article)
        by_article[article]["texts"].append(unit["text"])
    rows = []
    for article in order:
        text = "".join(by_article[article]["texts"])
        rows.append({"id": article, "document_id": by_article[article]["document_id"], "heading": text.split("\n", 1)[0].strip(), "text": text})
    return rows


def _article_of(unit_id):
    parts = unit_id.split("/")
    at = next((n for n, part in enumerate(parts) if part.startswith("article-")), None)
    return "/".join(parts[:at + 1]) if at is not None else None


def candidates(units, rows, aliases=None, k=MAX_CANDIDATES, dense=0, embedder=None):
    """{article id: [candidate article ids]}: referenced or referencing articles first, then BM25 neighbours (k in
    all), then the `dense` nearest articles by embedding that are not chosen yet."""
    linked = {}
    for source, targets in reference_edges(units, aliases).items():
        a = _article_of(source)
        for target in targets:
            b = _article_of(target)
            if a and b and a != b:
                linked.setdefault(a, []).append(b)
                linked.setdefault(b, []).append(a)
    index = BM25([tokens(r["text"]) for r in rows], k1=1.2, b=0.75)
    found = {}
    for n, row in enumerate(rows):
        chosen = list(dict.fromkeys(linked.get(row["id"], [])))[:k]
        for other, _ in index.rank(tokens(row["text"])[:QUERY_TOKENS]):
            if len(chosen) >= k:
                break
            if other != n and rows[other]["id"] not in chosen:
                chosen.append(rows[other]["id"])
        found[row["id"]] = chosen
    if dense:
        import numpy
        vectors = numpy.asarray(embedder.encode([r["text"][:DENSE_TEXT_CHARS] for r in rows]), dtype="float32")
        similarity = vectors @ vectors.T
        for n, row in enumerate(rows):
            extra = [rows[j]["id"] for j in numpy.argsort(-similarity[n]) if j != n and rows[j]["id"] not in found[row["id"]]]
            found[row["id"]] = found[row["id"]] + extra[:dense]
    return found


def schema(n):
    ids = [f"A{i}" for i in range(1, n + 1)] or ["A1"]
    return {"type": "object", "additionalProperties": False, "required": ["relations"], "properties": {
        "relations": {"type": "array", "maxItems": n or 1, "items": {
            "type": "object", "additionalProperties": False, "required": ["target", "type", "source_quote", "target_quote"], "properties": {
                "target": {"type": "string", "enum": ids}, "type": {"type": "string", "enum": list(TYPES)},
                "source_quote": {"type": "string", "maxLength": 300}, "target_quote": {"type": "string", "maxLength": 300}}}}}}


def request(source, others, chars=CANDIDATE_CHARS):
    return json.dumps({"source": {"heading": source["heading"], "text": source["text"][:SOURCE_CHARS]},
                       "candidates": [{"id": f"A{i}", "heading": o["heading"], "text": o["text"][:chars]} for i, o in enumerate(others, 1)]},
                      ensure_ascii=False)


def sample(rows, n):
    """A seeded sample of article IDs (all articles when n is None)."""
    ids = [r["id"] for r in rows]
    if n is None or n >= len(ids):
        return ids
    return sorted(random.Random(SEED).sample(ids, n), key=ids.index)


def start(bundle, output, model, provider, sample_size=None, dense=0, candidate_chars=CANDIDATE_CHARS, embedding=None):
    output = Path(output)
    units_path = Path(bundle) / "units.jsonl"
    manifest = {"run_version": RUN_VERSION, "bundle": Path(bundle).as_posix(), "units_sha256": digest(units_path.read_bytes()),
                "provider": provider, "model": model, "prompt": PROMPT, "system_sha256": digest((PROMPTS / PROMPT).read_text(encoding="utf-8")),
                "max_candidates": MAX_CANDIDATES, "sample": sample_size, "seed": SEED,
                **({"dense_candidates": dense, "candidate_chars": candidate_chars, "embedding": embedding} if dense or candidate_chars != CANDIDATE_CHARS else {}),
                "limitations": ["Candidates come from references and BM25 similarity; a relation to an article never offered is not found",
                                "Accepted means the quotes and types pass the automatic checks, not a legally verified relation"]}
    path = output / "manifest.json"
    if path.exists():
        earlier = json.loads(path.read_text(encoding="utf-8"))
        if {k: v for k, v in earlier.items() if k != "created_at"} != manifest:
            raise ValueError("this relation run used other inputs, model or settings; use a new directory")
    else:
        if output.exists() and any(output.iterdir()):
            raise ValueError("output must be empty or an earlier relation run with the same inputs")
        write_json(path, manifest | {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    return manifest


def extract(units, provider, output, aliases=None, log=None, workers=1, embedder=None):
    """Call the model for every planned article not yet answered; `workers` calls run at once (the Claude Code CLI
    spends most of a call starting up). Rows are appended under a lock, so the file stays one JSON object per line."""
    output = Path(output)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    rows = articles(units)
    by_id = {r["id"]: r for r in rows}
    dense, chars = manifest.get("dense_candidates", 0), manifest.get("candidate_chars", CANDIDATE_CHARS)
    if dense and embedder is None:
        raise ValueError("this relation run uses dense candidates: give the embedding model")
    offered = candidates(units, rows, aliases, dense=dense, embedder=embedder)
    system = (PROMPTS / PROMPT).read_text(encoding="utf-8")
    raw_path = output / "raw.jsonl"
    done = {r["key"] for r in read_jsonl(raw_path) if r.get("status") == "ok"} if raw_path.exists() else set()
    planned = sample(rows, manifest["sample"])
    counts = {"articles": len(planned), "already_done": 0, "ok": 0, "failed": 0}
    lock, stop = threading.Lock(), threading.Event()
    todo = []
    for article in planned:
        others = [by_id[c] for c in offered[article]]
        text = request(by_id[article], others, chars)
        key = digest(canonical([article, offered[article], text]))
        if key in done:
            counts["already_done"] += 1
        else:
            todo.append((article, others, text, key))
    with raw_path.open("a", encoding="utf-8") as handle:
        def one(item):
            article, others, text, key = item
            if stop.is_set():
                return
            row = {"key": key, "article_id": article, "candidates": offered[article], "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            try:
                answer = provider.structured(system, text, schema(len(others)), purpose="relation-extraction")
                row |= {"status": "ok", "output": answer["output"], "served_by": answer.get("model")}
                if answer.get("raw_content") is not None:
                    row["raw_content"] = answer["raw_content"]
            except ProviderError as exc:
                row |= {"status": "error", "code": exc.code}
            with lock:
                counts["ok" if row["status"] == "ok" else "failed"] += 1
                handle.write(canonical(row) + "\n")
                handle.flush()
                if log:
                    log(f"{counts['ok'] + counts['failed']}/{len(todo)} {article}: {row['status']}")
            if row.get("code") in ("quota_exhausted", "budget_exhausted", "rate_limited"):
                stop.set()
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            list(pool.map(one, todo))
    return counts


def _squash(text):
    return re.sub(r"\s+", " ", text).strip().casefold()


def materialize(units, output):
    """Validate raw.jsonl into relations.jsonl and report.json (offline, deterministic)."""
    output = Path(output)
    by_id = {r["id"]: r for r in articles(units)}
    latest = {}
    for row in read_jsonl(output / "raw.jsonl"):
        if row["article_id"] not in latest or row.get("status") == "ok":
            latest[row["article_id"]] = row
    accepted, reasons, types = [], {}, {}
    for article in sorted(latest):
        row = latest[article]
        if row.get("status") != "ok":
            reasons["call_failed"] = reasons.get("call_failed", 0) + 1
            continue
        seen = set()
        for item in (row["output"].get("relations") if isinstance(row["output"], dict) else None) or []:
            problem = None
            if not isinstance(item, dict):
                problem = "not_an_object"
            else:
                target = item.get("target")
                n = int(target[1:]) if isinstance(target, str) and re.fullmatch(r"A\d+", target) else 0
                if not 1 <= n <= len(row["candidates"]):
                    problem = "target_not_offered"
                elif item.get("type") not in TYPES:
                    problem = "unknown_type"
                elif row["candidates"][n - 1] in seen:
                    problem = "duplicate_target"
                else:
                    target_id = row["candidates"][n - 1]
                    source_q, target_q = _squash(str(item.get("source_quote", ""))), _squash(str(item.get("target_quote", "")))
                    if not source_q or source_q not in _squash(by_id[article]["text"]):
                        problem = "source_quote_not_verbatim"
                    elif not target_q or target_q not in _squash(by_id[target_id]["text"]):
                        problem = "target_quote_not_verbatim"
            if problem:
                reasons[problem] = reasons.get(problem, 0) + 1
                continue
            seen.add(target_id)
            types[item["type"]] = types.get(item["type"], 0) + 1
            accepted.append({"relation_id": digest(canonical([article, target_id, item["type"]]))[:16], "source_article": article,
                             "target_article": target_id, "type": item["type"], "source_quote": item["source_quote"], "target_quote": item["target_quote"]})
    write_jsonl(output / "relations.jsonl", accepted)
    report = {"run_version": RUN_VERSION, "articles_answered": sum(1 for r in latest.values() if r.get("status") == "ok"),
              "articles_planned": len(latest), "accepted": len(accepted), "by_type": dict(sorted(types.items())),
              "rejected": dict(sorted(reasons.items())), "relations_sha256": digest("".join(canonical(r) + "\n" for r in accepted))}
    write_json(output / "report.json", report)
    return report
