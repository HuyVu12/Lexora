"""Context packing (`pack-article-v1`): how ranked records fill a token budget, the same function for the answer run
and for the budget recall of the retrieval run.

- `P0`: a flat list in rank order; each block is what the record shows the generator (`generator_text` or
  `index_text`), so the document title, path and lead text repeat on every block. This is the only mode for DK1
  (a fixed chunk has no Article to group by).
- `P1`: ranking unchanged, but the kept records are grouped per (document, Article) in order of first appearance in
  the ranking; inside a group the units follow the text order. The title, the path down to the Article and the
  Article's lead text are printed once per group; each unit keeps its own block ID so citations still reach the
  Clause or Point. No unit is added.
- `P2`: `P1`, plus the unranked sibling leaves (Clauses, Points) of the first `SIBLING_ARTICLES` groups, added in text
  order right after the group opens while the group stays within `SIBLING_GROUP_TOKENS` tokens.

The budget counts every token the generator reads (headers once, bodies, claim lines). Records are taken in rank order
until the next one does not fit; the first is always kept so a long record cannot leave the generator with nothing.
Packing never re-ranks and never changes a record's text: a body is the record's own text minus the shared header.
A record may carry a `status_note` (validity filtering, `kb.validity`); it is printed on its own line after the body
and counted in the budget.
"""

from functools import lru_cache

from legal_ai.indexing.records import token_spans, unit_path

PACKING_VERSION = "pack-article-v1"
MODES = ("P0", "P1", "P2")
SIBLING_ARTICLES = 3
SIBLING_GROUP_TOKENS = 400


def check_mode(mode):
    if mode not in MODES:
        raise ValueError(f"context_packing must be one of {MODES}")
    return mode


def condition_mode(condition, mode):
    """DK1 always packs flat; DK2-DK4 use the shared mode."""
    return "P0" if condition == "DK1" else check_mode(mode or "P0")


@lru_cache(maxsize=500_000)
def _cost(text):
    return len(token_spans(text))


