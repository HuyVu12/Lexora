"""Choose articles of a long statute and cut them out as one verbatim excerpt.

`outline` lists the articles of a document with their chapter and section, and marks the ones a knowledge base
cannot take: an article holding a heading the parser could not place (a duplicate or orphan heading, typical of
articles that amend other laws and quote their clauses). `excerpt` joins the chosen articles in document order,
each with all its clauses and points, and repeats the chapter and section headings above them, so the excerpt
parses into the same structure. Every character of the excerpt is copied from the normalized source text.
"""

from legal_ai.ingestion.parser import parse
from legal_ai.normalization.text import normalize

BLOCKING = {"duplicate_heading", "orphan_heading"}
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


def outline(text):
    """Articles in document order: {id, heading, chapter, section, blocked, reason}; IDs are stable for `excerpt`."""
    _, parsed = _parsed(text)
    units = parsed["units"]
    by_id = {u["unit_id"]: u for u in units}
    spans = _spans(units)
    blocked = {}
    for item in parsed["audit"]:
        if item["code"] not in BLOCKING:
            continue
        for article, (start, end) in spans.items():
            if start <= item["offset"] < end:
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
                         "blocked": unit["unit_id"] in blocked, "reason": blocked.get(unit["unit_id"])})
    return articles


def excerpt(text, article_ids):
    """The chosen articles (outline IDs) with their chapter/section headings, verbatim, in document order."""
    chosen = set(article_ids)
    if not chosen:
        raise ValueError("Chọn ít nhất một Điều")
    if len(chosen) > MAX_ARTICLES:
        raise ValueError(f"Mỗi lần nhập tối đa {MAX_ARTICLES} Điều; nhập phần còn lại ở lần sau và gộp vào kho")
    source, parsed = _parsed(text)
    units = parsed["units"]
    by_id = {u["unit_id"]: u for u in units}
    spans = _spans(units)
    known = {uid.split("/", 1)[1]: uid for uid in spans}
    missing = sorted(chosen - known.keys())
    if missing:
        raise ValueError(f"Không có Điều này trong văn bản: {missing[0]}")
    blocked = {a["id"] for a in outline(text) if a["blocked"]}
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
        parts.append(source[start:end])
    return "".join(parts)
