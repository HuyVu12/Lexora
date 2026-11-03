"""Conservative explicit reference detection; no similarity-based legal edges."""

import re

from legal_ai.common.io import digest, canonical
from legal_ai.schemas.contract import validate_evidence

REFERENCE_VERSION = "explicit-article-ref-v1"
ARTICLE = re.compile(r"(?:(?P<clause_word>khoản)\s+(?P<clause>\d+)\s+)?Điều\s+(?P<article>\d+[a-zđ]?)(?:\s+của\s+(?P<scope>Bộ luật này|Luật này|Nghị định này|Thông tư này|Bộ luật Lao động))?", re.IGNORECASE)


def evidence_at(unit, start, end):
    quote = unit["text"][start:end]
    return validate_evidence({"evidence_id": digest(canonical([unit["unit_version_id"], start, quote])), "document_id": unit["document_id"], "unit_id": unit["unit_id"], "unit_version_id": unit["unit_version_id"], "quote": quote, "start": start, "end": end, "normalized_sha256": unit["normalized_sha256"]})


def detect_references(unit, units, aliases=None):
    aliases = {key.casefold(): value for key, value in (aliases or {}).items()}
    result = []
    for match in ARTICLE.finditer(unit["text"]):
        # Article headings describe this unit; they are not citations.
        if not match.group("clause") and not unit["text"][:match.start()].strip() and unit["text"][match.end():].startswith((".", ":")):
            continue
        before = unit["text"][max(0, match.start() - 90):match.start()]
        complex_prefix = re.search(r"(?:(?:các\s+)?điểm\s+[^.;:\n]+|các\s+khoản\s+[^.;:\n]+)$", before, re.IGNORECASE)
        start = max(0, match.start() - 90) + complex_prefix.start() if complex_prefix else match.start()
        point_labels = []
        if complex_prefix:
            point_match = re.fullmatch(r"(?:các\s+)?điểm\s+([a-zđ](?:\s*(?:,|và)\s*[a-zđ])*)\s*", complex_prefix.group(), re.IGNORECASE)
            if point_match and match.group("clause"):
                point_labels = re.split(r"\s*(?:,|và)\s*", point_match.group(1).casefold())
        scope = match.group("scope")
        after = unit["text"][match.end():match.end() + 65]
        # A following named authority which this detector cannot bind is external.
        unbound_authority = not scope and bool(re.match(r"\s+(?:của\s+)?(?:Luật|Bộ luật|Nghị định|Thông tư)\b", after, re.IGNORECASE))
        target_document = unit["document_id"] if not scope or scope.casefold().endswith(" này") else aliases.get(scope.casefold())
        if unbound_authority:
            target_document = None
        candidates = []
        if target_document:
            articles = [row for row in units if row["document_id"] == target_document and row["unit_type"] == "article" and row["label"].casefold() == match.group("article").casefold()]
            if match.group("clause"):
                article_ids = {row["unit_id"] for row in articles}
                candidates = [row for row in units if row["parent_id"] in article_ids and row["unit_type"] == "clause" and row["label"] == match.group("clause")]
            else:
                candidates = articles
        expected_targets = 1
        ambiguous = len(candidates) > 1
        if point_labels and len(candidates) == 1:
            clause_id = candidates[0]["unit_id"]
            candidates = [row for row in units if row["parent_id"] == clause_id and row["unit_type"] == "point" and row["label"].casefold() in point_labels]
            expected_targets = len(point_labels)
            ambiguous = len({row["label"].casefold() for row in candidates}) != len(candidates)
        elif point_labels:
            candidates = []
            expected_targets = len(point_labels)
        unresolved_complex = complex_prefix and not point_labels
        status = "needs_review" if unresolved_complex else "external" if not target_document else "ambiguous" if ambiguous else "pending" if len(candidates) != expected_targets else "resolved"
        evidence = evidence_at(unit, start, match.end())
        result.append({"reference_id": digest(canonical([REFERENCE_VERSION, unit["unit_version_id"], start, match.end()])), "source_unit_version_id": unit["unit_version_id"], "raw": evidence["quote"], "target_document_id": target_document, "article_label": match.group("article"), "clause_label": match.group("clause"), "point_labels": point_labels, "status": status, "candidate_unit_version_ids": [row["unit_version_id"] for row in candidates], "target_unit_version_ids": [row["unit_version_id"] for row in candidates] if status == "resolved" else [], "reason": "complex_reference_not_resolved" if unresolved_complex else "named_authority_not_bound" if not target_document else "target_outside_loaded_scope" if status == "pending" else "multiple_targets" if status == "ambiguous" else None, "evidence": evidence})
    return result
