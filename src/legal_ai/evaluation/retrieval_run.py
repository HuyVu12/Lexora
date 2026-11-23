"""Retrieval run for one condition (DK1-DK4): build its index records, rank them with BM25 for every
question and score Recall@K against gold canonical units. No network, no model, no generated answers.

A run directory holds `manifest.json` (inputs, hashes, parameters, environment), `records.jsonl` (the
index), `predictions.jsonl` (ranked records per question), `metrics.json` and `errors.jsonl`.

Recall@K for one question = gold units covered by the top-K records / gold units. A record covers a gold
unit when one of its `unit_ids` is that unit or lies inside it (a Clause of a gold Article). Questions
without gold units (expected refusals) are excluded from the mean and counted. Because a DK1 chunk can
span several units, every K also reports the mean number of index tokens behind the top-K records, so a
higher recall bought with more context stays visible, and Recall at fixed token budgets (`token_budgets`, default
250 to 6000) packs ranked records with the answer run's own packing function (`indexing.packing`, `context_packing`
P0-P3 in the shared settings; DK1 always P0) while the tokens the generator would read fit the budget, so conditions
are compared on equal context too. `tokens_to_reach` gives, per recall target (`recall_targets`, default 0.4 and 0.8),
the smallest budget at which the mean recall reaches it, computed exactly from every question's packing breakpoints.

Predictions keep enough ranked records to fill the largest budget even with the smallest records (at least 50). The
hybrid ranking is the RRF of the first `rrf_candidates` of each list, followed (when deeper records are needed) by
the remaining records in the order of RRF over the full lists, so the head of the ranking never changes.

DK3/DK4 records are either one serialized claim each (`record: claims`, the first design, kept as an ablation) or
the DK2 record of each unit with its claims attached (`record: unit_with_claims`). With a `graph` block the ranking
is expanded over the knowledge base's cross-reference edges (`retrieval.graph`), keeping the list length; with
`graph.amendments` it is then expanded over amendment edges (`retrieval.amendment_graph`, validity option B of
22/11/2026): DK3 follows them whatever the question's date, a condition with unit-level validity (DK4) only when the
edge is effective by that date, before its unit status filter. Neighbours carry their relation note as `status_note`.
With `index_keys` ({"version": "kb-keys-v1", "aliases": <alias table>}, `record: unit_with_claims` only) every unit
record with claims also gets deterministic key phrases (`indexing.kb_keys`) in its index text, never in what the
generator reads; the manifest records the alias table's hash. `kb-keys-v2` ({..., "model_keys": <keys run>}) adds the
model-written questions of a `kb-keys-gen` run on the same bundle and DK3 claims, under the same rules; the manifest
records that run's hashes. Without `index_keys` the records are those of earlier runs.

With `shared.subqueries` (a decomposition run, the same for every condition) each question is ranked once as
written and once per issue query, and the rankings are merged round-robin, so every issue gets early records.
With `shared.adaptive_budget` ({base, per_issue, max}) every question also gets Recall within a budget that grows
with its number of issues (`adaptive_budget`), the same rule for every condition.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess

from legal_ai.common.io import canonical, digest, read_jsonl, write_json, write_jsonl
from legal_ai.indexing import kb_keys
from legal_ai.indexing.packing import PACKING_VERSION, Packer, condition_mode
from legal_ai.kb.validity import DROP, STATUS_VERSION, VERSIONS as STATUS_VERSIONS, RecordFilter
from legal_ai.indexing.records import RECORD_VERSION, TOKENIZER, check_records, claim_records, fixed_chunks, kb_unit_records, structural_records, token_spans
from legal_ai.evaluation import decompose, evidence_coverage
from legal_ai.retrieval import amendment_graph
from legal_ai.retrieval import graph as kb_graph
from legal_ai.retrieval import legal_chain
from legal_ai.retrieval import norm_query
from legal_ai.retrieval.bm25 import BM25, tokens
from legal_ai.validation.bundle import validate_bundle

RUN_VERSION = "retrieval-run-v1"
BUILDERS = {"fixed_chunks": "DK1", "structural_units": "DK2", "llm_kb_raw": "DK3", "llm_kb_validated": "DK4"}
KB_FILES = {"llm_kb_raw": "dk3.jsonl", "llm_kb_validated": "dk4.jsonl"}
RECORD_MODES = ("claims", "unit_with_claims", "norm_lines")
TOKEN_BUDGETS = (250, 500, 1000, 1500, 2000, 3000, 4000, 6000)
RECALL_TARGETS = (0.4, 0.8)
MIN_DEPTH = 50


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


def index_keys(condition, units_path=None):
    """The `kb_keys.KbKeys` of a condition with `index_keys` ({version: kb-keys-v1, aliases} or {version: kb-keys-v2,
    aliases, model_keys}), else None (the default). For kb-keys-v2 the keys run must match the bundle's units and the
    DK3 claims of the condition's knowledge-base run; its manifest record is kept on the builder as `model_record`."""
    spec = condition.get("index_keys")
    if spec is None:
        return None
    spec = kb_keys.check_config(spec)
    if spec["version"] == kb_keys.KEYS_VERSION:
        return kb_keys.KbKeys(spec["aliases"])
    table, record = kb_keys.load_model_keys(spec["model_keys"], digest(Path(units_path).read_bytes()),
                                            digest((Path(condition["kb_run"]) / "dk3.jsonl").read_bytes()))
    keys = kb_keys.KbKeys(spec["aliases"], table)
    keys.model_record = record
    return keys


