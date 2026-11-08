"""Is a claim the validator rejected actually wrong? (`rejection-audit-v1`)

The validator rejects a claim when a slot value or the modality cue is not an exact quote of the claim's own
sentence. That is not the same as being wrong: in a list ("2. Người lao động có quyền ... trong trường hợp sau
đây: ... e) Đủ tuổi nghỉ hưu ...") a model may fill the actor and action of point e) from the lead-in of clause 2,
which is legally right but not in the sentence of point e).

Two measurements:

- `explain` (automatic, every rejected claim): for each slot or cue that is not verbatim in the sentence, where
  the text can be found instead: elsewhere in the same unit, in an ancestor unit (the lead-in of the clause, the
  article heading), or nowhere. A claim is `context` when every such value is found in the unit or its ancestors,
  `not_found` when at least one value is nowhere, `modality_only` when only the cue's meaning was wrong
  (`modality_cue_mismatch`) and no value is missing.
- `make_sheet` / `score_sheet` (people): a seeded, blinded sample of rejected and accepted claims of one or more
  runs in a CSV; annotators label each claim against the statute without seeing the model or the validator's
  decision. The key file maps items back. Labels, most severe first when several apply:
  `sai` (says something the law does not say, or contradicts it), `dien_dat` (right meaning, reworded),
  `dung_ngu_canh` (right, with words taken from the lead-in or heading), `dung` (right and verbatim),
  `khong_ro` (cannot decide). `score_sheet` reports, per run and per validator decision, how many claims are
  wrong; `agreement` gives Cohen's kappa of two annotators.
"""

import csv
import json
from pathlib import Path
import random

from legal_ai.common.io import canonical, digest, read_jsonl, write_json
from legal_ai.extraction.llm_norms import LLM_SLOTS, locate
from legal_ai.research.questions import kappa

AUDIT_VERSION = "rejection-audit-v1"
LABELS = ("sai", "dien_dat", "dung_ngu_canh", "dung", "khong_ro")
SLOT_NAMES = {"actor": "Chủ thể", "action": "Hành vi", "object": "Đối tượng", "beneficiary": "Bên thụ hưởng", "recipient": "Bên nhận",
              "conditions": "Điều kiện", "exceptions": "Ngoại lệ", "deadlines": "Thời hạn", "quantities": "Định lượng", "outcome": "Kết quả"}
MODALITY_NAMES = {"obligation": "nghĩa vụ", "prohibition": "cấm", "permission": "được phép", "entitlement": "quyền", "unknown": "chưa rõ"}
COLUMNS = ["item_id", "context", "unit_text", "sentence", "norm", "label", "note"]


def _run(run_dir):
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    units = {u["unit_id"]: u for u in read_jsonl(Path(manifest["bundle"]) / "units.jsonl")}
    validation = {r["claim_id"]: r for r in read_jsonl(run_dir / "validation.jsonl")}
    return manifest, units, read_jsonl(run_dir / "dk3.jsonl"), validation


def _ancestors(unit, units):
    chain, parent = [], units.get(unit.get("parent_id"))
    while parent is not None:
        chain.append(parent)
        parent = units.get(parent.get("parent_id"))
    return chain


def _where(value, unit, ancestors):
    if locate(unit["text"], 0, len(unit["text"]), value) is not None:
        return "unit"
    if any(locate(a["text"], 0, len(a["text"]), value) is not None for a in ancestors):
        return "ancestor"
    return "nowhere"


def explain_claim(claim, result, units):
    """{"category": ..., "values": {slot or "modality_cue": "unit" | "ancestor" | "nowhere"}} for one rejected claim."""
    unit = units.get(claim["unit_id"])
    reasons = [r.split(":", 1)[0] for r in result["reasons"]]
    if unit is None:
        return {"category": "other", "values": {}}
    ancestors = _ancestors(unit, units)
    values = {}
    for reason in reasons:
        if reason.endswith("_not_verbatim"):
            name = reason[: -len("_not_verbatim")]
            value = claim.get("modality_cue") if name == "modality_cue" else (claim.get("slots") or {}).get(name)
            values[name] = _where(value, unit, ancestors)
    if any(where == "nowhere" for where in values.values()):
        category = "not_found"
    elif values:
        category = "context"
    elif "modality_cue_mismatch" in reasons:
        category = "modality_only"
    else:
        category = "other"  # Schema, integrity or duplicate.
    return {"category": category, "values": values}


def explain(run_dir):
    """Automatic breakdown of every rejected claim of one knowledge-base run."""
    manifest, units, claims, validation = _run(run_dir)
    categories, places = {}, {}
    for claim in claims:
        result = validation.get(claim["claim_id"])
        if result is None or result["decision"] == "accepted":
            continue
        found = explain_claim(claim, result, units)
        categories[found["category"]] = categories.get(found["category"], 0) + 1
        for where in found["values"].values():
            places[where] = places.get(where, 0) + 1
    rejected = sum(categories.values())
    return {"audit_version": AUDIT_VERSION, "model": manifest.get("model"), "rejected": rejected,
            "categories": dict(sorted(categories.items())), "values_found": dict(sorted(places.items()))}


