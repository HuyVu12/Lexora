"""Unit status at a date (`unit-status-v1`): a deterministic function of the document dates vbpl.vn reported and the
amendment edges (`kb.amendments`), never a judgment of the team.

`unit_status(unit_id, as_of)` returns one of:

- `not_yet_effective`: `as_of` is before the document's `effective_from`;
- `expired`: `as_of` is on or after the document's `effective_to` (the document as a whole stopped applying);
- `repealed`: a resolved repeal edge, effective by `as_of`, targets the unit or one of its ancestors;
- `amended`: a resolved modify or phrase-replacement edge, effective by `as_of`, targets the unit, an ancestor or a
  descendant (the unit's text is no longer the text in force);
- `in_force`: the document applies on `as_of` and no edge above applies;
- `unknown`: the document has no `effective_from`.

Edges whose effective date is unknown are ignored and counted. The document dates and the vbpl.vn effect status are
what the site reported at access time (`accessed_at`); a document marked "partly expired" (HHL1P) without an edge
for the expired part stays `in_force` at unit level, a stated limitation.
"""

from datetime import date

STATUS_VERSION = "unit-status-v1"
STATUSES = ("in_force", "not_yet_effective", "expired", "repealed", "amended", "unknown")
STALE = ("expired", "repealed", "amended")


def _day(value):
    return date.fromisoformat(value) if isinstance(value, str) else value


class Validity:
    """Unit statuses over one corpus: its documents (`effective_from`/`effective_to`), units and amendment edges.
    `reported` is the effect status per document from the corpus manifest (kept as provenance only)."""

    def __init__(self, documents, units, edges=(), reported=None):
        self.documents = {d["document_id"]: d for d in documents}
        self.units = {u["unit_id"]: u for u in units}
        self.reported = reported or {}
        self.children = {}
        for unit in units:
            self.children.setdefault(unit["parent_id"], []).append(unit["unit_id"])
        self.edges, self.undated = {}, 0
        for edge in edges:
            if edge.get("status") != "resolved" or edge["kind"] == "add" or not edge.get("target_unit_id"):
                continue
            if not edge.get("effective_from"):
                self.undated += 1
                continue
            self.edges.setdefault(edge["target_unit_id"], []).append(edge)

    def _lineage(self, unit_id):
        chain, current = [], self.units.get(unit_id)
        while current:
            chain.append(current["unit_id"])
            current = self.units.get(current["parent_id"])
        return chain

    def _descendants(self, unit_id):
        out, stack = [], list(self.children.get(unit_id, []))
        while stack:
            current = stack.pop()
            out.append(current)
            stack.extend(self.children.get(current, []))
        return out

    def applying_edges(self, unit_id, as_of):
        """Resolved edges effective by `as_of` on the unit, its ancestors (any kind) or its descendants (not repeals)."""
        as_of = _day(as_of)
        found = []
        for target in self._lineage(unit_id):
            found += [e for e in self.edges.get(target, []) if _day(e["effective_from"]) <= as_of]
        for target in self._descendants(unit_id):
            found += [e for e in self.edges.get(target, []) if e["kind"] != "repeal" and _day(e["effective_from"]) <= as_of]
        return found

    def describe(self, unit_id):
        """"khoản 5 Điều 3, Nghị định số 152/2020/NĐ-CP ..." for a status note (labels and title, never invented)."""
        names = {"article": "Điều", "clause": "khoản", "point": "điểm"}
        parts, current = [], self.units.get(unit_id)
        while current:
            if current["unit_type"] in names:
                parts.append(f"{names[current['unit_type']]} {current['label']}")
            current = self.units.get(current["parent_id"])
        document = self.documents[self.units[unit_id]["document_id"]]
        return f"{' '.join(parts)}, {document.get('title', document['document_id'])}"

    def replacements(self, unit_id, as_of):
        """Amending units in the corpus that carry the text now in force for this unit: [(amending unit, full)] where
        `full` is True for a modify edge on the unit itself (its whole new wording replaces it) and False otherwise
        (a reworded phrase, or a change below or above the unit, shown next to it)."""
        out = {}
        for edge in self.applying_edges(unit_id, as_of):
            target = edge.get("amending_unit_id")
            if edge["kind"] == "repeal" or not target or target not in self.units:
                continue
            full = edge["kind"] == "modify" and edge["target_unit_id"] == unit_id
            out[target] = out.get(target, False) or full
        return sorted(out.items())

    def status(self, unit_id, as_of):
        as_of = _day(as_of)
        unit = self.units[unit_id]
        document = self.documents[unit["document_id"]]
        start, end = document.get("effective_from"), document.get("effective_to")
        if not start:
            return "unknown"
        if as_of < _day(start):
            return "not_yet_effective"
        if end and as_of >= _day(end):
            return "expired"
        edges = self.applying_edges(unit_id, as_of)
        if any(e["kind"] == "repeal" and e["target_unit_id"] in self._lineage(unit_id) for e in edges):
            return "repealed"
        if edges:
            return "amended"
        return "in_force"

    def note(self, unit_id, as_of):
        """A one-line status note for the generator (Vietnamese), or None for a unit in force."""
        status = self.status(unit_id, as_of)
        if status == "in_force":
            return None
        document = self.documents[self.units[unit_id]["document_id"]]
        if status == "expired":
            return f"[Tình trạng tại {as_of}: văn bản hết hiệu lực từ {document['effective_to']} theo vbpl.vn]"
        if status == "not_yet_effective":
            return f"[Tình trạng tại {as_of}: văn bản chưa có hiệu lực, hiệu lực từ {document['effective_from']}]"
        if status == "unknown":
            return f"[Tình trạng tại {as_of}: chưa rõ hiệu lực]"
        edges = self.applying_edges(unit_id, as_of)
        sources = sorted({f"{e['instruction']['text'][:120]} ({e['amending_document_id']}, hiệu lực từ {e['effective_from']})" for e in edges})
        verb = "đã bị bãi bỏ" if status == "repealed" else "đã được sửa đổi"
        return f"[Tình trạng tại {as_of}: quy định này {verb} theo: {'; '.join(sources)}]"


def stale_units(validity, unit_ids, as_of):
    return [u for u in unit_ids if validity.status(u, as_of) in STALE]