def index_keys_record(condition, records, units_path):
    """The manifest record of a condition's `index_keys`: version, alias table hash, records with keys and, for
    kb-keys-v2, the keys run's hashes and the records that got model questions."""
    spec = condition["index_keys"]
    record = {"version": spec["version"], "aliases": Path(spec["aliases"]).as_posix(), "aliases_sha256": digest(Path(spec["aliases"]).read_bytes()),
              "records_with_keys": sum(1 for r in records if r.get("index_keys"))}
    if spec["version"] == kb_keys.MODEL_KEYS_VERSION:
        keys = index_keys(condition, units_path)
        record["model_keys"] = keys.model_record | {
            "records_with_model_keys": sum(1 for r in records if r.get("index_keys") and keys.unit_model_keys(r["unit_ids"][0], r["claim_ids"]))}
    return record


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
        keys = index_keys(condition, units_path)
        if keys is not None and mode != "unit_with_claims":
            raise ValueError("index_keys needs record=unit_with_claims")
        if mode == "norm_lines":  # DK3-q/DK4-q: only units with claims, the generator reads one line per claim.
            from legal_ai.retrieval.norm_query import norm_records
            records = norm_records(condition["condition"], documents, units, texts, claims, condition.get("max_tokens", 384))
        else:
            records = (claim_records(condition["condition"], documents, units, texts, claims) if mode == "claims" else
                       kb_unit_records(condition["condition"], documents, units, texts, claims, condition.get("max_tokens", 384),
                                       condition.get("claims_view", "full"), keys))
    if condition.get("index_keys") is not None and representation not in KB_FILES:
        raise ValueError("index_keys come from the knowledge base and apply to DK3/DK4 only")
    if condition.get("graph") and representation not in KB_FILES:
        raise ValueError("graph expansion uses the knowledge base and applies to DK3/DK4 only")
    return check_records(records, texts)


FLAT = Packer("P0")


def within_budget(top, budget, packer=FLAT):
    """The records the answer run would hand the generator within `budget` (the first is always kept)."""
    return [b["record"] for b in packer.pack(top, budget)["blocks"]]


def rank_depth(records, ks, budgets):
    """Ranked records to keep per question: enough to fill the largest budget even with the smallest records."""
    costs = sorted(len(token_spans(r.get("generator_text") or r["index_text"])) for r in records)
    need, used = 0, 0
    for cost in costs:
        if used > max(budgets, default=0):
            break
        used += cost
        need += 1
    return max(max(ks), MIN_DEPTH, need)


def extend_tail(head, ranked, depth):
    """`head` (an expanded ranking) followed by the ranked records it does not hold, up to `depth`."""
    taken = {i for i, _ in head}
    return (head + [(i, s) for i, s in ranked if i not in taken])[:depth]


def _recall(kept, gold):
    return len([g for g in gold if any(_covers(r["unit_ids"], g) for r in kept)]) / len(gold) if gold else None


def recall_steps(top, gold, packer=FLAT):
    """[(tokens, recall)] of one question at every packed prefix: the context grows only when the budget reaches the
    next record's cost, so these points are where its recall-by-budget curve can change."""
    if not gold:
        return []
    steps, budget = [], 0
    while True:
        packed = packer.pack(top, budget)
        steps.append((packed["tokens"], _recall([b["record"] for b in packed["blocks"]], gold)))
        if packed["next_budget"] is None:
            return steps
        budget = packed["next_budget"]


def tokens_to_reach(step_lists, target):
    """Smallest budget at which the mean recall over questions reaches `target`, or None within the ranked depth."""
    if not step_lists:
        return None

    def recall_at(steps, budget):
        value = steps[0][1]
        for used, recall in steps:
            if used > budget:
                break
            value = recall
        return value
    for budget in sorted({t for steps in step_lists for t, _ in steps}):
        if sum(recall_at(steps, budget) for steps in step_lists) / len(step_lists) >= target - 1e-12:
            return budget
    return None


