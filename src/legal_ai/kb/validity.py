"""Unit status at a date (`unit-status-v2`; `unit-status-v1` stays available): a deterministic function of the
document dates vbpl.vn reported and the amendment edges (`kb.amendments`), never a judgment of the team.

`Validity(...).status(unit_id, as_of)` returns one of:

- `not_yet_effective`: `as_of` is before the document's `effective_from`;
- `expired`: `as_of` is on or after the document's `effective_to` (the document as a whole stopped applying), or (v2)
  a resolved `expire` edge, effective by `as_of`, names the unit or one of its ancestors;
- `repealed`: a resolved repeal edge, effective by `as_of`, targets the unit or one of its ancestors;
- `amended`: the unit's own text is no longer the text in force (below);
- `in_force`: the document applies on `as_of` and no edge above applies;
- `unknown`: the document has no `effective_from`.

What counts as amended differs between the versions. A non-leaf unit's `text` in this corpus is its own heading or
lead sentence only; its clauses and points are separate units.

- `unit-status-v1`: a resolved modify or phrase-replacement edge on the unit, an ancestor or a descendant. A Clause
  is amended as soon as one of its points is, and every point of a Clause is amended when only the Clause's heading
  was rewritten.
- `unit-status-v2` (status per unit): a modify edge of scope `unit` on the unit or an ancestor (the new wording
  replaces the unit and everything below it); a modify edge of scope `own_text` on the unit itself only (a rewritten
  heading or lead sentence leaves the points as they were); a phrase replacement on the unit or an ancestor when the
  unit's own text holds one of the replaced phrases (when no unit under the target holds one, the target itself).
  A change below a unit does not change the unit. Units whose heading or lead above them was amended keep their
  status, and `RecordFilter` shows the new wording next to them.

Edges whose effective date is unknown are ignored and counted. The document dates and the vbpl.vn effect status are
what the site reported at access time (`accessed_at`); a document marked "partly expired" (HHL1P) without an edge
for the expired part stays `in_force` at unit level, a stated limitation (`expire_subject` edges are never applied).

`RecordFilter` is the one place that decides, for index records at a date, what the retrieval run ranks and what the
packer may add as a sibling, so `run-retrieval` and `answer-run` cannot diverge.
"""

from datetime import date

from legal_ai.kb.amendments import edge_phrases, edge_scope

STATUS_VERSION = "unit-status-v2"
VERSIONS = ("unit-status-v1", "unit-status-v2")
STATUSES = ("in_force", "not_yet_effective", "expired", "repealed", "amended", "unknown")
STALE = ("expired", "repealed", "amended")
DROP = ("expired", "repealed", "not_yet_effective")
_V1_KINDS = ("modify", "repeal", "replace_phrase")


def _day(value):
    return date.fromisoformat(value) if isinstance(value, str) else value


