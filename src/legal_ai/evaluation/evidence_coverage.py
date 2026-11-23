"""Leaf-complete evidence coverage (`evidence-coverage-v1`), the primary retrieval metric next to the legacy recall.

The legacy `recall_at_tokens` counts a gold unit as found when any packed record carries its unit ID. A DK1 fixed
chunk carries the ID of every unit it overlaps by even one character, so a window that clips a clause gets full credit
for it. This module measures what the generator can actually read of the gold evidence, in source coordinates:

- A gold unit expands into pieces: its leaf units plus the lead-in segment (own text before the first child) of every
  non-leaf node on the way down. A piece is (document_id, start, end).
- The packed context contributes spans: each packed record's own source span and, for a unit record that prints its
  ancestors' lead-in (Article and Clause lead text, shown in every packing mode of DK2-DK4 unit records), those
  lead-ins. A record that prints no context (DK1 chunks, claim records, `pack_layout` records) adds only its span.
- Leaf recall at tau is the share of pieces with at least tau of their characters covered (tau 1.0 tolerates
  `BOUNDARY` uncovered characters, so a cut at a token edge or a trailing space does not fail a piece). Chars recall is
  the mean over gold units of the covered share of their pieces. Complete is 1 when every piece is complete at tau 1.0.

Questions without gold units have no value. Nothing here ranks, packs or calls a model.
"""

from collections import defaultdict

VERSION = "evidence-coverage-v1"
TAUS = (0.5, 0.8, 1.0)
BOUNDARY = 2
PRINTED_TYPES = {"article", "clause"}
_EPS = 1e-9


def tau_key(tau):
    return f"tau{tau}"


class EvidenceTree:
    """Unit hierarchy of a bundle: pieces of a gold unit and the lead-ins a record prints."""

    def __init__(self, units):
        self.by_id = {u["unit_id"]: u for u in units}
        self.children = defaultdict(list)
        for u in units:
            parent = u.get("parent_id")
            if parent in self.by_id:
                self.children[parent].append(u)
        self.lead = {}  # unit_id -> (start, end) of its own text before its first child
        for uid, kids in self.children.items():
            u = self.by_id[uid]
            first = min(k["source_start"] for k in kids)
            if first > u["source_start"]:
                self.lead[uid] = (u["source_start"], first)
        self._printed = {}

    def pieces(self, gold_id):
        """[(document_id, start, end)] of one gold unit; empty when the unit is unknown."""
        unit = self.by_id.get(gold_id)
        if unit is None:
            return []
        out, stack = [], [unit]
        while stack:
            u = stack.pop()
            kids = self.children.get(u["unit_id"])
            if kids:
                if u["unit_id"] in self.lead:
                    out.append((u["document_id"],) + self.lead[u["unit_id"]])
                stack.extend(kids)
            elif u["source_end"] > u["source_start"]:
                out.append((u["document_id"], u["source_start"], u["source_end"]))
        return out

    def printed_leads(self, record):
        """[(start, end)] lead-ins of the Article and Clause ancestors a unit record prints with its text."""
        key = (record["record_id"], record.get("generator_text") or record["index_text"], bool(record.get("pack_layout")))
        if key not in self._printed:
            self._printed[key] = self._leads(record)
        return self._printed[key]

    def _leads(self, record):
        if record.get("condition") == "DK1" or record.get("pack_layout") or len(record["unit_ids"]) != 1:
            return []
        leaf = self.by_id.get(record["unit_ids"][0])
        if leaf is None:
            return []
        chain, current = [], self.by_id.get(leaf.get("parent_id"))
        while current:
            chain.append(current)
            current = self.by_id.get(current.get("parent_id"))
        chain.reverse()
        chain = [u for u in chain if u["unit_type"] in PRINTED_TYPES]
        shown = record.get("generator_text") or record["index_text"]
        printed = ("".join(u["text"] for u in chain) + record["text"]).rstrip("\n")  # Packing prints the body without its last newline.
        if not chain or printed not in shown:
            return []  # The record does not print its ancestors (claim records print their own lines).
        return [self.lead[u["unit_id"]] for u in chain if u["unit_id"] in self.lead]


def packed_spans(tree, records):
    """{document_id: merged [(start, end)]} read from the packed records."""
    raw = defaultdict(list)
    for r in records:
        raw[r["document_id"]].append((r["source_start"], r["source_end"]))
        raw[r["document_id"]].extend(tree.printed_leads(r))
    out = {}
    for doc, spans in raw.items():
        merged = []
        for s, e in sorted(spans):
            if merged and s <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], e)
            else:
                merged.append([s, e])
        out[doc] = merged
    return out


def _covered(spans, start, end):
    return sum(max(0, min(e, end) - max(s, start)) for s, e in spans)


def piece_ok(covered, length, tau):
    return covered >= tau * length - _EPS or (tau == 1.0 and length - covered <= BOUNDARY)


def question_coverage(tree, gold, records):
    """{leaf_recall_tau<t>, chars_recall, complete} of one question for the packed `records`, or None without gold."""
    units = [(g, tree.pieces(g)) for g in gold]
    units = [(g, p) for g, p in units if p]
    if not units:
        return None
    spans = packed_spans(tree, records)
    cache = {}

    def cover(piece):
        if piece not in cache:
            doc, a, b = piece
            cache[piece] = _covered(spans.get(doc, []), a, b)
        return cache[piece]

    pieces = {p for _, ps in units for p in ps}
    out = {}
    for tau in TAUS:
        out[f"leaf_recall_{tau_key(tau)}"] = sum(piece_ok(cover(p), p[2] - p[1], tau) for p in pieces) / len(pieces)
    shares = [sum(cover(p) for p in ps) / sum(p[2] - p[1] for p in ps) for _, ps in units]
    out["chars_recall"] = sum(shares) / len(shares)
    out["complete"] = 1.0 if all(piece_ok(cover(p), p[2] - p[1], 1.0) for p in pieces) else 0.0
    return out


METRIC_KEYS = tuple(f"leaf_recall_{tau_key(t)}" for t in TAUS) + ("chars_recall", "complete")


def rows_by_budget(per_budget):
    """{metric: {budget: value}} from {budget: question_coverage or None}."""
    out = {key: {} for key in METRIC_KEYS}
    for budget, value in per_budget.items():
        for key in METRIC_KEYS:
            out[key][str(budget)] = None if value is None else value[key]
    return out


def means(rows, budgets):
    """Block for metrics.json: version and the mean of every metric at every budget over questions with a value."""
    out = {"version": VERSION, "scored_questions": sum(1 for r in rows if r and r["complete"].get(str(budgets[0])) is not None) if budgets else 0}
    for key in METRIC_KEYS:
        block = {}
        for b in budgets:
            vals = [r[key][str(b)] for r in rows if r and r[key].get(str(b)) is not None]
            block[str(b)] = sum(vals) / len(vals) if vals else None
        out[f"mean_{key}_at_tokens"] = block
    return out
