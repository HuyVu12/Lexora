"""LLM knowledge base for DK3/DK4 (`llm-kb-run-v1`): one extraction snapshot, two conditions.

`extract` sends every sentence of every leaf unit of a frozen corpus bundle to one structured model (Claude Code,
fixed model and effort) in article-sized batches, with the `norm-llm-v1` prompt and schema. Every answer is
appended to `raw.jsonl` as soon as it arrives, keyed by the hash of its request, so an interrupted run resumes
without paying twice; model answers cannot be reproduced by re-running (no seed), so `raw.jsonl` is the record.

`materialize` turns `raw.jsonl` into the two knowledge bases, offline and deterministically:
- `dk3.jsonl`: every norm the model returned, slot strings exactly as given (KB before validation);
- `validation.jsonl`: the automatic validator's result for each DK3 claim;
- `dk4.jsonl`: the accepted DK3 claims with their evidence offsets (KB after automatic validation).
DK4 is a subset of DK3 by construction, so the two differ only by validation.
"""

from datetime import datetime, timezone
import json
from pathlib import Path

from legal_ai.common.io import canonical, digest, read_jsonl, write_json, write_jsonl
from legal_ai.extraction.llm_norms import LLM_SLOTS, MAX_NORMS_PER_SENTENCE, RUN as PROMPT_RUN, SCHEMA, SYSTEM, plan, request_text
from legal_ai.extraction.norms import leaf_units, sentences
from legal_ai.providers.pilot import ProviderError
from legal_ai.validation.claims import VALIDATOR_VERSION, validate

RUN_VERSION = "llm-kb-run-v1"
KB_VERSION = "llm-kb-v1"


def targets(units):
    """Every sentence of every leaf unit, in document order: {unit_version_id, start, end, text} (unit offsets)."""
    rows = []
    for unit in sorted(leaf_units(units), key=lambda u: (u["document_id"], u["source_start"])):
        rows.extend({"unit_version_id": unit["unit_version_id"], "start": start, "end": end, "text": text} for start, end, text in sentences(unit))
    return rows


def batches(units):
    """[(key, article_id, rows, request)] in a stable order; the key is the hash of the request text."""
    planned = []
    for article_id, rows in plan(units, targets(units)):
        request = request_text(units, article_id, rows)
        planned.append((digest(canonical({"system": SYSTEM, "request": request})), article_id, rows, request))
    return planned


def estimate(units):
    planned = batches(units)
    return {"batches": len(planned), "sentences": sum(len(rows) for _, _, rows, _ in planned),
            "request_characters": sum(len(request) for *_, request in planned), "system_characters": len(SYSTEM)}


