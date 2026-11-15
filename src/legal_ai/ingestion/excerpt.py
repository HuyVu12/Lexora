"""Choose articles of a long statute and cut them out as one verbatim excerpt.

`outline` lists the articles of a document with their chapter and section, and marks the ones a knowledge base
cannot take: an article holding a heading the parser could not place (a duplicate or orphan heading) or a quotation
that hides headings (`quoted_text`, typical of articles that amend other laws and quote their clauses). `excerpt` joins the chosen articles in document order,
each with all its clauses and points, and repeats the chapter and section headings above them, so the excerpt
parses into the same structure. Every character of the excerpt is copied from the normalized source text.

A repeated chapter or section heading (a numbering slip of the source, such as the second "Chương XI" of NĐ
145/2020/NĐ-CP) is a `duplicate_heading` that the parser skips, so its lines fall inside the article before it and
that article is blocked although its own text is intact. With `cut_stray_headings` (off by default, so corpus versions
built before 15/11/2026, including the frozen scope v3, rebuild byte for byte) such an article is not blocked and
its excerpt stops where the stray heading starts. A repeated clause or point label inside an article (the two "d)" of
khoản 5 Điều 30 NĐ 152/2020/NĐ-CP) still blocks it: which unit is meant would be a guess.
"""

from legal_ai.ingestion.parser import parse
from legal_ai.normalization.text import normalize

BLOCKING = {"duplicate_heading", "orphan_heading", "quoted_text"}
MAX_ARTICLES = 60


def _parsed(text):
    normalized = normalize(text, "source.txt")
    return normalized["text"], parse(normalized, "source", normalized["normalized_sha256"])


def _spans(units):
    """Article unit -> (start, end) covering the article and every unit below it."""
    by_parent = {}
    for unit in units:
        by_parent.setdefault(unit["parent_id"], []).append(unit)
    spans = {}
    for unit in units:
        if unit["unit_type"] != "article":
            continue
        end, stack = unit["source_end"], [unit]
        while stack:
            for child in by_parent.get(stack.pop()["unit_id"], []):
                end = max(end, child["source_end"])
                stack.append(child)
        spans[unit["unit_id"]] = (unit["source_start"], end)
    return spans


def _heading(unit):
    return unit["text"].strip().split("\n")[0][:200]


def _structural(item):
    """A duplicate chapter or section heading (not a clause or point label inside an article)."""
    return item["code"] == "duplicate_heading" and item["unit_id"].rsplit("/", 1)[-1].startswith(("chapter-", "section-"))


def outline(text, cut_stray_headings=False):
    """Articles in document order: {id, heading, chapter, section, blocked, reason}; IDs are stable for `excerpt`.
    With `cut_stray_headings`, an article holding only a repeated chapter or section heading is not blocked and gets
    `cut_at`, the offset where its excerpt stops."""
    _, parsed = _parsed(text)
    units = parsed["units"]
    by_id = {u["unit_id"]: u for u in units}
    spans = _spans(units)
    blocked, cuts = {}, {}
    for item in parsed["audit"]:
        if item["code"] not in BLOCKING:
            continue
        for article, (start, end) in spans.items():
            if start <= item["offset"] < end:
                if cut_stray_headings and _structural(item):
                    cuts[article] = min(cuts.get(article, end), item["offset"])
                else:
                    blocked.setdefault(article, item["code"])
    articles = []
    for unit in units:
        if unit["unit_type"] != "article":
            continue
        chapter = section = None
        current = by_id.get(unit["parent_id"])
        while current:
            if current["unit_type"] == "section":
                section = _heading(current)
            elif current["unit_type"] == "chapter":
                chapter = " ".join(current["text"].split())[:200]
            current = by_id.get(current["parent_id"])
        articles.append({"id": unit["unit_id"].split("/", 1)[1], "heading": _heading(unit), "chapter": chapter, "section": section,
                         "blocked": unit["unit_id"] in blocked, "reason": blocked.get(unit["unit_id"]),
                         **({"cut_at": cuts[unit["unit_id"]]} if unit["unit_id"] in cuts and unit["unit_id"] not in blocked else {})})
    return articles


def excerpt(text, article_ids, limit=MAX_ARTICLES, include_amending=False, cut_stray_headings=False):
    """The chosen articles (outline IDs) with their chapter/section headings, verbatim, in document order.
    `limit` caps one knowledge-base import; research scopes pass None. With `include_amending` an article blocked only
    for quoted text (an article amending another document) may be chosen: the parser keeps each quoted new wording
    inside the leaf unit of its instruction, so every amendment becomes one citable unit (corpus scope v3). With
    `cut_stray_headings` an article holding a repeated chapter or section heading is cut before it (see the module)."""
    chosen = set(article_ids)
    if not chosen:
        raise ValueError("Chọn ít nhất một Điều")
    if limit is not None and len(chosen) > limit:
        raise ValueError(f"Mỗi lần nhập tối đa {limit} Điều; nhập phần còn lại ở lần sau và gộp vào kho")
    source, parsed = _parsed(text)
    units = parsed["units"]
    by_id = {u["unit_id"]: u for u in units}
    spans = _spans(units)
    known = {uid.split("/", 1)[1]: uid for uid in spans}
    missing = sorted(chosen - known.keys())
    if missing:
        raise ValueError(f"Không có Điều này trong văn bản: {missing[0]}")
    articles = outline(text, cut_stray_headings)
    blocked = {a["id"] for a in articles if a["blocked"] and not (include_amending and a["reason"] == "quoted_text")}
    cuts = {a["id"]: a["cut_at"] for a in articles if "cut_at" in a}
    if chosen & blocked:
        raise ValueError(f"Điều có cấu trúc lồng nhau không nhập được: {sorted(chosen & blocked)[0]}")
    parts, shown = [], set()
    for short in sorted(chosen, key=lambda s: spans[known[s]][0]):
        uid = known[short]
        ancestors, current = [], by_id.get(by_id[uid]["parent_id"])
        while current:
            ancestors.append(current)
            current = by_id.get(current["parent_id"])
        for heading in reversed(ancestors):
            if heading["unit_id"] not in shown:
                shown.add(heading["unit_id"])
                parts.append(source[heading["source_start"]:heading["source_end"]])
        start, end = spans[uid]
        parts.append(source[start:min(end, cuts.get(short, end))])
    return "".join(parts)