class Packer:
    """Packs ranked records of one index. `units` and `documents` are the bundle the records were built from; they are
    needed for `P1`/`P2` only (to split each record into the Article header and its own body)."""

    def __init__(self, mode, records=(), units=(), documents=()):
        self.mode = check_mode(mode)
        self.layouts, self.siblings = {}, {}
        if self.mode == "P0":
            return
        by_id = {u["unit_id"]: u for u in units}
        titles = {d["document_id"]: d["title"] for d in documents}
        for record in records:
            self.layouts[record["record_id"]] = self._layout(record, by_id, titles)
        for record in sorted(records, key=lambda r: (r["document_id"], r["source_start"], r["record_id"])):
            self.siblings.setdefault(self.layouts[record["record_id"]]["group"], []).append(record)

    @staticmethod
    def _layout(record, by_id, titles):
        if record.get("pack_layout"):  # Records that print their own lines (norm-query-v1) carry their split.
            layout = record["pack_layout"]
            return {"group": tuple(layout["group"]), "header": layout["header"], "body": layout["body"],
                    "header_tokens": _cost(layout["header"]), "body_tokens": _cost(layout["body"])}
        shown = record.get("generator_text") or record["index_text"]
        if len(record["unit_ids"]) != 1 or record["unit_ids"][0] not in by_id:
            raise ValueError(f"article packing needs one leaf unit per record (DK2-DK4): {record['record_id']}")
        leaf = by_id[record["unit_ids"][0]]
        path, chain = unit_path(leaf, by_id)
        context = "".join(u["text"] for u in chain if u["unit_type"] in {"article", "clause"})
        base = f"{titles[record['document_id']]}\n{path}\n{context}{record['text']}".rstrip("\n")
        if not shown.startswith(base):
            raise ValueError(f"record text does not follow the structural layout: {record['record_id']}")
        suffix = shown[len(base):]  # Claim lines of DK3/DK4; empty for DK2.
        article = next((u for u in chain if u["unit_type"] == "article"), leaf if leaf["unit_type"] == "article" else None)
        lineage = chain + [leaf]
        cut = lineage.index(article) + 1 if article is not None else len(lineage)
        header_units, own_units = lineage[:cut], lineage[cut:]
        header_path = " > ".join(path.split(" > ")[:cut])
        lead = "".join(u["text"] for u in header_units if u is not leaf and u["unit_type"] == "article")
        header = f"{titles[record['document_id']]}\n{header_path}" + (f"\n{lead}".rstrip("\n") if lead else "")
        if own_units:
            own_path = " > ".join(path.split(" > ")[cut:])
            own_lead = "".join(u["text"] for u in own_units[:-1] if u["unit_type"] == "clause")
            body = f"{own_path}\n{own_lead}{record['text']}".rstrip("\n") + suffix
        else:  # The Article is the leaf: its text is the whole body.
            body = record["text"].rstrip("\n") + suffix
        group = (record["document_id"], (article or leaf)["unit_id"])
        return {"group": group, "header": header, "body": body, "header_tokens": _cost(header), "body_tokens": _cost(body)}

    def pack(self, ranked, budget, top_k=None):
        """Blocks for the first `top_k` ranked records (all when None) within `budget` tokens.

        Returns `{"groups": [...], "blocks": [...], "tokens": n}`. Each block has `id` (E01.. in reading order),
        `record`, `text` (what the generator reads for it), `token_count`, `group` (index into groups) and `sibling`
        (added by P2, not ranked). Each group has `header` (None in P0) and `header_tokens`."""
        ranked = list(ranked)[:top_k] if top_k is not None else list(ranked)
        if self.mode == "P0":
            return self._flat(ranked, budget)
        groups, order, seen, used, blocked = {}, [], set(), 0, None

        def add(record, sibling):
            nonlocal used, blocked
            layout = self.layouts[record["record_id"]]
            if record.get("status_note"):
                body = f"{layout['body']}\n{record['status_note']}"
                layout = layout | {"body": body, "body_tokens": _cost(body)}
            key = layout["group"]
            cost = layout["body_tokens"] + (0 if key in groups else layout["header_tokens"])
            if order and used + cost > budget:
                blocked = used + cost
                return False
            if key not in groups:
                groups[key] = {"header": layout["header"], "header_tokens": layout["header_tokens"], "items": [], "tokens": layout["header_tokens"]}
                order.append(key)
            groups[key]["items"].append((record, layout, sibling))
            groups[key]["tokens"] += layout["body_tokens"]
            seen.add(record["record_id"])
            used += cost
            return True

        for record in ranked:
            if record["record_id"] in seen:
                continue
            opened = self.layouts[record["record_id"]]["group"] not in groups
            if not add(record, False):
                break
            key = self.layouts[record["record_id"]]["group"]
            if self.mode == "P2" and opened and len(order) <= SIBLING_ARTICLES:
                for sibling in self.siblings.get(key, []):
                    if sibling["record_id"] in seen:
                        continue
                    if groups[key]["tokens"] + self.layouts[sibling["record_id"]]["body_tokens"] > SIBLING_GROUP_TOKENS:
                        break
                    if not add(sibling, True):
                        break
                if blocked is not None:  # The budget is spent: nothing after this point is added.
                    break
        out_groups, blocks = [], []
        for number, key in enumerate(order):
            group = groups[key]
            out_groups.append({"header": group["header"], "header_tokens": group["header_tokens"]})
            for record, layout, sibling in sorted(group["items"], key=lambda item: (item[0]["source_start"], item[0]["record_id"])):
                blocks.append({"id": f"E{len(blocks) + 1:02d}", "record": record, "text": layout["body"], "token_count": layout["body_tokens"],
                               "group": number, "sibling": sibling})
        return {"groups": out_groups, "blocks": blocks, "tokens": used, "next_budget": blocked}

    @staticmethod
    def _flat(ranked, budget):
        blocks, groups, seen, used = [], [], set(), 0
        for record in ranked:
            text = record.get("generator_text") or record["index_text"]
            if record.get("status_note"):
                text = f"{text}\n{record['status_note']}"
            if text in seen:
                continue
            cost = _cost(text)
            if blocks and used + cost > budget:
                return {"groups": groups, "blocks": blocks, "tokens": used, "next_budget": used + cost}
            seen.add(text)
            used += cost
            groups.append({"header": None, "header_tokens": 0})
            blocks.append({"id": f"E{len(blocks) + 1:02d}", "record": record, "text": text, "token_count": cost, "group": len(groups) - 1,
                           "sibling": False})
        return {"groups": groups, "blocks": blocks, "tokens": used, "next_budget": None}


def evidence_payload(packed):
    """The evidence the generator reads: a flat [{id, text}] list in P0, else [{source, passages: [{id, text}]}] per Article."""
    if all(g["header"] is None for g in packed["groups"]):
        return [{"id": b["id"], "text": b["text"]} for b in packed["blocks"]]
    out = []
    for number, group in enumerate(packed["groups"]):
        out.append({"source": group["header"], "passages": [{"id": b["id"], "text": b["text"]} for b in packed["blocks"] if b["group"] == number]})
    return out