class Validity:
    """Unit statuses over one corpus: its documents (`effective_from`/`effective_to`), units and amendment edges.
    `reported` is the effect status per document from the corpus manifest (kept as provenance only)."""

    def __init__(self, documents, units, edges=(), reported=None, version=STATUS_VERSION):
        if version not in VERSIONS:
            raise ValueError(f"unit status version must be one of {VERSIONS}")
        self.version = version
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
            if version == "unit-status-v1" and edge["kind"] not in _V1_KINDS:
                continue  # v1 knew modify, repeal and phrase replacement only.
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

    def _applies(self, edge, unit_id):
        """v2: does an edge on this unit or on one of its ancestors change the unit's own text?"""
        scope = edge_scope(edge)
        if scope == "own_text":
            return edge["target_unit_id"] == unit_id
        if scope == "phrase":
            old = [pair[0] for pair in edge_phrases(edge) if pair[0]]
            if any(phrase in self.units[unit_id]["text"] for phrase in old):
                return True
            if edge["target_unit_id"] != unit_id:
                return False
            below = self._descendants(unit_id)
            return not old or not any(phrase in self.units[d]["text"] for d in below for phrase in old)
        return True

    def applying_edges(self, unit_id, as_of):
        """Resolved edges effective by `as_of` that change this unit (see the module docstring for each version)."""
        as_of = _day(as_of)
        found = []
        if self.version == "unit-status-v1":
            for target in self._lineage(unit_id):
                found += [e for e in self.edges.get(target, []) if _day(e["effective_from"]) <= as_of]
            for target in self._descendants(unit_id):
                found += [e for e in self.edges.get(target, []) if e["kind"] != "repeal" and _day(e["effective_from"]) <= as_of]
            return found
        for target in self._lineage(unit_id):
            found += [e for e in self.edges.get(target, []) if _day(e["effective_from"]) <= as_of and self._applies(e, unit_id)]
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
        `full` is True when the whole new wording replaces the unit (v1: a modify edge on the unit itself; v2: a modify
        edge of scope `unit` on the unit or an ancestor) and False otherwise (a reworded phrase or heading, or in v1 a
        change below the unit), shown next to it."""
        out = {}
        for edge in self.applying_edges(unit_id, as_of):
            target = edge.get("amending_unit_id")
            if edge["kind"] not in ("modify", "replace_phrase") or not target or target not in self.units:
                continue
            if self.version == "unit-status-v1":
                full = edge["kind"] == "modify" and edge["target_unit_id"] == unit_id
            else:
                full = edge["kind"] == "modify" and edge_scope(edge) == "unit"
            out[target] = out.get(target, False) or full
        return sorted(out.items())

    def amended_ancestors(self, unit_id, as_of):
        """v2: ancestors whose own text (heading or lead sentence) was amended by `as_of`; [] in v1, where such a change
        already makes the unit itself amended."""
        if self.version == "unit-status-v1":
            return []
        return [a for a in self._lineage(unit_id)[1:] if self.status(a, as_of) == "amended"]

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
        if any(e["kind"] == "expire" for e in edges):
            return "expired"
        if edges:
            return "amended"
        return "in_force"

    def _sources(self, unit_id, as_of):
        return "; ".join(sorted({f"{e['instruction']['text'][:120]} ({e['amending_document_id']}, hiệu lực từ {e['effective_from']})"
                                 for e in self.applying_edges(unit_id, as_of)}))

    def note(self, unit_id, as_of):
        """A one-line status note for the generator (Vietnamese), or None for a unit in force."""
        status = self.status(unit_id, as_of)
        if status == "in_force":
            return None
        document = self.documents[self.units[unit_id]["document_id"]]
        end = document.get("effective_to")
        if status == "expired" and end and _day(as_of) >= _day(end):
            return f"[Tình trạng tại {as_of}: văn bản hết hiệu lực từ {end} theo vbpl.vn]"
        if status == "not_yet_effective":
            return f"[Tình trạng tại {as_of}: văn bản chưa có hiệu lực, hiệu lực từ {document['effective_from']}]"
        if status == "unknown":
            return f"[Tình trạng tại {as_of}: chưa rõ hiệu lực]"
        verb = {"repealed": "đã bị bãi bỏ", "expired": "đã hết hiệu lực"}.get(status, "đã được sửa đổi")
        return f"[Tình trạng tại {as_of}: quy định này {verb} theo: {self._sources(unit_id, as_of)}]"

    def context_note(self, ancestor_id, as_of):
        """v2: the note for a unit whose heading or lead sentence above it (`ancestor_id`) was amended."""
        return f"[Tình trạng tại {as_of}: phần dẫn của {self.describe(ancestor_id)} đã được sửa đổi theo: {self._sources(ancestor_id, as_of)}]"


class RecordFilter:
    """Validity of index records at a date, shared by the ranking filter of the retrieval run and by the packer (P2/P3
    siblings), so a unit is kept, annotated or replaced the same way wherever it enters the context.

    `level` is `unit` (DK2-DK4) or `document` (the DK1-hl control: only the document dates count)."""

    def __init__(self, validity, level, records):
        if level not in ("unit", "document"):
            raise ValueError("validity level must be unit or document")
        self.validity, self.level, self.records = validity, level, list(records)
        self.index = {record["record_id"]: n for n, record in enumerate(self.records)}
        self.records_of = {}
        for n, record in enumerate(self.records):
            for unit in record["unit_ids"]:
                self.records_of.setdefault(unit, []).append(n)

    def admit(self, n, as_of):
        """[(record index, status note or None)] that take the place of record `n` at `as_of`: [] when it is dropped;
        the record itself first when it is kept (annotated when amended or under an amended lead); then the records of
        the amending units that carry the wording in force. Amending units obey their own document dates."""
        record, validity = self.records[n], self.validity
        if self.level == "document":
            document = validity.documents[record["document_id"]]
            start, end = document.get("effective_from"), document.get("effective_to")
            return [] if (start and as_of < start) or (end and as_of >= end) else [(n, None)]
        statuses = {u: validity.status(u, as_of) for u in record["unit_ids"]}
        if all(s in DROP for s in statuses.values()):
            return []
        amended = [u for u, s in statuses.items() if s == "amended"]
        context = [a for u, s in statuses.items() if s not in DROP for a in validity.amended_ancestors(u, as_of)]
        context = [a for a in dict.fromkeys(context) if a not in amended]
        swaps = {u: validity.replacements(u, as_of) for u in amended + context}
        replaced = bool(amended) and all(any(full for _, full in swaps[u]) for u in amended)
        out = []
        if not replaced:
            lines = [validity.note(u, as_of) for u in amended] + [validity.context_note(a, as_of) for a in context]
            out.append((n, "\n".join(lines) if lines else None))
        for unit in amended + context:
            for target, _ in swaps[unit]:
                if validity.status(target, as_of) in DROP:
                    continue
                out += [(m, f"[Lời văn sửa đổi, có hiệu lực tại {as_of}, của {validity.describe(unit)}]") for m in self.records_of.get(target, [])]
        return out

    def admit_record(self, record, as_of):
        """The records (with `status_note` when annotated) that take the place of `record` at `as_of`."""
        return [self.records[m] | ({"status_note": note} if note else {}) for m, note in self.admit(self.index[record["record_id"]], as_of)]


def stale_units(validity, unit_ids, as_of):
    return [u for u in unit_ids if validity.status(u, as_of) in STALE]