def _covers(record_units, gold):
    return any(unit == gold or unit.startswith(gold + "/") for unit in record_units)


def check_adaptive(rule):
    """An adaptive budget rule {"base", "per_issue", "max"} (generator tokens): the same rule for every condition."""
    if not isinstance(rule, dict) or set(rule) != {"base", "per_issue", "max"} or any(type(rule[k]) is not int or rule[k] < 0 for k in rule)             or rule["max"] < rule["base"] or rule["base"] < 1:
        raise ValueError("adaptive_budget must be {base, per_issue, max} with non-negative integers, base >= 1 and max >= base")
    return rule


def adaptive_budget(rule, issue_count):
    """Tokens for a question with `issue_count` legal issues (at least one): base + per_issue * issues, capped at max.
    The count comes from the shared decomposition run, never from gold labels, so a complex case gets more context
    by the same rule in every condition."""
    return min(rule["max"], rule["base"] + rule["per_issue"] * max(1, issue_count))


def _overlaps(record_units, targets):
    return any(u == s or u.startswith(s + "/") or s.startswith(u + "/") for u in record_units for s in targets)


def score_top(top, gold, ks, budgets, adaptive=None, packer=FLAT, stale=None, later=None, tree=None):
    """Recall at every K and token budget, and context tokens at every K, of one question's ranked records; with
    `adaptive` (this question's adaptive budget) also the recall within it. Budgets pack records with `packer`.
    With `stale` (units outdated at the question's date) also whether the packed context holds one of them; with
    `later` (units not yet in force at that date) whether it holds a unit of the wrong version, stale or later.
    With `tree` (an `evidence_coverage.EvidenceTree`) also the leaf-complete evidence coverage of the same packed
    context at every budget (`evidence_coverage`, `evidence-coverage-v1`); the legacy values are unchanged."""
    row = {"recall": {}, "context_tokens": {}, "recall_at_tokens": {}}
    if stale:
        row["stale_at_tokens"] = {str(b): any(_overlaps(r["unit_ids"], stale) for r in within_budget(top, b, packer)) for b in budgets}
    if stale or later:
        wrong = list(stale or []) + list(later or [])
        row["wrong_version_at_tokens"] = {str(b): any(_overlaps(r["unit_ids"], wrong) for r in within_budget(top, b, packer)) for b in budgets}
    for k in ks:
        covered = [g for g in gold if any(_covers(r["unit_ids"], g) for r in top[:k])]
        row["recall"][str(k)] = len(covered) / len(gold) if gold else None
        row["context_tokens"][str(k)] = sum(r["token_count"] for r in top[:k])
    covered_at = {}
    for budget in budgets:
        kept = within_budget(top, budget, packer)
        row["recall_at_tokens"][str(budget)] = _recall(kept, gold)
        if tree is not None:
            covered_at[budget] = evidence_coverage.question_coverage(tree, gold, kept)
    if tree is not None:
        row["evidence_coverage"] = evidence_coverage.rows_by_budget(covered_at)
    if adaptive is not None:
        row["adaptive_budget"] = adaptive
        row["recall_at_adaptive"] = _recall(within_budget(top, adaptive, packer), gold)
    return row


