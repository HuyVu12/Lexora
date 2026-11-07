"""Extraction gold set for RQ1 (`extraction-gold-v1`): templates, checks, agreement and P/R/F1.

A gold file is JSONL with one row per sentence of the chosen leaf units:
  {"unit_id", "unit_version_id", "sentence": {"start", "end"}, "text", "norms": [
      {"modality", "modality_cue", "slots": {"actor": "...", "action": "...", ...}}]}
Offsets are document offsets; every slot value must be an exact quote of the sentence (`check`). Two annotators
fill copies of the same template independently; `agreement` compares them, and the adjudicated file is the gold.

Matching rules, fixed before any run:
- slot (entity) level, per sentence and slot name: strict = equal after case folding, whitespace and edge
  punctuation normalization; lenient = one normalized value contains the other (a boundary disagreement) or
  token Jaccard >= 0.5. One gold value matches at most one prediction.
- norm (relation) level, per sentence: a pair matches when the modality is equal, the actions match and the
  actors match (both empty, or matching); pairs are taken greedily by similarity, each norm used once.
Predictions come from the rule baseline (`norm-rules-v2`, structured sentences only; cue-only review flags carry
no slots and are left out) or from a knowledge-base run (DK3 or DK4 claims), on exactly the gold sentences.
"""

import random
import re

from legal_ai.common.io import digest
from legal_ai.extraction.llm_norms import LLM_SLOTS, locate
from legal_ai.extraction.norms import leaf_units, match_sentence, sentences
from legal_ai.research.questions import kappa

GOLD_VERSION = "extraction-gold-v1"
QUALIFIERS = ("conditions", "exceptions", "deadlines", "quantities")
_TOKEN = re.compile(r"[^\W_]+|%", re.UNICODE)


def _article(unit_id):
    match = re.match(r"(.*?/article-[^/]+)", unit_id)
    return match.group(1) if match else unit_id


def sample_articles(units, count, seed="lexora-gold-v1"):
    """`count` article unit IDs, spread over documents in proportion to their article counts, seeded."""
    articles = sorted({_article(u["unit_id"]) for u in leaf_units(units) if "/article-" in u["unit_id"]})
    by_doc = {}
    for article in articles:
        by_doc.setdefault(article.split("/", 1)[0], []).append(article)
    chosen = []
    for document, items in sorted(by_doc.items()):
        share = max(1, round(count * len(items) / len(articles)))
        chosen += sorted(items, key=lambda a: digest(f"{seed}:{a}"))[:share]
    rng = random.Random(seed)
    while len(chosen) > count:
        chosen.remove(rng.choice(sorted(chosen)))
    return sorted(chosen)


def template(units, article_ids):
    """Empty gold rows for every sentence of the leaf units under these articles."""
    wanted = set(article_ids)
    rows = []
    for unit in sorted(leaf_units(units), key=lambda u: (u["document_id"], u["source_start"])):
        if _article(unit["unit_id"]) not in wanted:
            continue
        for start, end, text in sentences(unit):
            rows.append({"gold_version": GOLD_VERSION, "unit_id": unit["unit_id"], "unit_version_id": unit["unit_version_id"],
                         "sentence": {"start": unit["source_start"] + start, "end": unit["source_start"] + end}, "text": text, "norms": []})
    missing = wanted - {_article(r["unit_id"]) for r in rows}
    if missing:
        raise ValueError(f"articles without sentences in this bundle: {sorted(missing)[:3]}")
    return rows


def check(rows, units):
    """Problems of a filled gold file: unknown units, moved sentences, values that are not exact quotes."""
    by_id = {u["unit_id"]: u for u in units}
    problems = []
    for number, row in enumerate(rows, 1):
        unit = by_id.get(row.get("unit_id"))
        if unit is None or unit["unit_version_id"] != row.get("unit_version_id"):
            problems.append(f"row {number}: unknown unit or version")
            continue
        start, end = row["sentence"]["start"] - unit["source_start"], row["sentence"]["end"] - unit["source_start"]
        if unit["text"][start:end] != row["text"]:
            problems.append(f"row {number}: sentence text does not match its offsets")
            continue
        for index, norm in enumerate(row.get("norms") or [], 1):
            if norm.get("modality") not in ("obligation", "prohibition", "entitlement", "permission", "unknown"):
                problems.append(f"row {number} norm {index}: modality")
            for name, value in (norm.get("slots") or {}).items():
                if name not in LLM_SLOTS:
                    problems.append(f"row {number} norm {index}: unknown slot {name}")
                elif value not in (None, "") and locate(unit["text"], start, end, value) is None:
                    problems.append(f"row {number} norm {index}: {name} is not an exact quote")
            if not (norm.get("slots") or {}).get("action"):
                problems.append(f"row {number} norm {index}: action missing")
    return problems


def _key(row):
    return (row["unit_id"], row["sentence"]["start"], row["sentence"]["end"])


def rule_predictions(units, gold_rows):
    """The rule baseline on the gold sentences, in gold format."""
    by_id = {u["unit_id"]: u for u in units}
    rows = []
    for row in gold_rows:
        unit = by_id[row["unit_id"]]
        offset = row["sentence"]["start"] - unit["source_start"]
        found = match_sentence(unit, offset, row["text"])
        norms = []
        if found:
            spans, modality, cue, _rule = found
            norms.append({"modality": modality, "modality_cue": unit["text"][cue[0]:cue[1]] if cue else None,
                          "slots": {name: unit["text"][s:e] for name, (s, e) in spans.items() if name in LLM_SLOTS and e > s}})
        rows.append(row | {"norms": norms})
    return rows