def _norm_text(claim):
    lines = [f"Tính quy phạm: {MODALITY_NAMES.get(claim.get('modality'), claim.get('modality'))}"
             + (f" (từ: \"{claim['modality_cue']}\")" if claim.get("modality_cue") else "")]
    lines += [f"{SLOT_NAMES[name]}: {value}" for name in LLM_SLOTS if (value := (claim.get("slots") or {}).get(name)) not in (None, "")]
    return "\n".join(lines)


def make_sheet(run_dirs, sheet_path, key_path, rejected=30, accepted=10, seed="lexora-rejection-audit-v1"):
    """Blinded CSV of a seeded sample: per run, `rejected` rejected and `accepted` accepted claims, shuffled together."""
    pool = []
    for run_dir in run_dirs:
        manifest, units, claims, validation = _run(run_dir)
        groups = {"rejected": [], "accepted": []}
        for claim in claims:
            result = validation.get(claim["claim_id"])
            if result is not None and claim["unit_id"] in units:
                groups["accepted" if result["decision"] == "accepted" else "rejected"].append((claim, result))
        rng = random.Random(canonical([seed, manifest.get("run_id")]))
        for decision, size in (("rejected", rejected), ("accepted", accepted)):
            for claim, result in rng.sample(groups[decision], min(size, len(groups[decision]))):
                pool.append((run_dir, manifest, units, claim, result, decision))
    random.Random(seed).shuffle(pool)
    key, rows = {}, []
    for run_dir, manifest, units, claim, result, decision in pool:
        unit = units[claim["unit_id"]]
        item_id = "R" + digest(canonical([seed, manifest.get("run_id"), claim["claim_id"]]))[:10]
        start, end = claim["sentence"]["start"] - unit["source_start"], claim["sentence"]["end"] - unit["source_start"]
        context = "\n".join(a["text"].strip() for a in reversed(_ancestors(unit, units)) if a["unit_type"] in ("article", "clause", "point"))
        rows.append({"item_id": item_id, "context": context, "unit_text": unit["text"].strip(),
                     "sentence": unit["text"][start:end].strip(), "norm": _norm_text(claim)})
        key[item_id] = {"run": Path(run_dir).as_posix(), "model": manifest.get("model"), "claim_id": claim["claim_id"], "decision": decision,
                        "reasons": result["reasons"], "automatic": explain_claim(claim, result, units)["category"] if decision == "rejected" else None}
    with Path(sheet_path).open("w", encoding="utf-8-sig", newline="") as handle:  # BOM so spreadsheet apps read UTF-8.
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    write_json(key_path, {"audit_version": AUDIT_VERSION, "seed": seed, "labels": list(LABELS), "items": key})
    return {"items": len(rows), "rejected": sum(v["decision"] == "rejected" for v in key.values()),
            "accepted": sum(v["decision"] == "accepted" for v in key.values())}


def read_labels(sheet_path):
    labels = {}
    with Path(sheet_path).open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            label = (row.get("label") or "").strip()
            if label and label not in LABELS:
                raise ValueError(f"{row['item_id']}: label {label!r} is not one of {list(LABELS)}")
            labels[row["item_id"]] = label or None
    return labels


def score_sheet(sheet_path, key_path):
    """Per model and validator decision: label counts and the share of labelled claims that are wrong (`sai`)."""
    key = json.loads(Path(key_path).read_text(encoding="utf-8"))["items"]
    labels = read_labels(sheet_path)
    unknown = sorted(set(labels) - set(key))
    if unknown:
        raise ValueError(f"items not in the key: {unknown[:3]}")
    report = {}
    for item_id, label in labels.items():
        entry = key[item_id]
        group = report.setdefault(entry["model"], {}).setdefault(entry["decision"], {"items": 0, "labelled": 0, "labels": {}, "by_automatic": {}})
        group["items"] += 1
        if label is None:
            continue
        group["labelled"] += 1
        group["labels"][label] = group["labels"].get(label, 0) + 1
        if entry.get("automatic"):
            cell = group["by_automatic"].setdefault(entry["automatic"], {})
            cell[label] = cell.get(label, 0) + 1
    for groups in report.values():
        for group in groups.values():
            decided = group["labelled"] - group["labels"].get("khong_ro", 0)
            group["wrong_rate"] = {"value": group["labels"].get("sai", 0) / decided if decided else None, "n": decided}
    return {"audit_version": AUDIT_VERSION, "by_model": report}


def agreement(first_sheet, second_sheet):
    a, b = read_labels(first_sheet), read_labels(second_sheet)
    pairs = [(a[i], b[i]) for i in sorted(set(a) & set(b)) if a[i] and b[i]]
    wrong = [(x == "sai", y == "sai") for x, y in pairs]
    return {"labels": {"kappa": kappa([p[0] for p in pairs], [p[1] for p in pairs]) if pairs else None, "n": len(pairs)},
            "wrong_or_not": {"kappa": kappa([p[0] for p in wrong], [p[1] for p in wrong]) if wrong else None, "n": len(wrong)}}