def summarize(predictions, ks, budgets, records, condition, headline_k, steps=None, targets=RECALL_TARGETS):
    scored = [row for row in predictions if row["gold_unit_ids"]]
    adaptive = {}
    if predictions and all("adaptive_budget" in row for row in predictions):
        adaptive = {"mean_recall_at_adaptive": sum(r["recall_at_adaptive"] for r in scored) / len(scored) if scored else None,
                    "mean_adaptive_budget": sum(r["adaptive_budget"] for r in predictions) / len(predictions)}
    return adaptive | {
        "run_version": RUN_VERSION, "condition": condition, "scored_questions": len(scored),
        "excluded_without_gold": len(predictions) - len(scored), "headline_k": headline_k,
        "mean_recall": {str(k): (sum(r["recall"][str(k)] for r in scored) / len(scored) if scored else None) for k in ks},
        # Share of questions whose gold units are all retrieved: what a multi-provision question needs.
        "mean_complete": {str(k): (sum(r["recall"][str(k)] == 1.0 for r in scored) / len(scored) if scored else None) for k in ks},
        "mean_recall_at_tokens": {str(b): (sum(r["recall_at_tokens"][str(b)] for r in scored) / len(scored) if scored else None) for b in budgets},
        "mean_complete_at_tokens": {str(b): (sum(r["recall_at_tokens"][str(b)] == 1.0 for r in scored) / len(scored) if scored else None) for b in budgets},
        **({"tokens_to_reach": {str(t): tokens_to_reach([s for s in steps if s], t) for t in targets}} if steps is not None else {}),
        **({"stale_context_rate_at_tokens": {str(b): sum(r["stale_at_tokens"][str(b)] for r in with_stale) / len(with_stale) for b in budgets},
            "questions_with_stale_units": len(with_stale)} if (with_stale := [r for r in predictions if "stale_at_tokens" in r]) else {}),
        # Supplementary to the stale rate: stale units or units not yet in force at the question's date (a past event).
        **({"wrong_version_context_rate_at_tokens": {str(b): sum(r["wrong_version_at_tokens"][str(b)] for r in with_wrong) / len(with_wrong) for b in budgets},
            "questions_with_wrong_version_units": len(with_wrong)} if (with_wrong := [r for r in predictions if "wrong_version_at_tokens" in r]) else {}),
        "mean_context_tokens": {str(k): (sum(r["context_tokens"][str(k)] for r in predictions) / len(predictions) if predictions else None) for k in ks},
        **({"evidence_coverage": evidence_coverage.means([r["evidence_coverage"] for r in scored], budgets)}
           if scored and all("evidence_coverage" in r for r in scored) else {}),
        "record_count": len(records),
        "mean_record_tokens": sum(r["token_count"] for r in records) / len(records) if records else None,
    }


