"""Draft enumeration questions from the human extraction gold set (`enumeration-draft-v1`), research plan WP5.1.

The answer of an enumeration question is every unit whose gold norm meets a criterion inside a topic scope, so the
gold does not depend on any model: the gold set (`extraction-gold-v1`, adjudicated) says which sentence states which
modality, actor, deadlines and quantities. `drafts` groups the gold norms per scope (one Article, or one Chapter) and
criterion:

- `by_actor`: modality obligation / prohibition / entitlement and one canonical actor (alias table of `norm-query-v1`);
- `deadlines`, `quantities`: any modality with that slot filled.

A group becomes a draft only with at least `min_units` distinct leaf units. The question text comes from a fixed
template; annotators rewrite it in natural wording, check every answer unit against the text (`check_sheet`) and
drop drafts that do not make sense before the set is frozen. Precision can only be scored on units the gold covers.
"""

import csv
import re

from legal_ai.retrieval.norm_query import actor_keys

DRAFT_VERSION = "enumeration-draft-v1"
MODAL = {"obligation": "nghĩa vụ", "prohibition": "hành vi bị cấm", "entitlement": "quyền"}


def _scope(unit_id, level):
    pattern = r"(.*?/article-[^/]+)" if level == "article" else r"(.*?/chapter-[^/]+)"
    match = re.match(pattern, unit_id)
    return match.group(1) if match else None


def _title(scope_id, units_by_id, titles):
    unit = units_by_id.get(scope_id)
    heading = unit["text"].split("\n", 1)[0].strip().rstrip(".") if unit else scope_id
    return f"{heading} của {titles.get(scope_id.split('/', 1)[0], scope_id.split('/', 1)[0])}"


def _filled(slots, name):
    return isinstance(slots.get(name), str) and slots[name].strip()


def drafts(gold_rows, units, documents, aliases, level="article", min_units=2):
    """Draft questions (question-file rows) with their criteria and gold answer units."""
    if level not in ("article", "chapter"):
        raise ValueError("level must be article or chapter")
    units_by_id = {u["unit_id"]: u for u in units}
    titles = {d["document_id"]: d["title"] for d in documents}
    groups = {}
    for row in gold_rows:
        scope = _scope(row["unit_id"], level)
        if scope is None:
            continue
        for norm in row.get("norms", []):
            slots = norm.get("slots") or {}
            if norm.get("modality") in MODAL:
                for actor in sorted(actor_keys(slots.get("actor") or "", aliases)):
                    groups.setdefault((scope, "by_actor", norm["modality"], actor), set()).add(row["unit_id"])
            for slot in ("deadlines", "quantities"):
                if _filled(slots, slot):
                    groups.setdefault((scope, slot, "any", None), set()).add(row["unit_id"])
    out = []
    for (scope, kind, modality, actor), unit_ids in sorted(groups.items(), key=lambda item: (item[0][0], item[0][1], item[0][2], item[0][3] or "")):
        if len(unit_ids) < min_units:
            continue
        where = _title(scope, units_by_id, titles)
        if kind == "by_actor":
            text = (f"Theo {where}, {actor} có những {MODAL[modality]} nào?" if modality != "prohibition"
                    else f"Theo {where}, những hành vi nào bị cấm đối với {actor}?")
            criteria = {"modality": modality, "actor": actor, "required_slots": []}
        else:
            text = f"Theo {where}, có những {'thời hạn' if kind == 'deadlines' else 'mức, tỉ lệ hoặc số lượng'} nào được quy định?"
            criteria = {"modality": "any", "actor": None, "required_slots": [kind]}
        number = len(out) + 1
        out.append({"question_id": f"enum-v1-{number:03d}", "family_id": f"enum-v1-{number:03d}", "question": text,
                    "question_type": "enumeration", "enumeration_kind": kind, "expected_status": "answer", "scope": scope,
                    "criteria": criteria, "relevant_unit_ids": sorted(unit_ids), "annotation_status": "draft",
                    "draft_version": DRAFT_VERSION})
    return out


def check_sheet(path, questions, gold_rows, units):
    """A CSV for the two annotators: one row per (question, answer unit) with the unit text and the gold norms, plus
    empty `keep` and `note` columns; the judgement is a text comparison, not a legal opinion."""
    units_by_id = {u["unit_id"]: u for u in units}
    norms = {}
    for row in gold_rows:
        norms.setdefault(row["unit_id"], []).extend(row.get("norms", []))
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["question_id", "question", "criteria", "unit_id", "unit_text", "gold_norms", "keep", "note"])
        for question in questions:
            for unit_id in question["relevant_unit_ids"]:
                summary = "; ".join(f"{n.get('modality')}: {(n.get('slots') or {}).get('actor') or '-'} / {(n.get('slots') or {}).get('action') or '-'}"
                                    for n in norms.get(unit_id, []))
                writer.writerow([question["question_id"], question["question"], str(question["criteria"]), unit_id,
                                 units_by_id.get(unit_id, {}).get("text", "")[:600], summary, "", ""])
