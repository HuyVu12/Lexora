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

Partial double annotation: when a gold set declares an agreement sample (`agreement_sample`), only the sample is
labelled by both annotators; each exported row then carries `annotation` = {"mode": "double" | "single",
"annotators", "decided_by", "in_sample"}, and `score` adds the same P/R/F1 on the double-annotated rows alone.
Rows without `annotation` (older gold files) are scored as before.

Inherited slots (`gold-inherited-v1`, declared before any comparison): `claims-inherit-v1` fills an empty actor,
action or outcome of a claim from the parent's lead-in, while the gold guideline tells annotators to leave a value
empty when it lives only in the lead-in, so an inherited value scores as a wrong guess. `inherited="score"` (the
default, the earlier behaviour) scores claims as they are; `inherited="ignore"` scores each claim with the slots
named in its `inheritance` provenance removed, so a derived knowledge base is scored on what the model extracted
from the sentence. Either way, when claims carry inheritance (or the mode is `ignore`), `score_claims` adds an
`inherited` block that counts the inherited values on the gold sentences and, where the gold left that slot empty
for the sentence, how many of them are verbatim at their recorded span inside the parent's lead-in of the bundle:
a sanity count of what the guideline expects, not a score.
"""

from fractions import Fraction
import math
import random
import re

from legal_ai.common.io import digest
from legal_ai.extraction.inherit import lead_in
from legal_ai.extraction.llm_norms import LLM_SLOTS, locate
from legal_ai.extraction.norms import leaf_units, match_sentence, sentences
from legal_ai.research.questions import kappa

GOLD_VERSION = "extraction-gold-v1"
SAMPLE_METHOD = "document-largest-remainder-v1"
SAMPLE_SEED = "lexora-gold-agreement-v1"
SAMPLE_SHARE = "0.3"
QUALIFIERS = ("conditions", "exceptions", "deadlines", "quantities")
INHERITED_SCORING = "gold-inherited-v1"
INHERITED_MODES = ("score", "ignore")
_TOKEN = re.compile(r"[^\W_]+|%", re.UNICODE)


def _article(unit_id):
    match = re.match(r"(.*?/article-[^/]+)", unit_id)
    return match.group(1) if match else unit_id


def article_id(unit_id):
    """The article unit ID a unit belongs to (the unit ID itself when it is not under an article)."""
    return _article(unit_id)


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


def sample_share(share):
    """The share as an exact fraction in (0, 1]; decimals are read from their text so 0.3 is exactly 3/10."""
    try:
        value = Fraction(str(share).strip())
    except (ValueError, ZeroDivisionError):
        raise ValueError("share must be a number between 0 and 1") from None
    if not 0 < value <= 1:
        raise ValueError("share must be greater than 0 and at most 1")
    return value


def sample_allocation(article_ids, share=SAMPLE_SHARE, seed=SAMPLE_SEED):
    """{document: number of sample articles}: `round(share * articles)` seats (half up, at least one), shared over
    documents by the largest-remainder (Hamilton) method on exact fractions, so a document gets its proportional
    quota rounded down plus at most one more seat; equal remainders are ordered by a seeded hash of the document ID.
    A document with one article out of forty therefore gets a seat only when its remainder wins, never by a floor."""
    articles = sorted(set(article_ids))
    if not articles:
        raise ValueError("no articles to sample")
    by_doc = {}
    for article in articles:
        by_doc.setdefault(article.split("/", 1)[0], []).append(article)
    count = min(len(articles), max(1, math.floor(sample_share(share) * len(articles) + Fraction(1, 2))))
    quotas = {document: Fraction(count * len(items), len(articles)) for document, items in by_doc.items()}
    seats = {document: math.floor(quota) for document, quota in quotas.items()}
    order = sorted(by_doc, key=lambda d: (-(quotas[d] - seats[d]), digest(f"{seed}:{d}")))
    for document in order[:count - sum(seats.values())]:
        seats[document] += 1
    return dict(sorted(seats.items()))


def agreement_sample(article_ids, share=SAMPLE_SHARE, seed=SAMPLE_SEED):
    """The article IDs both annotators label (`document-largest-remainder-v1`): a pure function of the set's
    articles, the share and the seed, so every machine computes the same list. Seats per document come from
    `sample_allocation`; inside a document the articles are taken in the order of a seeded hash of their IDs."""
    articles = sorted(set(article_ids))
    chosen = []
    for document, seats in sample_allocation(articles, share, seed).items():
        items = [a for a in articles if a.split("/", 1)[0] == document]
        chosen += sorted(items, key=lambda a: digest(f"{seed}:{a}"))[:seats]
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
            if not any((norm.get("slots") or {}).get(name) for name in ("action", "object", "conditions", "exceptions", "quantities", "deadlines", "outcome")):
                problems.append(f"row {number} norm {index}: no content slot")
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


def _inherited_slots(claim):
    """Names of the slots `claims-inherit-v1` filled in this claim (empty for a claim without provenance)."""
    return set(((claim.get("inheritance") or {}).get("slots") or {}))


def claim_predictions(claims, gold_rows, inherited="score"):
    """DK3/DK4 claims on the gold sentences, in gold format (claims on other sentences are ignored). With
    `inherited="ignore"` the slots a claim inherited from the lead-in are left out (`gold-inherited-v1`)."""
    if inherited not in INHERITED_MODES:
        raise ValueError(f"inherited must be one of {list(INHERITED_MODES)}")
    grouped = {}
    for claim in claims:
        dropped = _inherited_slots(claim) if inherited == "ignore" else set()
        grouped.setdefault((claim["unit_id"], claim["sentence"]["start"], claim["sentence"]["end"]), []).append(
            {"modality": claim.get("modality"), "modality_cue": claim.get("modality_cue"),
             "slots": {k: v for k, v in (claim.get("slots") or {}).items() if isinstance(v, str) and v.strip() and k not in dropped}})
    return [row | {"norms": grouped.get(_key(row), [])} for row in gold_rows]


def inherited_report(claims, gold_rows, units, inherited="score"):
    """Counts of inherited values on the gold sentences (`gold-inherited-v1`), not a score: per slot, how many
    values were inherited, how many sit where the gold left that slot empty in every norm of the sentence (and of
    those, how many are verbatim at their recorded span inside the parent's lead-in in the bundle, and how many are
    on a sentence the gold gives no norm at all), and how many
    sit where the gold filled the slot (and of those, how many match a gold value leniently)."""
    by_version = {unit["unit_version_id"]: unit for unit in units}
    by_id = {unit["unit_id"]: unit for unit in units}
    gold = {_key(row): row for row in gold_rows}
    counts = {}
    claims_with = 0
    for claim in claims:
        row = gold.get((claim["unit_id"], claim["sentence"]["start"], claim["sentence"]["end"]))
        names = _inherited_slots(claim)
        if row is None or not names:
            continue
        claims_with += 1
        place = lead_in(by_version.get(claim.get("unit_version_id")), by_id)
        for name in sorted(names):
            entry = counts.setdefault(name, {"values": 0, "gold_slot_empty": 0, "gold_slot_empty_lead_in_verbatim": 0,
                                             "gold_sentence_without_norm": 0, "gold_slot_filled": 0, "gold_slot_filled_lenient_match": 0})
            value = (claim.get("slots") or {}).get(name)
            entry["values"] += 1
            golds = [n["slots"][name] for n in row.get("norms") or [] if (n.get("slots") or {}).get(name)]
            if golds:
                entry["gold_slot_filled"] += 1
                entry["gold_slot_filled_lenient_match"] += any(lenient_match(g, value) for g in golds)
                continue
            entry["gold_slot_empty"] += 1
            entry["gold_sentence_without_norm"] += not row.get("norms")
            span = (claim["inheritance"]["slots"][name] or {}).get("span")
            if place is not None and isinstance(span, list) and len(span) == 2:
                parent, lead_start, lead_end = place
                start, end = span[0] - parent["source_start"], span[1] - parent["source_start"]
                entry["gold_slot_empty_lead_in_verbatim"] += lead_start <= start < end <= lead_end and parent["text"][start:end] == value
    total = {key: sum(entry[key] for entry in counts.values()) for key in
             ("values", "gold_slot_empty", "gold_slot_empty_lead_in_verbatim", "gold_sentence_without_norm", "gold_slot_filled",
              "gold_slot_filled_lenient_match")}
    return {"scoring": INHERITED_SCORING, "mode": inherited, "claims_with_inherited_slots": claims_with,
            "total": total, "per_slot": dict(sorted(counts.items()))}


def score_claims(gold_rows, claims, units, inherited="score"):
    """`score` of knowledge-base claims under the chosen inherited-slot mode; the `inherited` block is added when
    any claim carries inheritance or the mode is `ignore`, so scores of runs without inheritance stay as before."""
    report = score(gold_rows, claim_predictions(claims, gold_rows, inherited))
    if inherited == "ignore" or any(_inherited_slots(claim) for claim in claims):
        report["inherited"] = inherited_report(claims, gold_rows, units, inherited)
    return report


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
    """Micro P/R/F1 of slots (overall, per slot, qualifiers) and norms, strict and lenient. When the gold rows
    carry `annotation` (a set with an agreement sample), `double_annotated` repeats the report on the rows two
    people labelled, and `annotation` counts the double and single rows."""
    report = {"gold_version": GOLD_VERSION} | _score(gold_rows, predicted_rows)
    if any("annotation" in row for row in gold_rows):
        double = [row for row in gold_rows if (row.get("annotation") or {}).get("mode") == "double"]
        report["annotation"] = {"double": len(double), "single": len(gold_rows) - len(double)}
        report["double_annotated"] = _score(double, predicted_rows)
    return report


def _score(gold_rows, predicted_rows):
    predicted = {_key(r): r for r in predicted_rows}
    report = {"sentences": len(gold_rows)}
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
