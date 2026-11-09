"""Fairness preflight for a DK1-DK4 comparison (`preflight-v1`), run before any RQ3 number is reported.

Given the retrieval runs of the conditions (and optionally their answer runs), it checks that the conditions differ
only in their representation:

- same frozen corpus bundle (units and documents), same question file, same shared retrieval settings (method,
  tokenizer, BM25 parameters, fusion, embedding model and revision, top-k, recall cut-offs);
- each condition appears once, and DK1-DK4 are all present (a missing condition is a warning);
- index isolation: every record of a run belongs to its own condition, maps only to units of the bundle, and no
  record ID is shared across runs;
- DK3 and DK4 come from the same knowledge-base run and every DK4 claim is a DK3 claim;
- answer runs: one per retrieval run, the same model, effort, prompt, top-k, token budget and split;
- held-out: a run on held-out questions needs frozen shared and condition settings.

Each check is `pass`, `fail` or `warn` with details; the overall status is the worst of them.
"""

import json
from pathlib import Path

from legal_ai.common.io import canonical, digest, read_jsonl

PREFLIGHT_VERSION = "preflight-v1"
CONDITIONS = ("DK1", "DK2", "DK3", "DK4")
SHARED_KEYS = ("method", "tokenizer", "k1", "b", "rrf_c", "rrf_candidates", "recall_k")


def _load(folder):
    folder = Path(folder)
    return json.loads((folder / "manifest.json").read_text(encoding="utf-8"))


def _same(values):
    return len({json.dumps(v, sort_keys=True, ensure_ascii=False) for v in values}) <= 1


def check(retrieval_dirs, answer_dirs=()):
    checks = []
    add = lambda name, status, detail="": checks.append({"check": name, "status": status, "detail": detail})
    runs = [(Path(d), _load(d)) for d in retrieval_dirs]
    if not runs:
        raise ValueError("give at least one retrieval run")

    conditions = [m["condition"]["condition"] for _, m in runs]
    duplicates = sorted({c for c in conditions if conditions.count(c) > 1})
    add("one run per condition", "fail" if duplicates else "pass", f"duplicated: {duplicates}" if duplicates else ", ".join(conditions))
    missing = [c for c in CONDITIONS if c not in conditions]
    add("all four conditions present", "warn" if missing else "pass", f"missing: {missing}" if missing else "")

    for name, key in (("same corpus units", "units"), ("same corpus documents", "documents"), ("same question file", "questions")):
        values = [m["inputs"][key]["sha256"] for _, m in runs]
        add(name, "pass" if _same(values) else "fail", "" if _same(values) else dict(zip(conditions, values)))

    shared = [{k: m["retrieval"].get(k) for k in SHARED_KEYS} | {"top_k": m["shared"].get("top_k")} for _, m in runs]
    add("same retrieval settings", "pass" if _same(shared) else "fail", "" if _same(shared) else dict(zip(conditions, shared)))
    dense = [({k: (m.get("dense") or {}).get(k) for k in ("model", "revision", "weights_sha256", "max_seq_length")} if m.get("dense") else None) for _, m in runs]
    add("same embedding model", "pass" if _same(dense) else "fail", "" if _same(dense) else dict(zip(conditions, dense)))

    units = {u["unit_id"] for u in read_jsonl(Path(runs[0][1]["inputs"]["units"]["path"]))} if Path(runs[0][1]["inputs"]["units"]["path"]).exists() else None
    seen_ids, problems = {}, []
    for (folder, manifest), condition in zip(runs, conditions):
        for row in read_jsonl(folder / "records.jsonl"):
            if row["condition"] != condition:
                problems.append(f"{condition}: record {row['record_id']} is labelled {row['condition']}")
            if units is not None and any(u not in units for u in row["unit_ids"]):
                problems.append(f"{condition}: record {row['record_id']} maps outside the bundle")
            if row["record_id"] in seen_ids and seen_ids[row["record_id"]] != condition:
                problems.append(f"record {row['record_id']} is in {seen_ids[row['record_id']]} and {condition}")
            seen_ids[row["record_id"]] = condition
        if digest("".join(canonical(r) + "\n" for r in read_jsonl(folder / "records.jsonl"))) != manifest["records_sha256"]:
            problems.append(f"{condition}: records.jsonl does not match the hash in its manifest")
    add("index isolation", "fail" if problems else "pass", problems[:10])

    kb = {c: m["condition"].get("kb_run") for (_, m), c in zip(runs, conditions) if c in ("DK3", "DK4")}
    if len(kb) == 2:
        same_run = Path(kb["DK3"]).resolve() == Path(kb["DK4"]).resolve()
        add("DK3 and DK4 from one extraction run", "pass" if same_run else "fail", "" if same_run else kb)
        if same_run:
            dk3 = {c["claim_id"] for c in read_jsonl(Path(kb["DK3"]) / "dk3.jsonl")}
            dk4 = {c["claim_id"] for c in read_jsonl(Path(kb["DK4"]) / "dk4.jsonl")}
            extra = sorted(dk4 - dk3)
            add("DK4 is a subset of DK3", "fail" if extra else "pass", f"{len(extra)} DK4 claims not in DK3" if extra else f"{len(dk4)} of {len(dk3)} kept")
        # DK3 and DK4 may differ only in which claims survived validation.
        shape = {c: {k: m["condition"].get(k) for k in ("record", "max_tokens", "graph")} for (_, m), c in zip(runs, conditions) if c in ("DK3", "DK4")}
        add("DK3 and DK4 use the same record shape and graph", "pass" if _same(list(shape.values())) else "fail", "" if _same(list(shape.values())) else shape)

    held = []
    for (_, manifest), condition in zip(runs, conditions):
        frozen = manifest["shared"].get("status") == "frozen" and manifest["condition"].get("status") == "frozen"
        held.append((condition, frozen))
    report = {"preflight_version": PREFLIGHT_VERSION, "retrieval_runs": [str(d) for d, _ in runs], "checks": checks}

    if answer_dirs:
        answers = [(Path(d), _load(d)) for d in answer_dirs]
        by_retrieval = {Path(m["retrieval_run"]).resolve(): m for _, m in answers}
        unmatched = [str(d) for d, _ in runs if d.resolve() not in by_retrieval]
        add("one answer run per retrieval run", "fail" if unmatched or len(answers) != len(runs) else "pass",
            f"without answers: {unmatched}" if unmatched else "")
        keys = ("provider", "model", "effort", "system_sha256", "prompt", "top_k", "context_token_budget", "token_counter", "split", "questions_sha256")
        settings = [{k: m.get(k) for k in keys} for _, m in answers]
        add("same answer settings", "pass" if _same(settings) else "fail", "" if _same(settings) else [dict(s, run=str(d)) for (d, _), s in zip(answers, settings)])
        if any(m.get("split") == "held_out" for _, m in answers):
            unfrozen = [c for c, frozen in held if not frozen]
            add("held-out only with frozen settings", "fail" if unfrozen else "pass", f"not frozen: {unfrozen}" if unfrozen else "")
        report["answer_runs"] = [str(d) for d, _ in answers]

    report["status"] = "fail" if any(c["status"] == "fail" for c in checks) else ("warn" if any(c["status"] == "warn" for c in checks) else "pass")
    return report
