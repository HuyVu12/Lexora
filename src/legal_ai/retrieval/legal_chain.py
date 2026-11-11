"""Legal-chain expansion over typed relations (`legal-chain-v1`), an experimental DK3/DK4 graph mode.

A legal answer joins provisions that rarely share words with the question: a rule, its exception, the decree that
details it, the sanction for breaking it. The plain graph expansion (`retrieval.graph.expand`) follows untyped
edges and, with `require_match`, only keeps neighbours the question already matches, which drops exactly those
provisions. This module follows the typed relations of a relation run (`relation-run-v1`) in a fixed order of
legal roles instead, with no keyword condition, and anchors every relation at the unit its verbatim quotes come
from, so a found Clause brings the Clause that is its exception, not the first Clause of the other Article.

Roles of a neighbour N for a retrieved record S, from a relation (source, target, type), where type names what the
target is for the source (`prompts/relation-llm-v1.md`):

- S on the source side: N is the `type` of S (`exception`, `sanction`, `detail`, `condition`, `procedure`,
  `consequence`);
- S on the target side of a sanction, detail or exception: N is the provision S serves (`base`), e.g. the Labour
  Code rule a sanction punishes; on the target side of the other types N is only `related` (a definition or a
  procedure serves many provisions), which the default order does not follow.

`sanction` is derived without a model: a relation with exactly one end in a document whose title names
administrative sanctions ("xử phạt vi phạm hành chính") is retyped `sanction`, oriented so the sanction article is
the target; the model's own type is kept as `llm_type`. Resolved cross-references (`kb.references`) join as role
`reference`, after every typed role. Nothing here decides which provision prevails or whether one is in force.
"""

import re

from legal_ai.retrieval.graph import reference_edges

CHAIN_VERSION = "legal-chain-v1"
RELATION_TYPES = ("exception", "procedure", "consequence", "condition", "detail")
ROLES = ("exception", "sanction", "base", "detail", "condition", "procedure", "consequence", "reference", "related")
BASE_OF = ("sanction", "detail", "exception")
DEFAULT_ORDER = ("exception", "sanction", "base", "detail", "condition", "procedure", "consequence", "reference")
SANCTION_TITLE = re.compile(r"xử phạt vi phạm hành chính", re.IGNORECASE)

# How a role reads in the generator's context: "E03 là <label> E01".
ROLE_LABELS = {"exception": "ngoại lệ của", "sanction": "chế tài đối với", "detail": "hướng dẫn chi tiết của",
               "condition": "điều kiện, khái niệm dùng cho", "procedure": "thủ tục thực hiện", "consequence": "hệ quả của",
               "reference": "có dẫn chiếu liên quan tới"}


def check_config(chain):
    if not isinstance(chain, dict) or not chain.get("relation_run"):
        raise ValueError("graph.chain needs relation_run")
    order = chain.get("order", list(DEFAULT_ORDER))
    if not order or set(order) - set(ROLES) or len(set(order)) != len(order):
        raise ValueError(f"graph.chain.order must list distinct roles from {ROLES}")
    if type(chain.get("max_neighbors", 2)) is not int or not 1 <= chain.get("max_neighbors", 2) <= 5:
        raise ValueError("graph.chain.max_neighbors must be an integer from 1 to 5")
    if chain.get("affinity") not in (None, "dense"):
        raise ValueError("graph.chain.affinity must be dense or null")
    if chain.get("select", "role") not in ("role", "affinity"):
        raise ValueError("graph.chain.select must be role or affinity")
    if chain.get("max_affinity_rank") is not None and (type(chain["max_affinity_rank"]) is not int or chain["max_affinity_rank"] < 1):
        raise ValueError("graph.chain.max_affinity_rank must be a positive integer or null")
    if chain.get("seeds") is not None and (type(chain["seeds"]) is not int or chain["seeds"] < 1):
        raise ValueError("graph.chain.seeds must be a positive integer or null")
    return chain