def extract(bundle_units, provider, output, *, log=None):
    """Call the model for every batch not yet in `output/raw.jsonl`. Returns counts; never retries a failed call."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    raw_path = output / "raw.jsonl"
    done = {row["key"] for row in read_jsonl(raw_path) if row.get("status") == "ok"} if raw_path.exists() else set()
    planned = batches(bundle_units)
    counts = {"batches": len(planned), "already_done": 0, "called": 0, "failed": 0}
    with raw_path.open("a", encoding="utf-8") as handle:
        for number, (key, article_id, rows, request) in enumerate(planned, 1):
            if key in done:
                counts["already_done"] += 1
                continue
            entry = {"key": key, "article_id": article_id, "rows": rows, "request_sha256": digest(request),
                     "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            try:
                answer = provider.structured(SYSTEM, request, SCHEMA, purpose="kb-extraction")
                entry |= {"status": "ok", "output": answer["output"], "usage": answer.get("usage"), "cost_usd": answer.get("cost_usd"),
                          "served_by": answer.get("model")}
                counts["called"] += 1
            except ProviderError as exc:
                entry |= {"status": "error", "code": exc.code}
                counts["failed"] += 1
            handle.write(canonical(entry) + "\n")
            handle.flush()
            if log:
                log(f"{number}/{len(planned)} {article_id}: {entry['status']}")
            if entry["status"] == "error" and entry["code"] == "budget_exhausted":
                break
    write_jsonl(output / "ledger.jsonl", getattr(provider, "ledger", []))  # Calls of this session, with hashes and usage.
    return counts


def _claims(units, raw_rows, run_id):
    by_version = {u["unit_version_id"]: u for u in units}
    claims, gaps = [], []
    latest = {}
    for row in raw_rows:  # The last answer per batch wins; a later success replaces an earlier error.
        if row["key"] not in latest or row.get("status") == "ok":
            latest[row["key"]] = row
    for row in sorted(latest.values(), key=lambda r: (by_version[r["rows"][0]["unit_version_id"]]["document_id"],
                                                      by_version[r["rows"][0]["unit_version_id"]]["source_start"], r["rows"][0]["start"])):
        if row.get("status") != "ok":
            gaps.extend({"unit_version_id": r["unit_version_id"], "start": r["start"], "end": r["end"], "reason": f"call_failed:{row.get('code')}"} for r in row["rows"])
            continue
        answers = {}
        for item in row["output"].get("results", []):
            if isinstance(item, dict) and isinstance(item.get("sentence"), str) and isinstance(item.get("norms"), list):
                answers.setdefault(item["sentence"], item["norms"])
        for index, target in enumerate(row["rows"], 1):
            unit = by_version[target["unit_version_id"]]
            norms = answers.get(f"S{index}")
            if norms is None:
                gaps.append({"unit_version_id": target["unit_version_id"], "start": target["start"], "end": target["end"], "reason": "missing_answer"})
                continue
            for number, norm in enumerate(norms[:MAX_NORMS_PER_SENTENCE]):
                norm = norm if isinstance(norm, dict) else {}
                claim_id = "kb:" + digest(canonical([row["key"], index, number]))[:16]
                claims.append({
                    "claim_id": claim_id, "kb_version": KB_VERSION, "document_id": unit["document_id"], "unit_id": unit["unit_id"],
                    "unit_version_id": unit["unit_version_id"],
                    "sentence": {"start": unit["source_start"] + target["start"], "end": unit["source_start"] + target["end"]},
                    "modality": norm.get("modality"), "modality_cue": norm.get("modality_cue"),
                    "slots": {name: norm.get(name) for name in LLM_SLOTS},
                    "extraction": {"run_id": run_id, "batch_key": row["key"], "sentence_index": index, "norm_index": number,
                                   "served_by": row.get("served_by"), "prompt": PROMPT_RUN},
                })
    return claims, gaps


def materialize(bundle_units, output):
    """Rebuild dk3.jsonl, validation.jsonl, dk4.jsonl and report.json from raw.jsonl (offline, deterministic)."""
    output = Path(output)
    raw_rows = read_jsonl(output / "raw.jsonl")
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    claims, gaps = _claims(bundle_units, raw_rows, manifest["run_id"])
    results = validate(claims, bundle_units)
    accepted = {r["claim_id"]: r for r in results if r["decision"] == "accepted"}
    dk4 = [claim | {"evidence": accepted[claim["claim_id"]]["evidence"], "validation": VALIDATOR_VERSION}
           for claim in claims if claim["claim_id"] in accepted]
    write_jsonl(output / "dk3.jsonl", claims)
    write_jsonl(output / "validation.jsonl", results)
    write_jsonl(output / "dk4.jsonl", dk4)
    write_jsonl(output / "gaps.jsonl", gaps)
    reasons = {}
    for result in results:
        for reason in result["reasons"]:
            code = reason.split(":", 1)[0]
            reasons[code] = reasons.get(code, 0) + 1
    check_counts = {name: {} for name in results[0]["checks"]} if results else {}
    for result in results:
        for name, value in result["checks"].items():
            check_counts[name][value] = check_counts[name].get(value, 0) + 1
    ok = [row for row in raw_rows if row.get("status") == "ok"]
    report = {"run_version": RUN_VERSION, "kb_version": KB_VERSION, "validator_version": VALIDATOR_VERSION,
              "batches_ok": len({r["key"] for r in ok}), "batch_errors": sum(1 for r in raw_rows if r.get("status") != "ok"),
              "sentences_without_answer": len(gaps), "dk3_claims": len(claims), "dk4_claims": len(dk4),
              "rejected": len(claims) - len(dk4), "checks": check_counts, "reasons": dict(sorted(reasons.items())),
              "cost_usd": round(sum(r.get("cost_usd") or 0 for r in ok), 4),
              "dk3_sha256": digest("".join(canonical(c) + "\n" for c in claims)), "dk4_sha256": digest("".join(canonical(c) + "\n" for c in dk4))}
    write_json(output / "report.json", report)
    return report


def start(bundle, output, model, effort):
    """Write the run manifest of a new run directory (or check it matches when resuming)."""
    output = Path(output)
    bundle = Path(bundle)
    units_sha = digest((bundle / "units.jsonl").read_bytes())
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (manifest["units_sha256"], manifest["model"], manifest["effort"]) != (units_sha, model, effort):
            raise ValueError("this run directory belongs to another bundle, model or effort; use a new directory")
        return manifest
    if output.exists() and any(output.iterdir()):
        raise ValueError("output must be empty or an earlier run of the same bundle")
    manifest = {"run_version": RUN_VERSION, "run_id": f"kb-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "bundle": bundle.as_posix(), "units_sha256": units_sha,
                "model": model, "effort": effort, "prompt": PROMPT_RUN, "system_sha256": digest(SYSTEM),
                "schema_sha256": digest(canonical(SCHEMA)),
                "limitations": ["Model answers are not reproducible by re-running; raw.jsonl is the record",
                                "Only norms (obligation, prohibition, entitlement, permission) are extracted; definitions without a modal cue are left out",
                                "Accepted means passing the automatic validator named in report.json, not a legally verified norm"]}
    write_json(manifest_path, manifest)
    return manifest
