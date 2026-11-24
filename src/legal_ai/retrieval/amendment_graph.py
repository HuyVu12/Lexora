"""Amendment edges as knowledge-base relations (`amendment-expansion-v1`), the DK3/DK4 part of validity option B
(decided 22/11/2026, `docs/planning/dk2-dk4-improvement-2026-11-22.md` sections 4.4 and 5.2).

The edges are an `amendment-rules-v2` run (`cli amendment-build`): which unit of the corpus an amending text modifies,
rewords, repeals, adds to or declares expired, and the unit of the amending document that holds the instruction
(`amending_unit_id`; in corpus scope v3 that unit carries the new wording). Here an edge is a relation between two units
of the knowledge base, followed in both directions after ranking: a found old unit brings the unit that amends it, a
found amending unit brings the unit it amends. Each neighbour carries a short relation note for the generator
("[Quan hệ trong kho: quy định này được sửa đổi bởi ...]") and pushes lower-ranked records out, so the list keeps its
length, as in `retrieval.graph`.

Which edges are relations: an edge whose status is `resolved` (target unit in the corpus) or `resolved_parent` (an
added unit whose parent is in the corpus, `anchor_unit_id`) and whose amending unit is in the corpus. Unresolved,
external and document-level edges have no unit to pull: they are never used and only counted (`describe`), so the
same edge set serves DK3 and DK4 and nothing is guessed.

DK3 (unvalidated) follows every relation whatever the question's date and never checks unit status: an old, amended
or repealed unit stays in context next to the unit that amended it. Its only date rule is the document-level filter it
shares with DK2 (a document not in force at the question's date is dropped), so DK3 differs from DK2 by knowledge-base
content only. DK4 validates: `expand(..., as_of=day)` follows only
relations whose edge is dated and effective by the question's date (the temporal check), and the retrieval run then
applies the unit status filter (`kb.validity`, `unit-status-v2`) to the ranked records and their neighbours alike.
"""

import json
import re
from pathlib import Path

from legal_ai.common.io import digest, read_jsonl

AMENDMENT_GRAPH_VERSION = "amendment-expansion-v1"
USABLE = ("resolved", "resolved_parent")
_NUMBER = re.compile(r"^(.*?\bsố\s+\d+/\d{4}/[^\s,;]+)")
_ACTIVE = {"modify": "sửa đổi, bổ sung", "replace_phrase": "thay thế cụm từ tại", "repeal": "bãi bỏ", "add": "bổ sung vào",
           "expire": "tuyên bố hết hiệu lực"}
_PASSIVE = {"modify": "được sửa đổi, bổ sung bởi", "replace_phrase": "được thay thế cụm từ bởi", "repeal": "bị bãi bỏ bởi",
            "add": "được bổ sung bởi", "expire": "bị tuyên bố hết hiệu lực bởi"}


def check_config(spec):
    """`graph.amendments` of a DK3/DK4 condition: {run: amendment edge run directory, max_neighbors?: 1-5}."""
    if not isinstance(spec, dict) or not spec.get("run") or set(spec) - {"run", "max_neighbors"}:
        raise ValueError("graph.amendments must be {run: amendment edge run directory, max_neighbors?: 1-5}")
    if type(spec.get("max_neighbors", 2)) is not int or not 1 <= spec.get("max_neighbors", 2) <= 5:
        raise ValueError("graph.amendments.max_neighbors must be an integer from 1 to 5")
    return spec


def load(spec, units_path):
    """(edges, SHA-256 of edges.jsonl) of the run named by `spec`, checked against the bundle's units."""
    folder = Path(spec["run"])
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest["units_sha256"] != digest(Path(units_path).read_bytes()):
        raise ValueError("the amendment edges were resolved against another corpus bundle")
    return read_jsonl(folder / "edges.jsonl"), digest((folder / "edges.jsonl").read_bytes())


def anchor(edge):
    """The corpus unit an edge acts on: the target, or for an added unit the parent it is added to."""
    return edge.get("target_unit_id") or (edge.get("anchor_unit_id") if edge.get("status") == "resolved_parent" else None)


