"""Graph expansion of a ranking over the knowledge base's explicit cross-reference edges (DK3/DK4 option).

The edges are the resolved references of `kb.references.detect_references` ("theo quy định tại khoản 1 Điều 36"):
a unit points to the unit it cites (`reference`). The reverse direction (`referenced_by`) leads from a provision to
the provisions that cite it, such as the Decree article that details a Labour Code article. After ranking, every
retrieved record is followed by up to `max_neighbors` records reached over the configured edge types, best ranked
first, so a cited or detailing provision reaches the generator together with the one that was found. The list
keeps its length: neighbours push lower-ranked records out instead of adding to the context, so every condition
still hands over the same number of records. No similarity edges, no invented
targets: pending, ambiguous and external references create no edge.
"""

from legal_ai.kb.references import detect_references

GRAPH_VERSION = "reference-expansion-v2"
EDGES = ("reference", "referenced_by")


def check_config(graph):
    if not isinstance(graph, dict) or set(graph.get("edges", [])) - set(EDGES) or not graph.get("edges"):
        raise ValueError(f"graph.edges must be a non-empty subset of {EDGES}")
    if type(graph.get("max_neighbors", 2)) is not int or not 1 <= graph.get("max_neighbors", 2) <= 5:
        raise ValueError("graph.max_neighbors must be an integer from 1 to 5")
    if not isinstance(graph.get("require_match", False), bool):
        raise ValueError("graph.require_match must be true or false")
    return graph


def reference_edges(units, aliases=None):
    """{source unit_id: [cited unit_id, ...]} from resolved references, cited units in text order."""
    by_version = {u["unit_version_id"]: u["unit_id"] for u in units}
    edges = {}
    for unit in units:
        for reference in detect_references(unit, units, aliases):
            for target in reference["target_unit_version_ids"]:
                cited = by_version[target]
                if cited != unit["unit_id"] and cited not in edges.setdefault(unit["unit_id"], []):
                    edges[unit["unit_id"]].append(cited)
    return {source: targets for source, targets in edges.items() if targets}


def graph_edges(units, kinds, aliases=None):
    """{unit_id: [neighbour unit_id, ...]} over the chosen edge kinds; `referenced_by` inverts `reference`."""
    forward = reference_edges(units, aliases)
    edges = {}
    if "reference" in kinds:
        for source, targets in forward.items():
            edges.setdefault(source, []).extend(targets)
    if "referenced_by" in kinds:
        for source, targets in forward.items():
            for target in targets:
                if source not in edges.setdefault(target, []):
                    edges[target].append(source)
    return edges


def _inside(unit_id, ancestor):
    return unit_id == ancestor or unit_id.startswith(ancestor + "/")


def expand(ranked, records, edges, depth, max_neighbors=2, require_match=False):
    """[(record index, score, via)] of length <= depth: each ranked record, then the records of the units it cites.

    `ranked` is the full [(index, score)] ranking. A unit cites through its own edges and those of its ancestors
    (an Article's lead text may hold the reference for all its Clauses). Neighbours are taken best ranked first,
    unranked ones after in source order; `via` is None for a ranked record and the citing record index otherwise.
    With `require_match` a neighbour must itself be among the ranked candidates (the graph proposes, the question
    confirms), so a heavily cited provision such as an entry-into-force article is not pulled in for every question."""
    position = {index: n for n, (index, _) in enumerate(ranked)}
    score = dict(ranked)
    result, taken = [], set()

    def cited_records(index):
        units = records[index]["unit_ids"]
        targets = [t for source, cited in edges.items() if any(_inside(u, source) for u in units) for t in cited]
        found = [i for i, row in enumerate(records) if i != index and any(_inside(u, t) for u in row["unit_ids"] for t in targets)]
        if require_match:
            found = [i for i in found if i in position]
        return sorted(found, key=lambda i: (position.get(i, len(position)), i))

    for index, _ in ranked:
        if len(result) >= depth:
            break
        if index in taken:
            continue
        result.append((index, score[index], None))
        taken.add(index)
        for neighbour in [i for i in cited_records(index) if i not in taken][:max_neighbors]:
            if len(result) >= depth:
                break
            result.append((neighbour, score.get(neighbour, 0.0), index))
            taken.add(neighbour)
    return result