def _git_state(root):
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root, capture_output=True, text=True, check=True).stdout.strip())
        return {"commit": commit, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


METHODS = ("bm25", "dense", "hybrid")


def load_validity(condition, shared, documents, units, bundle):
    """The `Validity` of a condition with a `validity` block ({level: unit|document, amendments: edge run}), or None.
    Unit level drops units that are expired, repealed or not yet effective at the question's date and replaces or notes
    amended ones (DK4 under option B of 22/11/2026; DK2-DK4 in the 16/11 `validity/` configs); document level drops
    records of documents that do not apply on that date (DK1-hl, and DK2/DK3 under option B)."""
    spec = condition.get("validity")
    if not spec:
        return None
    if spec.get("level") not in ("unit", "document") or set(spec) - {"level", "amendments", "status_version"}:
        raise ValueError("validity must be {level: unit|document, amendments?: edge run directory, status_version?}")
    if spec.get("status_version", STATUS_VERSION) not in STATUS_VERSIONS:
        raise ValueError(f"validity.status_version must be one of {STATUS_VERSIONS}")
    if spec["level"] == "unit" and condition["representation"] == "fixed_chunks":
        raise ValueError("a fixed chunk has no unit to filter: use validity level document (DK1-hl)")
    if not shared.get("validity_as_of"):
        raise ValueError("validity needs shared.validity_as_of, the date used for questions without as_of")
    from legal_ai.kb.validity import Validity
    edges, edges_sha = [], None
    if spec.get("amendments"):
        folder = Path(spec["amendments"])
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        if manifest["units_sha256"] != digest((bundle / "units.jsonl").read_bytes()):
            raise ValueError("the amendment edges were resolved against another corpus bundle")
        edges, edges_sha = read_jsonl(folder / "edges.jsonl"), digest((folder / "edges.jsonl").read_bytes())
    validity = Validity(documents, units, edges if spec["level"] == "unit" else (), version=spec.get("status_version", STATUS_VERSION))
    validity.edges_sha256 = edges_sha
    return validity


def validity_of_run(manifest, records):
    """The `RecordFilter` a retrieval run used (None without a validity block), rebuilt from its manifest so the answer
    run packs P2/P3 siblings exactly as the retrieval run scored them; the bundle and the edges must hash as recorded."""
    spec = manifest["condition"].get("validity")
    if not spec:
        return None
    from legal_ai.kb.validity import Validity
    paths = {name: Path(manifest["inputs"][name]["path"]) for name in ("units", "documents")}
    for name, path in paths.items():
        if digest(path.read_bytes()) != manifest["inputs"][name]["sha256"]:
            raise ValueError(f"the bundle {name} changed since the retrieval run")
    edges = []
    if spec.get("amendments") and spec["level"] == "unit":
        path = Path(spec["amendments"]) / "edges.jsonl"
        if digest(path.read_bytes()) != manifest["validity"]["edges_sha256"]:
            raise ValueError("the amendment edges changed since the retrieval run")
        edges = read_jsonl(path)
    validity = Validity(read_jsonl(paths["documents"]), read_jsonl(paths["units"]), edges, version=manifest["validity"]["version"])
    return RecordFilter(validity, spec["level"], records)


def filter_valid(ranked, records, validity, level, as_of):
    """(kept ranking, {index: status note}, dropped count) for one question's date.

    Unit level: a unit whose whole new wording is a unit of the corpus (an amending unit of scope v3, linked by
    `amending_unit_id`) is replaced at its rank by that unit's records; other amended units keep their record with a
    status note, and their amending units follow right after. Amending units obey their own document dates. The rule
    itself is `kb.validity.RecordFilter.admit`, which the packer also applies to P2/P3 siblings."""
    rfilter = getattr(validity, "record_filter", None)
    if rfilter is None or rfilter.level != level or getattr(rfilter, "source", None) is not records:
        rfilter = validity.record_filter = RecordFilter(validity, level, records)
        rfilter.source = records
    kept, notes, dropped, seen = [], {}, 0, set()
    for i, score in ranked:
        if i in seen:
            continue
        admitted = rfilter.admit(i, as_of)
        if not admitted or admitted[0][0] != i:
            dropped += 1
        for n, note in admitted:
            if n in seen:
                continue
            if note:
                notes[n] = note
            seen.add(n)
            kept.append((n, score))
    return kept, notes, dropped


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
    targets = sorted(shared.get("recall_targets", RECALL_TARGETS))
    packing = condition_mode(condition["condition"], shared.get("context_packing"))
    rule = check_adaptive(shared["adaptive_budget"]) if shared.get("adaptive_budget") else None
    chain = legal_chain.check_config(condition["graph"]["chain"]) if condition.get("graph", {}).get("chain") else None
    graph = (kb_graph.check_config(condition["graph"]) if condition.get("graph") and not chain else condition.get("graph"))

    documents, units, texts = load_bundle(bundle)
    validity = load_validity(condition, shared, documents, units, Path(bundle))
    known = {unit["unit_id"] for unit in units}
    ids = [q["question_id"] for q in questions]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate question_id")
    missing = sorted({gold for q in questions for gold in q["relevant_unit_ids"] if gold not in known})
    if missing:
        raise ValueError(f"gold units missing from the bundle: {missing[:5]}")

    records = build_records(condition, documents, units, texts, Path(bundle) / "units.jsonl")
    packer = Packer(packing, records, units, documents)
    lexical = BM25([tokens(row["index_text"]) for row in records], k1=retrieval["k1"], b=retrieval["b"]) if method != "dense" else None
    dense = None
    if method != "bm25":
        from legal_ai.retrieval.embeddings import DenseIndex, rrf
        dense = DenseIndex(embedder, [row["index_text"] for row in records])
    relations = None
    if graph and not chain and "relation" in graph["edges"]:
        folder = Path(graph["relation_run"])
        if json.loads((folder / "manifest.json").read_text(encoding="utf-8"))["units_sha256"] != digest((Path(bundle) / "units.jsonl").read_bytes()):
            raise ValueError("the relation run was made from another corpus bundle")
        relations = [r for r in read_jsonl(folder / "relations.jsonl") if r["type"] in graph.get("relation_types", kb_graph.RELATION_TYPES)]
    edges = kb_graph.graph_edges(units, graph["edges"], graph.get("source_aliases"), relations) if graph and not chain else None
    if chain:
        folder = Path(chain["relation_run"])
        if json.loads((folder / "manifest.json").read_text(encoding="utf-8"))["units_sha256"] != digest((Path(bundle) / "units.jsonl").read_bytes()):
            raise ValueError("the relation run was made from another corpus bundle")
        relations = read_jsonl(folder / "relations.jsonl")
        edges = legal_chain.typed_edges(units, relations, documents, graph.get("source_aliases"), chain.get("references", True))
    # Validity option B (22/11/2026): amendment edges as knowledge-base relations of DK3/DK4. They are followed after the
    # reference expansion; only a condition with unit-level validity (DK4) checks the edge dates per question.
    amend_links, amend_report, amend_sha = None, None, None
    if graph and graph.get("amendments"):
        if chain:
            raise ValueError("graph.amendments is not available with graph.chain")
        spec = amendment_graph.check_config(graph["amendments"])
        amend_edges, amend_sha = amendment_graph.load(spec, Path(bundle) / "units.jsonl")
        amend_links, amend_report = amendment_graph.relations(amend_edges, units)
    amend_dated = (condition.get("validity") or {}).get("level") == "unit"
    units_by_id, documents_by_id = {u["unit_id"]: u for u in units}, {d["document_id"]: d for d in documents}
    concepts = None
    if graph and not chain and "concept" in graph["edges"]:
        concepts = kb_graph.record_concepts(records, kb_graph.concept_keys(kb_claims(condition, Path(bundle) / "units.jsonl")))
    subqueries = decompose.load(shared["subqueries"], questions_path)[0] if shared.get("subqueries") else None
    # Deep enough for the largest token budget of the smallest records; predictions keep this depth.
    depth = rank_depth(records, ks, budgets)
    predictions, errors, steps = [], [], []
    tree = evidence_coverage.EvidenceTree(units)
    # norm-query-v1: every condition ranks with the shared analysis' topic query; DK3-q/DK4-q also filter by its fields.
    analyses = norm_query.load(shared["query_slots"], questions_path)[0] if shared.get("query_slots") else None
    query_filter = condition.get("query")
    if query_filter and (analyses is None or condition.get("record") != "norm_lines" or set(query_filter) != {"aliases"}):
        raise ValueError("a query condition needs record=norm_lines, query={aliases} and shared.query_slots")
    aliases = norm_query.load_aliases(query_filter["aliases"]) if query_filter else None

    def rank(text, limit=depth):
        if method == "bm25":
            return lexical.rank(tokens(text))[:limit]
        if method == "dense":
            return dense.rank(text)[:limit]
        lists = [lexical.rank(tokens(text)), dense.rank(text)]
        fused = rrf(lists, retrieval.get("rrf_c", 60), retrieval.get("rrf_candidates", 30))
        if limit is None or len(fused) < limit:  # Beyond the fused candidates: the rest in full-list RRF order; the head is unchanged.
            head = {i for i, _ in fused}
            fused += [(i, 0.0) for i, _ in rrf(lists, retrieval.get("rrf_c", 60), len(records)) if i not in head]
        return fused[:limit]

    for question in questions:
        issues = subqueries.get(question["question_id"]) if subqueries is not None else None
        if subqueries is not None and issues is None:
            errors.append({"question_id": question["question_id"], "code": "no_decomposition"})
        analysis = analyses.get(question["question_id"]) if analyses is not None else None
        if analyses is not None and analysis is None:
            errors.append({"question_id": question["question_id"], "code": "no_query_slots"})
        text = analysis["topic_query"] if analysis else question["question"]
        if query_filter:  # Filter the whole ranking, then cut: most units hold no passing claim.
            ranked = norm_query.filter_ranked(rank(text, None), records, analysis, aliases)[:depth] if analysis else []
        else:
            ranked = rank(text)
        if issues:
            ranked = decompose.merge([ranked] + [rank(i["query"]) for i in issues], depth)
        via, roles = {}, {}
        if chain:
            affinity = None
            if chain.get("affinity") == "dense":
                if dense is None:
                    raise ValueError("graph.chain.affinity=dense needs dense or hybrid retrieval")
                affinity = {}
                for text in [question["question"]] + [i["query"] for i in issues or []]:
                    for n, (i, _) in enumerate(dense.rank(text)):
                        affinity[i] = min(n, affinity.get(i, n))
            # The graph expands the first MIN_DEPTH candidates (its confirming pool, as before deeper rankings existed);
            # deeper records follow unexpanded, so the head never depends on the budget grid.
            expanded = legal_chain.expand(ranked[:MIN_DEPTH], records, edges, MIN_DEPTH, chain.get("order", legal_chain.DEFAULT_ORDER),
                                           chain.get("max_neighbors", 2), chain.get("seeds"), affinity, chain.get("select", "role"),
                                           chain.get("max_affinity_rank"))
            via = {i: v for i, _, v, _ in expanded if v is not None}
            roles = {i: r for i, _, v, r in expanded if v is not None}
            ranked = extend_tail([(i, s) for i, s, _, _ in expanded], ranked, depth)
        elif graph:
            expanded = kb_graph.expand(ranked[:MIN_DEPTH], records, edges, MIN_DEPTH, graph.get("max_neighbors", 2), graph.get("require_match", False), concepts)
            via = {i: v for i, _, v in expanded if v is not None}
            ranked = extend_tail([(i, s) for i, s, _ in expanded], ranked, depth)
        as_of = question.get("as_of") or shared.get("validity_as_of")
        amended_via = {}
        if amend_links is not None:
            expanded = amendment_graph.expand(ranked[:MIN_DEPTH], records, amend_links, MIN_DEPTH, graph["amendments"].get("max_neighbors", 2),
                                              as_of if amend_dated else None, units_by_id, documents_by_id)
            amended_via = {i: v for i, _, v in expanded if v is not None}
            ranked = extend_tail([(i, s) for i, s, _ in expanded], ranked, depth)
        notes = {i: v["note"] for i, v in amended_via.items()}  # Relation notes; validity notes are added below.
        dropped, unused_claims, question_packer = 0, None, packer
        if validity is not None:
            before = ranked
            ranked, status_notes, dropped = filter_valid(ranked, records, validity, condition["validity"]["level"], as_of)
            kept = {i for i, _ in ranked}
            if condition["representation"] in KB_FILES:  # Claims of records the status filter removed are not used.
                unused_claims = len({c for i, _ in before if i not in kept for c in records[i].get("claim_ids", [])})
            notes = {i: "\n".join(n for n in (notes.get(i), status_notes.get(i)) if n) for i in kept if notes.get(i) or status_notes.get(i)}
            if packer.adds_siblings:  # P2/P3 siblings pass the same validity rule as ranked records.
                question_packer = packer.bind(lambda record, day=as_of: validity.record_filter.admit_record(record, day))
        top = [records[i] | {"status_note": notes[i]} if i in notes else records[i] for i, _ in ranked]
        gold = question["relevant_unit_ids"]
        row = {"question_id": question["question_id"], "family_id": question.get("family_id"), "split": question.get("split"),
               "expected_status": question.get("expected_status"), "gold_unit_ids": gold,
               "ranked": [{"rank": n, "record_id": records[i]["record_id"], "score": round(score, 9), "unit_ids": records[i]["unit_ids"],
                           "token_count": records[i]["token_count"],
                           **({"via_reference_from": records[via[i]]["record_id"]} if i in via else {}),
                           **({"via_role": roles[i]} if i in roles else {}),
                           **({"via_amendment": {"from": records[amended_via[i]["from"]]["record_id"], "edge_id": amended_via[i]["edge_id"],
                                                 "role": amended_via[i]["role"]}} if i in amended_via else {}),
                           **({"status_note": notes[i]} if i in notes else {})} for n, (i, score) in enumerate(ranked, 1)],
               **({"validity": {"as_of": as_of, "as_of_source": "question" if question.get("as_of") else "default", "dropped": dropped,
                                **({"unused_claims": unused_claims} if unused_claims is not None else {})}}
                  if validity is not None else {}),
               **({"amendment_neighbours": len(amended_via)} if amend_links is not None else {}),
               "recall": {}, "context_tokens": {}, "recall_at_tokens": {}}
        row.update(score_top(top, gold, ks, budgets, adaptive_budget(rule, len(issues or [])) if rule else None, question_packer,
                             question.get("stale_unit_ids"), question.get("not_yet_effective_unit_ids"), tree))
        steps.append(recall_steps(top, gold, question_packer))
        if not ranked:
            errors.append({"question_id": question["question_id"], "code": "no_match"})
        predictions.append(row)

    metrics = summarize(predictions, ks, budgets, records, condition["condition"], shared["top_k"], steps, targets)
    metrics["context_packing"] = packing
    root = Path(__file__).resolve().parents[3]
    files = {"units": Path(bundle) / "units.jsonl", "documents": Path(bundle) / "documents.jsonl", "questions": Path(questions_path),
             "condition": Path(condition_path), "shared": Path(shared_path)}
    manifest = {
        "run_version": RUN_VERSION, "record_version": RECORD_VERSION, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "condition": condition, "shared": shared, "tokenizer": TOKENIZER, "retrieval": retrieval, "recall_k": ks,
        "token_budgets": budgets, "evidence_coverage_version": evidence_coverage.VERSION, "rank_depth": depth, "context_packing": {"version": PACKING_VERSION, "mode": packing},
        "validity": ({"version": validity.version, **condition["validity"], "default_as_of": shared.get("validity_as_of"),
                      "edges_sha256": validity.edges_sha256, "undated_edges": validity.undated} if validity is not None else None),
        "inputs": {name: {"path": path.as_posix(), "sha256": digest(path.read_bytes())} for name, path in files.items()},
        "question_set": {"description": question_file.get("description"), "count": len(questions)},
        "records_sha256": digest("".join(canonical(r) + "\n" for r in records)),
        "status": "exploratory" if shared.get("status") != "frozen" or condition.get("status") != "frozen" else "frozen",
        "subqueries": ({"path": Path(shared["subqueries"]).as_posix(),
                        "sha256": digest((Path(shared["subqueries"]) / "subqueries.jsonl").read_bytes())} if shared.get("subqueries") else None),
        **({"query_slots": {"version": norm_query.QUERY_VERSION, "path": Path(shared["query_slots"]).as_posix(),
                            "sha256": digest((Path(shared["query_slots"]) / "query_slots.jsonl").read_bytes())}} if shared.get("query_slots") else {}),
        **({"index_keys": index_keys_record(condition, records, files["units"])} if condition.get("index_keys") else {}),
        **({"query_filter": {"aliases": Path(query_filter["aliases"]).as_posix(),
                             "aliases_sha256": digest(Path(query_filter["aliases"]).read_bytes())}} if query_filter else {}),
        "graph": ({"version": legal_chain.CHAIN_VERSION, **graph, "edge_count": sum(len(v) for v in edges.values()),
                   "relations_sha256": digest((Path(chain["relation_run"]) / "relations.jsonl").read_bytes())} if chain else
                  {"version": kb_graph.GRAPH_VERSION, **graph, "edge_count": sum(len(v) for v in edges.values()),
                   **({"relations_sha256": digest((Path(graph["relation_run"]) / "relations.jsonl").read_bytes())} if relations is not None else {}),
                   **({"amendment_relations": {"version": amendment_graph.AMENDMENT_GRAPH_VERSION, "edges_sha256": amend_sha,
                                               "date_check": amend_dated, **amend_report}} if amend_links is not None else {})}
                  if graph else None),
        "method": method, "dense": ({**embedder.describe(), "texts_sha256": dense.texts_sha256} if dense else None),
        "network": False, "model_calls": 0,
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "git": _git_state(root)},
        "limitations": ["Retrieval only: no generation, citation or abstention behavior is scored",
                        "Recall depends on the gold units of the question file; draft questions are not independent gold"],
    }
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "records.jsonl", records)
    write_jsonl(output / "predictions.jsonl", predictions)
    write_jsonl(output / "errors.jsonl", errors)
    write_json(output / "metrics.json", metrics)
    write_json(output / "manifest.json", manifest)
    return metrics