def _squash(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def _article_of(unit_id):
    parts = unit_id.split("/")
    at = next((n for n, part in enumerate(parts) if part.startswith("article-")), None)
    return "/".join(parts[:at + 1]) if at is not None else None


def sanction_documents(documents):
    return {d["document_id"] for d in documents if SANCTION_TITLE.search(d.get("title") or "")}


def retype_sanctions(relations, sanction_docs):
    """Relations with exactly one end in a sanction document become `sanction`, sanction article as target."""
    out = []
    for row in relations:
        a, b = row["source_article"].split("/")[0], row["target_article"].split("/")[0]
        if (a in sanction_docs) == (b in sanction_docs):
            out.append(dict(row))
            continue
        if a in sanction_docs:  # The decree article is the source: swap so the sanction is the target.
            row = {**row, "source_article": row["target_article"], "target_article": row["source_article"],
                   "source_quote": row["target_quote"], "target_quote": row["source_quote"]}
        out.append({**row, "type": "sanction", "llm_type": row["type"]})
    return out


def anchor(article, quote, units_by_article, parents):
    """The unit of `article` whose text holds `quote` (whitespace and case aside): a leaf first, then a Clause or
    the Article lead; the Article itself when the quote spans units or is not found."""
    needle = _squash(quote or "")
    if not needle:
        return article
    rows = units_by_article.get(article, [])
    for leaf_only in (True, False):
        for unit in rows:
            if (unit["unit_id"] not in parents) == leaf_only and needle in _squash(unit["text"]):
                return unit["unit_id"]
    return article


def typed_edges(units, relations, documents, aliases=None, with_references=True):
    """{anchor unit_id: [(neighbour anchor unit_id, role, relation)]} in both directions; `relation` is None for a
    plain cross-reference. Anchors are units or Articles (see `anchor`)."""
    parents = {u["parent_id"] for u in units}
    by_article = {}
    for unit in sorted(units, key=lambda u: (u["document_id"], u["source_start"])):
        article = _article_of(unit["unit_id"])
        if article:
            by_article.setdefault(article, []).append(unit)
    edges = {}

    def add(a, b, role, relation):
        if a != b and (b, role) not in {(n, r) for n, r, _ in edges.setdefault(a, [])}:
            edges[a].append((b, role, relation))

    for row in retype_sanctions(relations, sanction_documents(documents)):
        source = anchor(row["source_article"], row.get("source_quote"), by_article, parents)
        target = anchor(row["target_article"], row.get("target_quote"), by_article, parents)
        add(source, target, row["type"], row)
        # Seen from the target, only a sanction, a guiding provision or an exception has a rule it serves; the
        # other way round a condition or procedure would lead to every provision that uses it.
        add(target, source, "base" if row["type"] in BASE_OF else "related", row)
    if with_references:
        for source, targets in reference_edges(units, aliases).items():
            for target in targets:
                add(source, target, "reference", None)
                add(target, source, "reference", None)
    return edges


def _prefixes(unit_id):
    parts = unit_id.split("/")
    return ["/".join(parts[:n]) for n in range(1, len(parts) + 1)]


def _record_index(records):
    under = {}
    for i, row in enumerate(records):
        for unit in row["unit_ids"]:
            for prefix in _prefixes(unit):
                under.setdefault(prefix, []).append(i)
    return under


def neighbours(index, records, edges, under, order):
    """[(record index, role)] reachable from record `index`, by role order, then by neighbour anchor order.
    A record reaches the edges anchored at its own units and at their ancestors (an Article-level relation
    applies to every Clause of the Article)."""
    rank = {role: n for n, role in enumerate(order)}
    found = []
    for unit in records[index]["unit_ids"]:
        for prefix in _prefixes(unit):
            for target, role, _ in edges.get(prefix, []):
                if role in rank:
                    found.append((rank[role], target, role))
    seen, result = set(), []
    for _, target, role in sorted(found, key=lambda x: x[0]):
        for i in under.get(target, []):
            if i != index and i not in seen:
                seen.add(i)
                result.append((i, role, target))
    return result


def expand(ranked, records, edges, depth, order=DEFAULT_ORDER, max_neighbors=2, seeds=None, affinity=None, select="role",
           max_affinity_rank=None):
    """[(record index, score, via, role)] of length <= depth: each ranked record, then up to `max_neighbors`
    records it reaches by role order. Only the first `seeds` ranked records expand (all when None), so the search
    results further down are not all pushed out. Within one neighbour Article, the best ranked record wins, then
    source order; one record per neighbour Article and seed, so a sanction Article with five Points brings one.

    `affinity` ({record index: rank of the record for the question over the whole index}, e.g. the dense ranking)
    makes the choice question-aware without a keyword condition: within an Article the closest record wins; with
    `select="affinity"` neighbour Articles are taken closest first (roles only decide what may be followed), and
    `max_affinity_rank` drops neighbours ranked below it for the question."""
    position = {index: n for n, (index, _) in enumerate(ranked)}
    if select not in ("role", "affinity"):
        raise ValueError("select must be role or affinity")
    closeness = (lambda i: affinity.get(i, len(affinity))) if affinity else (lambda i: position.get(i, len(position)))
    score = dict(ranked)
    under = _record_index(records)
    result, taken, expanded = [], set(), 0
    for index, _ in ranked:
        if len(result) >= depth:
            break
        if index in taken:
            continue
        result.append((index, score[index], None, None))
        taken.add(index)
        if seeds is not None and expanded >= seeds:
            continue
        expanded += 1
        by_anchor = {}
        for i, role, target in neighbours(index, records, edges, under, order):
            article = _article_of(target) or target
            if not any(key[0] == article and key[1] != role for key in by_anchor):
                by_anchor.setdefault((article, role), []).append(i)
        added = 0
        choices = []
        for n, ((target, role), candidates) in enumerate(by_anchor.items()):  # dict keeps the role order of `neighbours`
            free = [i for i in candidates if i not in taken]
            if not free:
                continue
            best = min(free, key=lambda i: (closeness(i), i))
            if max_affinity_rank is not None and closeness(best) >= max_affinity_rank:
                continue
            choices.append((closeness(best) if select == "affinity" else n, best, role))
        for _, best, role in sorted(choices, key=lambda c: (c[0], c[1])):
            if added >= max_neighbors or len(result) >= depth:
                break
            if best in taken:
                continue
            result.append((best, score.get(best, 0.0), index, role))
            taken.add(best)
            added += 1
    return result


def block_relations(blocks, records, edges):
    """Typed relations between the evidence blocks of one answer: [{"from": "E03", "role": "sanction", "to": "E01"}],
    meaning E03 is the sanction for E01. `base` is read from the other side (the sanction, not the rule, carries the
    label); one relation per pair of blocks, the first role in `ROLES` order winning."""
    by_record = {b["record_id"]: b["id"] for b in blocks}
    index = {r["record_id"]: i for i, r in enumerate(records)}
    present = [index[b["record_id"]] for b in blocks if b["record_id"] in index]
    local_records = [records[i] for i in present]
    under = _record_index(local_records)
    found = {}
    for n in range(len(present)):
        for m, role, _ in neighbours(n, local_records, edges, under, ROLES):
            if role in ("base", "related"):
                continue
            a, b = by_record[local_records[m]["record_id"]], by_record[local_records[n]["record_id"]]
            pair = frozenset((a, b))
            if a != b and (pair not in found or ROLES.index(role) < ROLES.index(found[pair]["role"])):
                found[pair] = {"from": a, "role": role, "to": b}
    return sorted(found.values(), key=lambda r: (ROLES.index(r["role"]), r["from"], r["to"]))


def relation_lines(relations):
    """One line per block and role for the generator, targets grouped: "E02 là chế tài đối với E01, E03"."""
    grouped = {}
    for r in relations:
        grouped.setdefault((r["from"], r["role"]), []).append(r["to"])
    lines = []
    for (source, role), targets in grouped.items():
        targets = ", ".join(sorted(targets))
        lines.append(f"{source} có dẫn chiếu liên quan tới {targets}" if role == "reference" else f"{source} là {ROLE_LABELS[role]} {targets}")
    return lines
