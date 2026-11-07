"""Planted errors for RQ2 (`error-injection-v1`): how many errors of each type the automatic validator catches,
and how many clean claims it rejects.

Clean claims are the DK4 claims of a knowledge-base run (they passed `kb-validator-v1`). For every error type a
seeded sample of clean claims is copied and corrupted in one way; each copy and each clean claim is validated on
its own, so duplicate detection does not interfere. Types marked `expected_detectable: false` change meaning while
every quote stays verbatim (a dropped negation, exception or condition); the validator is not built to see them,
and they are kept on purpose so the report shows its limits instead of only the easy errors.
"""

import json
from pathlib import Path
import random
import re

from legal_ai.common.io import canonical, digest, read_jsonl, write_json, write_jsonl
from legal_ai.validation.claims import VALIDATOR_VERSION, validate

INJECTION_VERSION = "error-injection-v1"
OTHER_ACTOR = "Cơ quan quản lý nhà nước về lao động"


def _slot(claim, names):
    return next((name for name in names if isinstance(claim["slots"].get(name), str) and claim["slots"][name].strip()), None)


def _alter_quote(claim, rng, _pool, _units):
    name = _slot(claim, ("action", "object", "actor", "conditions"))
    words = claim["slots"][name].split()
    position = rng.randrange(len(words))
    words[position] = words[position] + "x"
    return {"slots": claim["slots"] | {name: " ".join(words)}}


def _swap_action(claim, rng, pool, _units):
    others = [c for c in pool if c["sentence"] != claim["sentence"] and c["slots"].get("action") and c["slots"]["action"] != claim["slots"]["action"]]
    if not others:
        return None
    return {"slots": claim["slots"] | {"action": rng.choice(others)["slots"]["action"]}}


def _fabricate_actor(claim, _rng, _pool, _units):
    return {"slots": claim["slots"] | {"actor": OTHER_ACTOR}}


def _change_number(claim, rng, _pool, _units):
    name = next((n for n in ("quantities", "deadlines", "action", "object", "conditions")
                 if isinstance(claim["slots"].get(n), str) and re.search(r"\d", claim["slots"][n])), None)
    if name is None:
        return None
    value = claim["slots"][name]
    digits = [m.start() for m in re.finditer(r"\d", value)]
    at = rng.choice(digits)
    changed = value[:at] + str((int(value[at]) + rng.randint(1, 8)) % 10) + value[at + 1:]
    return {"slots": claim["slots"] | {name: changed}}


def _wrong_unit(claim, rng, _pool, units):
    others = [u for u in units if u["unit_id"] != claim["unit_id"] and u["source_end"] - u["source_start"] > 20]
    unit = rng.choice(others)
    return {"unit_id": unit["unit_id"], "unit_version_id": unit["unit_version_id"]}


def _stale_version(claim, _rng, _pool, _units):
    return {"unit_version_id": digest("stale:" + claim["unit_version_id"])}


def _invalid_modality(_claim, _rng, _pool, _units):
    return {"modality": "duty"}


def _flip_modality(claim, _rng, _pool, _units):
    flipped = {"obligation": "prohibition", "prohibition": "obligation", "entitlement": "obligation", "permission": "prohibition"}
    if claim["modality"] not in flipped:
        return None
    return {"modality": flipped[claim["modality"]]}


def _drop_negation(claim, _rng, _pool, _units):
    if claim["modality"] != "prohibition" or not isinstance(claim.get("modality_cue"), str) or not claim["modality_cue"].lower().startswith("không "):
        return None
    return {"modality": "permission", "modality_cue": claim["modality_cue"].split(" ", 1)[1]}


def _drop_slot(name):
    def corrupt(claim, _rng, _pool, _units):
        if not claim["slots"].get(name):
            return None
        return {"slots": claim["slots"] | {name: None}}
    return corrupt


TYPES = {  # name: (corruption, expected_detectable, check expected to fire)
    "quote_altered": (_alter_quote, True, "V3_evidence"),
    "action_from_other_sentence": (_swap_action, True, "V3_evidence"),
    "fabricated_actor": (_fabricate_actor, True, "V3_evidence"),
    "number_changed": (_change_number, True, "V3_evidence"),
    "wrong_unit": (_wrong_unit, True, "V2_integrity"),
    "stale_unit_version": (_stale_version, True, "V2_integrity"),
    "invalid_modality": (_invalid_modality, True, "V1_schema"),
    "modality_flipped": (_flip_modality, True, "V4_modality"),
    "negation_dropped": (_drop_negation, False, None),
    "exception_dropped": (_drop_slot("exceptions"), False, None),
    "condition_dropped": (_drop_slot("conditions"), False, None),
}