def rescore_evidence(run_dir):
    """Recompute the `evidence-coverage-v1` metrics of an existing run from its manifest, `records.jsonl` and
    `predictions.jsonl`, without re-ranking: the stored ranking is packed again with the run's own packer (including
    the validity admission of P2/P3 siblings at each question's date) and scored against the bundle named in the
    manifest. Writes `metrics-evidence.json` (means plus every question's values) into the run directory. The packing
    is checked against the run: `legacy_recall_mismatches` counts budgets where the legacy recall does not reproduce."""
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    records = read_jsonl(run_dir / "records.jsonl")
    by_record = {r["record_id"]: r for r in records}
    paths = {name: Path(manifest["inputs"][name]["path"]) for name in ("units", "documents")}
    for name, path in paths.items():
        if digest(path.read_bytes()) != manifest["inputs"][name]["sha256"]:
            raise ValueError(f"the bundle {name} changed since the retrieval run")
    units, documents = read_jsonl(paths["units"]), read_jsonl(paths["documents"])
    budgets = manifest["token_budgets"]
    packer = Packer(manifest["context_packing"]["mode"], records, units, documents)
    rfilter = validity_of_run(manifest, records) if packer.adds_siblings else None
    tree = evidence_coverage.EvidenceTree(units)
    questions, rows, mismatched = {}, [], 0
    for prediction in read_jsonl(run_dir / "predictions.jsonl"):
        top = [by_record[x["record_id"]] | ({"status_note": x["status_note"]} if x.get("status_note") else {}) for x in prediction["ranked"]]
        question_packer = packer
        if rfilter is not None:
            as_of = prediction["validity"]["as_of"]
            question_packer = packer.bind(lambda record, day=as_of: rfilter.admit_record(record, day))
        gold = prediction["gold_unit_ids"]
        covered_at = {}
        for budget in budgets:
            kept = within_budget(top, budget, question_packer)
            covered_at[budget] = evidence_coverage.question_coverage(tree, gold, kept) if gold else None
            if gold and abs(_recall(kept, gold) - prediction["recall_at_tokens"][str(budget)]) > 1e-9:
                mismatched += 1
        row = evidence_coverage.rows_by_budget(covered_at)
        rows.append(row if gold else None)
        questions[prediction["question_id"]] = {"family_id": prediction.get("family_id"), **row}
    result = {"run_version": RUN_VERSION, "evidence_coverage_version": evidence_coverage.VERSION, "run": run_dir.as_posix(),
              "condition": manifest["condition"]["condition"], "context_packing": manifest["context_packing"]["mode"],
              "legacy_recall_mismatches": mismatched, "metrics": evidence_coverage.means([r for r in rows if r], budgets),
              "questions": questions}
    write_json(run_dir / "metrics-evidence.json", result)
    return result