def relations(edges, units):
    """({unit_id: [(other unit_id, edge, role)]}, report). `role` is what the other unit is to the key unit:
    `amending` (it amends the key unit) or `amended` (the key unit amends it). The report counts used edges per status
    and unused ones per status and reason."""
    known = {u["unit_id"] for u in units}
    links, used, unused = {}, {}, {}
    for edge in edges:
        old, new = anchor(edge), edge.get("amending_unit_id")
        if edge.get("status") not in USABLE or old not in known or new not in known:
            key = f"{edge.get('status')}:{edge.get('reason') or ('endpoint_not_in_corpus' if edge.get('status') in USABLE else 'none')}"
            unused[key] = unused.get(key, 0) + 1
            continue
        used[edge["status"]] = used.get(edge["status"], 0) + 1
        links.setdefault(old, []).append((new, edge, "amending"))
        links.setdefault(new, []).append((old, edge, "amended"))
    return links, {"edges": len(edges), "used": dict(sorted(used.items())), "unused": dict(sorted(unused.items()))}


def short_name(document):
    """"Nghị định số 70/2023/NĐ-CP" from the title, or the document ID when the title has no number."""
    match = _NUMBER.match(document.get("title") or "")
    return match.group(1) if match else document["document_id"]


def describe(unit_id, units, documents):
    """"điểm b khoản 1 Điều 1 Nghị định số 70/2023/NĐ-CP": labels from the unit's lineage and the document number."""
    names = {"article": "Điều", "clause": "khoản", "point": "điểm"}
    parts, current = [], units.get(unit_id)
    while current:
        if current["unit_type"] in names:
            parts.append(f"{names[current['unit_type']]} {current['label']}")
        current = units.get(current["parent_id"])
    return " ".join(parts + [short_name(documents[units[unit_id]["document_id"]])])


def note(edge, role, units, documents):
    """The relation note of a neighbour (the unit pulled in, `role` relative to the unit that brought it): what it is to
    that unit."""
    seed = edge.get("amending_unit_id") if role == "amended" else anchor(edge)
    verb = (_ACTIVE if role == "amending" else _PASSIVE).get(edge["kind"], "liên quan sửa đổi với")
    since = f", từ {edge['effective_from']}" if edge.get("effective_from") else ""
    return f"[Quan hệ trong kho: quy định này {verb} {describe(seed, units, documents)}{since}]"


def _prefixes(unit_id):
    parts = unit_id.split("/")
    return ["/".join(parts[:n]) for n in range(1, len(parts) + 1)]


def expand(ranked, records, links, depth, max_neighbors=2, as_of=None, units=None, documents=None):
    """[(record index, score, via)] of length <= depth: each record of `ranked` ([(index, score)]), then up to
    `max_neighbors` records reached over amendment relations, best ranked first, unranked ones in source order.

    A unit relates through its own relations and those of its ancestors (a modify edge on a Clause covers its Points);
    the records of a related unit are the records inside it. `via` is None for a record of `ranked` and
    {from: index, edge_id, role, note} for a neighbour. With `as_of` (DK4) a relation counts only when its edge is dated
    and effective by that date; without it (DK3) every relation counts. Neighbours are not expanded further."""
    position = {index: n for n, (index, _) in enumerate(ranked)}
    score = dict(ranked)
    under = {}
    for i, row in enumerate(records):
        for unit in row["unit_ids"]:
            for prefix in _prefixes(unit):
                under.setdefault(prefix, []).append(i)

    def related(index):
        found = {}
        for unit in records[index]["unit_ids"]:
            for prefix in _prefixes(unit):
                for other, edge, role in links.get(prefix, []):
                    if as_of is not None and (not edge.get("effective_from") or edge["effective_from"] > as_of):
                        continue
                    for i in under.get(other, []):
                        if i != index and i not in found:
                            found[i] = (other, edge, role)
        return sorted(found.items(), key=lambda item: (position.get(item[0], len(position)), item[0]))

    result, taken = [], set()
    for index, _ in ranked:
        if len(result) >= depth:
            break
        if index in taken:
            continue
        result.append((index, score[index], None))
        taken.add(index)
        for neighbour, (_, edge, role) in [item for item in related(index) if item[0] not in taken][:max_neighbors]:
            if len(result) >= depth:
                break
            via = {"from": index, "edge_id": edge["edge_id"], "role": role}
            if units is not None and documents is not None:
                via["note"] = note(edge, role, units, documents)
            result.append((neighbour, score.get(neighbour, 0.0), via))
            taken.add(neighbour)
    return result