def inject(clean, units, per_type=30, seed="lexora-inject-v1"):
    """Corrupted copies: up to `per_type` per type, each from a different clean claim where the type applies."""
    injected = []
    for name, (corrupt, detectable, check) in TYPES.items():
        rng = random.Random(f"{seed}:{name}")
        order = sorted(clean, key=lambda c: digest(f"{seed}:{name}:{c['claim_id']}"))
        made = 0
        for claim in order:
            if made == per_type:
                break
            if name == "quote_altered" and _slot(claim, ("action", "object", "actor", "conditions")) is None:
                continue
            change = corrupt(claim, rng, clean, units)
            if not change:
                continue
            copy = json.loads(canonical(claim)) | change
            for key in ("evidence", "validation"):
                copy.pop(key, None)
            copy["claim_id"] = "inj:" + digest(canonical([seed, name, claim["claim_id"]]))[:16]
            copy["injection"] = {"type": name, "source_claim_id": claim["claim_id"], "expected_detectable": detectable, "expected_check": check}
            injected.append(copy)
            made += 1
    return injected


def run(kb_dir, units, output, per_type=30, seed="lexora-inject-v1"):
    kb_dir, output = Path(kb_dir), Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("output must be empty: use a new directory")
    clean = [{k: v for k, v in c.items() if k not in ("evidence", "validation")} for c in read_jsonl(kb_dir / "dk4.jsonl")]
    injected = inject(clean, units, per_type, seed)
    verdict = lambda claim: validate([claim], units)[0]
    clean_results = [verdict(c) for c in clean]
    injected_results = [verdict(c) for c in injected]
    by_type = {}
    for claim, result in zip(injected, injected_results):
        meta = claim["injection"]
        row = by_type.setdefault(meta["type"], {"expected_detectable": meta["expected_detectable"], "expected_check": meta["expected_check"],
                                                "injected": 0, "rejected": 0, "rejected_by_expected_check": 0})
        row["injected"] += 1
        row["rejected"] += result["decision"] == "rejected"
        row["rejected_by_expected_check"] += bool(meta["expected_check"]) and result["checks"].get(meta["expected_check"]) == "fail"
    for row in by_type.values():
        row["detection_rate"] = row["rejected"] / row["injected"] if row["injected"] else None
    false_rejects = sum(r["decision"] == "rejected" for r in clean_results)
    caught = sum(r["decision"] == "rejected" for r in injected_results)
    detectable = [(c, r) for c, r in zip(injected, injected_results) if c["injection"]["expected_detectable"]]
    report = {"injection_version": INJECTION_VERSION, "validator_version": VALIDATOR_VERSION, "seed": seed, "per_type": per_type,
              "kb_run": kb_dir.as_posix(), "dk4_sha256": digest((kb_dir / "dk4.jsonl").read_bytes()),
              "clean_claims": len(clean), "false_rejects_on_clean": false_rejects,
              "false_reject_rate": false_rejects / len(clean) if clean else None,
              "injected": len(injected), "caught": caught,
              "detection_rate_detectable_types": sum(r["decision"] == "rejected" for _, r in detectable) / len(detectable) if detectable else None,
              "detection_precision": caught / (caught + false_rejects) if caught + false_rejects else None,
              "by_type": dict(sorted(by_type.items())),
              "notes": ["Types with expected_detectable=false keep every quote verbatim; the validator is not designed to catch them",
                        "Clean means accepted by kb-validator-v1 in DK4, not checked against the human gold set"]}
    write_jsonl(output / "injected.jsonl", injected)
    write_jsonl(output / "results.jsonl", [{"claim_id": c["claim_id"], "kind": "injected", **r} for c, r in zip(injected, injected_results)]
                + [{"claim_id": c["claim_id"], "kind": "clean", **r} for c, r in zip(clean, clean_results)])
    write_json(output / "report.json", report)
    return report