def claim_predictions(claims, gold_rows):
    """DK3/DK4 claims on the gold sentences, in gold format (claims on other sentences are ignored)."""
    grouped = {}
    for claim in claims:
        grouped.setdefault((claim["unit_id"], claim["sentence"]["start"], claim["sentence"]["end"]), []).append(
            {"modality": claim.get("modality"), "modality_cue": claim.get("modality_cue"),
             "slots": {k: v for k, v in (claim.get("slots") or {}).items() if isinstance(v, str) and v.strip()}})
    return [row | {"norms": grouped.get(_key(row), [])} for row in gold_rows]


def normalize(value):
    return " ".join(str(value).casefold().split()).strip(" .,;:\"'“”()")


def _tokens(value):
    return set(_TOKEN.findall(normalize(value)))


def similarity(a, b):
    left, right = _tokens(a), _tokens(b)
    return len(left & right) / len(left | right) if left | right else 1.0


def lenient_match(a, b):
    left, right = normalize(a), normalize(b)
    return bool(left and right) and (left in right or right in left or similarity(a, b) >= 0.5)


def _match_values(gold, predicted, strict):
    """Greedy one-to-one matching of two value lists; returns the number of matched pairs."""
    pairs = sorted(((similarity(g, p), i, j) for i, g in enumerate(gold) for j, p in enumerate(predicted)), reverse=True)
    used_g, used_p, matched = set(), set(), 0
    for score, i, j in pairs:
        if i in used_g or j in used_p:
            continue
        if (normalize(gold[i]) == normalize(predicted[j])) if strict else lenient_match(gold[i], predicted[j]):
            used_g.add(i)
            used_p.add(j)
            matched += 1
    return matched


def _slot_match(a, b, strict):
    if not a and not b:
        return True
    if not a or not b:
        return False
    return normalize(a) == normalize(b) if strict else lenient_match(a, b)


def _match_norms(gold, predicted, strict):
    """[(gold index, predicted index)] of matched norms."""
    pairs = []
    for i, g in enumerate(gold):
        for j, p in enumerate(predicted):
            gs, ps = g.get("slots") or {}, p.get("slots") or {}
            if g.get("modality") == p.get("modality") and _slot_match(gs.get("action"), ps.get("action"), strict) \
                    and _slot_match(gs.get("actor"), ps.get("actor"), strict):
                pairs.append((similarity(gs.get("action", ""), ps.get("action", "")), i, j))
    used_g, used_p, matched = set(), set(), []
    for _, i, j in sorted(pairs, reverse=True):
        if i not in used_g and j not in used_p:
            used_g.add(i)
            used_p.add(j)
            matched.append((i, j))
    return matched


def _prf(tp, gold, predicted):
    precision = tp / predicted if predicted else None
    recall = tp / gold if gold else None
    f1 = 2 * precision * recall / (precision + recall) if precision and recall else (0.0 if precision is not None and recall is not None else None)
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "gold": gold, "predicted": predicted}


def score(gold_rows, predicted_rows):
    """Micro P/R/F1 of slots (overall, per slot, qualifiers) and norms, strict and lenient."""
    predicted = {_key(r): r for r in predicted_rows}
    report = {"gold_version": GOLD_VERSION, "sentences": len(gold_rows)}
    for mode, strict in (("strict", True), ("lenient", False)):
        slot_counts = {name: [0, 0, 0] for name in LLM_SLOTS}
        norm_counts = [0, 0, 0]
        for row in gold_rows:
            gold_norms = row.get("norms") or []
            pred_norms = (predicted.get(_key(row)) or {}).get("norms") or []
            norm_counts[0] += len(_match_norms(gold_norms, pred_norms, strict))
            norm_counts[1] += len(gold_norms)
            norm_counts[2] += len(pred_norms)
            for name in LLM_SLOTS:
                g = [n["slots"][name] for n in gold_norms if (n.get("slots") or {}).get(name)]
                p = [n["slots"][name] for n in pred_norms if (n.get("slots") or {}).get(name)]
                slot_counts[name][0] += _match_values(g, p, strict)
                slot_counts[name][1] += len(g)
                slot_counts[name][2] += len(p)
        total = [sum(c[i] for c in slot_counts.values()) for i in range(3)]
        qualifiers = [sum(slot_counts[n][i] for n in QUALIFIERS) for i in range(3)]
        report[mode] = {"norms": _prf(*norm_counts), "slots": _prf(*total), "qualifiers": _prf(*qualifiers),
                        "per_slot": {name: _prf(*counts) for name, counts in slot_counts.items() if counts[1] or counts[2]}}
    return report


def agreement(first_rows, second_rows):
    """Agreement of two annotators on the same template: kappa on has-norm per sentence and on the modality of
    matched norms (lenient), plus slot and norm F1 with the first annotator as reference."""
    second = {_key(r): r for r in second_rows}
    if set(second) != {_key(r) for r in first_rows}:
        raise ValueError("the two files must cover the same sentences")
    has_a, has_b, mod_a, mod_b = [], [], [], []
    for row in first_rows:
        a, b = row.get("norms") or [], second[_key(row)].get("norms") or []
        has_a.append(bool(a))
        has_b.append(bool(b))
        for i, j in _match_norms([n | {"modality": "any"} for n in a], [n | {"modality": "any"} for n in b], False):
            mod_a.append(a[i].get("modality"))
            mod_b.append(b[j].get("modality"))
    report = score(first_rows, second_rows)
    return {"sentences": len(first_rows), "kappa_has_norm": kappa(has_a, has_b), "kappa_modality_matched": kappa(mod_a, mod_b),
            "matched_norm_pairs": len(mod_a), "f1_strict": {k: report["strict"][k]["f1"] for k in ("norms", "slots")},
            "f1_lenient": {k: report["lenient"][k]["f1"] for k in ("norms", "slots")}}
