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
- `P3`: `P2` (same ranking, same sibling rule and parameters) in a tree layout: inside an Article group the path and
  lead text of a Clause are printed once, as a `lead`, and its Points follow with only their own label and text,
  instead of repeating the Clause lead in every Point; a lead is counted in the budget once per group, when its first
  Point enters. The group header names the document by `short_title` (the title up to its number, e.g. "Nghị định số
  145/2020/NĐ-CP") instead of the full title. Every leaf keeps its own block ID, so citations still reach the Point.

The budget counts every token the generator reads (headers once, Clause leads once in P3, bodies, claim lines).
Records are taken in rank order until the next one does not fit; the first is always kept so a long record cannot
leave the generator with nothing.
Packing never re-ranks and never changes a record's text: a body is the record's own text minus the shared header.
A record may carry a `status_note` (validity filtering, `kb.validity`); it is printed on its own line after the body
and counted in the budget. A condition with a validity block passes `admit` (`kb.validity.RecordFilter.admit_record`
at the question's date): a P2/P3 sibling is then dropped, annotated or replaced by the records of its amending units
exactly as a ranked record would be, so siblings never bring back a unit the validity filter removed. Without
`admit` packing is unchanged.
"""

from functools import lru_cache
import re

from legal_ai.indexing.records import token_spans, unit_path

PACKING_VERSION = "pack-article-v1"
MODES = ("P0", "P1", "P2", "P3")
SIBLING_MODES = ("P2", "P3")  # Modes that add unranked sibling leaves (and pass them through `admit`).
SIBLING_ARTICLES = 3
SIBLING_GROUP_TOKENS = 400
# The document number in a Vietnamese title: "số" followed by a token that starts with a digit ("số 145/2020/NĐ-CP").
_NUMBER = re.compile(r"^(.*?\bsố\s+\d\S*)")


def check_mode(mode):
    if mode not in MODES:
        raise ValueError(f"context_packing must be one of {MODES}")
    return mode


def condition_mode(condition, mode):
    """DK1 always packs flat; DK2-DK4 use the shared mode."""
    return "P0" if condition == "DK1" else check_mode(mode or "P0")


def short_title(title):
    """The document title cut right after its number ("Nghị định số 145/2020/NĐ-CP Quy định ..." -> "Nghị định số
    145/2020/NĐ-CP"); the whole title when it holds no number. Nothing is abbreviated or added."""
    match = _NUMBER.match(title)
    return match.group(1).rstrip(",.;:") if match else title


@lru_cache(maxsize=500_000)
def _cost(text):
    return len(token_spans(text))


class Packer:
    """Packs ranked records of one index. `units` and `documents` are the bundle the records were built from; they are
    needed for `P1`-`P3` only (to split each record into the Article header and its own body)."""

    def __init__(self, mode, records=(), units=(), documents=()):
        self.mode = check_mode(mode)
        self.adds_siblings = self.mode in SIBLING_MODES
        self.layouts, self.siblings = {}, {}
        if self.mode == "P0":
            return
        by_id = {u["unit_id"]: u for u in units}
        titles = {d["document_id"]: d["title"] for d in documents}
        tree = self.mode == "P3"
        for record in records:
            self.layouts[record["record_id"]] = self._layout(record, by_id, titles, tree)
        for record in sorted(records, key=lambda r: (r["document_id"], r["source_start"], r["record_id"])):
            self.siblings.setdefault(self.layouts[record["record_id"]]["group"], []).append(record)

    @staticmethod
    def _layout(record, by_id, titles, tree=False):
        """The group key, header and body of one record; with `tree` (P3) also its Clause `lead` ({key, text, tokens},
        None when the record is not a Point under a Clause) and a header with the short document name."""
        title = titles.get(record["document_id"])
        if record.get("pack_layout"):  # Records that print their own lines (norm-query-v1) carry their split.
            layout = record["pack_layout"]
            header = layout["header"]
            if tree and title is not None and header.startswith(f"{title}\n"):  # They print no Clause lead, so no tree.
                header = short_title(title) + header[len(title):]
            return {"group": tuple(layout["group"]), "header": header, "body": layout["body"],
                    "header_tokens": _cost(header), "body_tokens": _cost(layout["body"]), "lead": None}
        shown = record.get("generator_text") or record["index_text"]
        if len(record["unit_ids"]) != 1 or record["unit_ids"][0] not in by_id:
            raise ValueError(f"article packing needs one leaf unit per record (DK2-DK4): {record['record_id']}")
        leaf = by_id[record["unit_ids"][0]]
        path, chain = unit_path(leaf, by_id)
        context = "".join(u["text"] for u in chain if u["unit_type"] in {"article", "clause"})
        base = f"{title}\n{path}\n{context}{record['text']}".rstrip("\n")
        if not shown.startswith(base):
            raise ValueError(f"record text does not follow the structural layout: {record['record_id']}")
        suffix = shown[len(base):]  # Claim lines of DK3/DK4; empty for DK2.
        article = next((u for u in chain if u["unit_type"] == "article"), leaf if leaf["unit_type"] == "article" else None)
        lineage = chain + [leaf]
        cut = lineage.index(article) + 1 if article is not None else len(lineage)
        header_units, own_units = lineage[:cut], lineage[cut:]
        header_path = " > ".join(path.split(" > ")[:cut])
        lead = "".join(u["text"] for u in header_units if u is not leaf and u["unit_type"] == "article")
        name = short_title(title) if tree else title
        header = f"{name}\n{header_path}" + (f"\n{lead}".rstrip("\n") if lead else "")
        clause_lead = None
        if own_units:
            own_labels = path.split(" > ")[cut:]
            own_lead = "".join(u["text"] for u in own_units[:-1] if u["unit_type"] == "clause")
            if tree and len(own_units) > 1:  # P3: the units between the Article and the leaf (its Clause) form one lead.
                text = f"{' > '.join(own_labels[:-1])}\n{own_lead}".rstrip("\n")
                clause_lead = {"key": tuple(u["unit_id"] for u in own_units[:-1]), "text": text, "tokens": _cost(text)}
                body = f"{own_labels[-1]}\n{record['text']}".rstrip("\n") + suffix
            else:
                body = f"{' > '.join(own_labels)}\n{own_lead}{record['text']}".rstrip("\n") + suffix
        else:  # The Article is the leaf: its text is the whole body.
            body = record["text"].rstrip("\n") + suffix
        group = (record["document_id"], (article or leaf)["unit_id"])
        return {"group": group, "header": header, "body": body, "header_tokens": _cost(header), "body_tokens": _cost(body),
                "lead": clause_lead}

    def bind(self, admit):
        """This packer with a fixed sibling `admit` function (one question's validity date), for callers that take a
        packer with `pack(ranked, budget, top_k)`."""
        return _Bound(self, admit)

    def pack(self, ranked, budget, top_k=None, admit=None):
        """Blocks for the first `top_k` ranked records (all when None) within `budget` tokens. `admit(record)`, when
        given, returns the records that take a P2/P3 sibling's place (none to drop it, itself with a `status_note`, or
        the records of its amending units); the sibling cap still counts the sibling's own body (and, in P3, its
        Clause lead when not yet printed).

        Returns `{"groups": [...], "blocks": [...], "tokens": n}`. Each block has `id` (E01.. in reading order),
        `record`, `text` (what the generator reads for it), `token_count`, `group` (index into groups) and `sibling`
        (added by P2/P3, not ranked). Each group has `header` (None in P0) and `header_tokens`. P3 also returns
        `leads` ([{group, text, tokens}] in reading order, each printed once before its first Point) and gives every
        block a `lead` (index into leads, None for a block outside a Clause lead); `tokens` counts each lead once."""
        ranked = list(ranked)[:top_k] if top_k is not None else list(ranked)
        if self.mode == "P0":
            return self._flat(ranked, budget)
        groups, order, seen, used, blocked = {}, [], set(), 0, None

        def cost_of(layout):
            key, lead = layout["group"], layout["lead"]
            if key not in groups:
                return layout["header_tokens"] + layout["body_tokens"] + (lead["tokens"] if lead else 0)
            return layout["body_tokens"] + (lead["tokens"] if lead and lead["key"] not in groups[key]["leads"] else 0)

        def add(record, sibling):
            nonlocal used, blocked
            layout = self.layouts[record["record_id"]]
            if record.get("status_note"):
                body = f"{layout['body']}\n{record['status_note']}"
                layout = layout | {"body": body, "body_tokens": _cost(body)}
            key = layout["group"]
            cost = cost_of(layout)
            if order and used + cost > budget:
                blocked = used + cost
                return False
            if key not in groups:
                groups[key] = {"header": layout["header"], "header_tokens": layout["header_tokens"], "items": [], "tokens": 0, "leads": set()}
                order.append(key)
            if layout["lead"]:
                groups[key]["leads"].add(layout["lead"]["key"])
            groups[key]["items"].append((record, layout, sibling))
            groups[key]["tokens"] += cost
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
            if self.adds_siblings and opened and len(order) <= SIBLING_ARTICLES:
                for sibling in self.siblings.get(key, []):
                    if sibling["record_id"] in seen:
                        continue
                    if groups[key]["tokens"] + cost_of(self.layouts[sibling["record_id"]]) > SIBLING_GROUP_TOKENS:
                        break
                    shown = [sibling] if admit is None else list({r["record_id"]: r for r in admit(sibling) if r["record_id"] not in seen}.values())
                    if not all(add(record, True) for record in shown):
                        break
                if blocked is not None:  # The budget is spent: nothing after this point is added.
                    break
        out_groups, blocks, leads = [], [], []
        for number, key in enumerate(order):
            group = groups[key]
            out_groups.append({"header": group["header"], "header_tokens": group["header_tokens"]})
            printed = {}
            for record, layout, sibling in sorted(group["items"], key=lambda item: (item[0]["source_start"], item[0]["record_id"])):
                block = {"id": f"E{len(blocks) + 1:02d}", "record": record, "text": layout["body"], "token_count": layout["body_tokens"],
                         "group": number, "sibling": sibling}
                if self.mode == "P3":
                    lead = layout["lead"]
                    if lead and lead["key"] not in printed:
                        printed[lead["key"]] = len(leads)
                        leads.append({"group": number, "text": lead["text"], "tokens": lead["tokens"]})
                    block["lead"] = printed[lead["key"]] if lead else None
                blocks.append(block)
        return {"groups": out_groups, "blocks": blocks, "tokens": used, "next_budget": blocked,
                **({"leads": leads} if self.mode == "P3" else {})}

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


class _Bound:
    def __init__(self, packer, admit):
        self.packer, self.admit, self.mode = packer, admit, packer.mode
        self.adds_siblings = packer.adds_siblings

    def pack(self, ranked, budget, top_k=None):
        return self.packer.pack(ranked, budget, top_k, self.admit)


def evidence_payload(packed):
    """The evidence the generator reads: a flat [{id, text}] list in P0, else [{source, passages: [{id, text}]}] per Article.
    In P3 the Points under one Clause lead are nested as {source: lead, passages: [{id, text}]} inside their Article's
    passages, so the lead is printed once and every Point keeps its own ID."""
    if all(g["header"] is None for g in packed["groups"]):
        return [{"id": b["id"], "text": b["text"]} for b in packed["blocks"]]
    leads = packed.get("leads")
    out = []
    for number, group in enumerate(packed["groups"]):
        passages, nested = [], {}
        for b in packed["blocks"]:
            if b["group"] != number:
                continue
            passage = {"id": b["id"], "text": b["text"]}
            if leads is None or b.get("lead") is None:
                passages.append(passage)
            elif b["lead"] in nested:
                nested[b["lead"]]["passages"].append(passage)
            else:
                nested[b["lead"]] = {"source": leads[b["lead"]]["text"], "passages": [passage]}
                passages.append(nested[b["lead"]])
        out.append({"source": group["header"], "passages": passages})
    return out
