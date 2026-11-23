"""Model-written retrieval keys (`kb-model-keys-v1`, the model part of `kb-keys-v2`; plan 22/11/2026 section 4.2 step 2).

For every leaf unit with claims in a knowledge-base run (in practice a derived run: `claims-inherit-v1` plus
`kb-validator-v4`), one structured model call per batch (`prompts/kb-keys-v1.md`) writes 2-3 short questions the unit
answers, in the everyday wording of a person telling their situation. The model reads the unit's verbatim text, the
verbatim lead-in of its parent and the unit's DK3 claims (modality and slots); the questions are retrieval keys only:
`retrieval_run` appends them to the index text of the unit's DK3/DK4 record (`indexing.kb_keys`, `kb-keys-v2`), never
to what the generator reads, never as evidence and never shown as law.

Batches group the units of one Article (at most `batch_size` units and `MAX_BATCH_CHARS` characters of unit text);
the answer schema of a batch constrains `unit_id` to the batch's own units. As in `kb_run`, every answer is appended to
`raw.jsonl` as soon as it arrives, keyed by the hash of the request, so an interrupted run resumes without paying
twice; failed calls are recorded, never dropped and never retried in the same session. `materialize` turns
`raw.jsonl` into `keys.jsonl` (one row per unit with keys) and `gaps.jsonl` (units without keys, with the reason),
offline and deterministically; deterministic checks drop a key that cites an Article or Clause number or a document
number, is not one short question, or repeats another key of the unit. `reuse` copies the answered batches of an
earlier keys run with the same model, prompt and inputs (a pilot); batches are whole Articles, so a later full run
pays only for the Articles the pilot did not cover.

Scope: `--all` (every leaf unit with claims) or the units of the Articles touched by question sets' gold units or by
retrieval runs' top-N records, so a pilot covers only the Articles the dev hard sets reach. `plan` (also `--dry-run`)
writes the units, batches, exact prompts and character counts without calling anything.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time

from legal_ai.common.io import canonical, digest, read_jsonl, write_json, write_jsonl
from legal_ai.extraction.norms import leaf_units
from legal_ai.indexing.records import MODALITY_LABELS, SLOT_LABELS
from legal_ai.providers.pilot import ProviderError

RUN_VERSION = "kb-keys-gen-run-v1"
MODEL_KEYS_VERSION = "kb-model-keys-v1"
PROMPTS = Path(__file__).resolve().parents[3] / "prompts"
PROMPT = "kb-keys-v1.md"
DEFAULT_BATCH_SIZE = 8
MAX_BATCH_CHARS = 8000  # Unit text plus lead-in per batch, so one long Article never makes one huge request.
MIN_KEYS, MAX_KEYS = 2, 3
MAX_KEY_CHARS = 250
MAX_KEY_WORDS = 40  # The prompt asks for about 25; anything far longer is not a short question.
DEFAULT_TOP_N = 30
STOP_CODES = ("budget_exhausted", "quota_exhausted", "rate_limited")  # Further calls would only fail too.
CITATION = re.compile(r"(?<!\w)(?:điều|khoản)\s+\d+|\d+/\d{4}/[a-zđ]", re.IGNORECASE)


def system_prompt(prompt=PROMPT):
    return (PROMPTS / prompt).read_text(encoding="utf-8")


def schema(unit_ids):
    """The answer schema of one batch: `unit_id` limited to the batch's own units, 2-3 questions each (a unit
    answered twice keeps its first answer in `materialize`)."""
    return {"type": "object", "additionalProperties": False, "required": ["units"], "properties": {"units": {
        "type": "array", "minItems": 1, "maxItems": len(unit_ids), "items": {
            "type": "object", "additionalProperties": False, "required": ["unit_id", "questions"], "properties": {
                "unit_id": {"type": "string", "enum": list(unit_ids)},
                "questions": {"type": "array", "minItems": MIN_KEYS, "maxItems": MAX_KEYS,
                              "items": {"type": "string", "minLength": 5, "maxLength": MAX_KEY_CHARS}}}}}}}


SCHEMA_TEMPLATE_SHA256 = digest(canonical(schema(["<unit_id>"])))


def article_of(unit, by_id):
    """The Article holding `unit` (itself if it is one), or None for units above Article level."""
    current = unit
    while current is not None and current["unit_type"] != "article":
        current = by_id.get(current["parent_id"]) if current["parent_id"] else None
    return current


def group_id(unit, by_id):
    """The batching and scope group of a leaf unit: its Article, or the unit itself when it lies above Article level."""
    article = article_of(unit, by_id)
    return (article or unit)["unit_id"]


def load_kb(kb_run, units_path):
    """DK3 claims and hashes of a knowledge-base run, checked against the bundle's units."""
    folder = Path(kb_run)
    manifest_bytes = (folder / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("units_sha256") != digest(Path(units_path).read_bytes()):
        raise ValueError("the knowledge-base run was extracted from another corpus bundle")
    dk3_bytes = (folder / "dk3.jsonl").read_bytes()
    info = {"path": folder.as_posix(), "manifest_sha256": digest(manifest_bytes), "dk3_sha256": digest(dk3_bytes),
            "dk4_sha256": digest((folder / "dk4.jsonl").read_bytes()) if (folder / "dk4.jsonl").exists() else None,
            "model": manifest.get("model"), "derivation": manifest.get("derivation")}
    return read_jsonl(folder / "dk3.jsonl"), info


def bundle_info(bundle):
    bundle = Path(bundle)
    units_sha, documents_sha = digest((bundle / "units.jsonl").read_bytes()), digest((bundle / "documents.jsonl").read_bytes())
    return {"path": bundle.as_posix(), "units_sha256": units_sha, "documents_sha256": documents_sha,
            "bundle_sha256": digest(canonical({"documents": documents_sha, "units": units_sha}))}


def claims_by_unit(units, claims):
    """{leaf unit_id: [claims in sentence order]}; a claim on an unknown or non-leaf unit is an error."""
    leaves = {u["unit_id"] for u in leaf_units(units)}
    grouped = {}
    for claim in claims:
        if claim.get("unit_id") not in leaves:
            raise ValueError(f"claim on an unknown or non-leaf unit: {claim.get('claim_id')}")
        grouped.setdefault(claim["unit_id"], []).append(claim)
    return {unit_id: sorted(rows, key=lambda c: (c["sentence"]["start"], c["claim_id"])) for unit_id, rows in grouped.items()}


def _touched(path, units_sha, top_n, split):
    """(kind, unit IDs, source record) of one `--units-from` input: a retrieval run directory or a question file."""
    path = Path(path)
    if path.is_dir():
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        if manifest["inputs"]["units"]["sha256"] != units_sha:
            raise ValueError(f"{path.as_posix()} ranked another corpus bundle")
        rows = [r for r in read_jsonl(path / "predictions.jsonl") if split is None or r.get("split") == split]
        ids = [unit_id for r in rows for record in r["ranked"][:top_n] for unit_id in record["unit_ids"]]
        return "retrieval_run", ids, {"path": path.as_posix(), "kind": "retrieval_run", "top_n": top_n, "questions": len(rows),
                                     "sha256": digest((path / "predictions.jsonl").read_bytes())}
    questions = [q for q in json.loads(path.read_text(encoding="utf-8"))["questions"] if split is None or q.get("split") == split]
    ids = [unit_id for q in questions for unit_id in q.get("relevant_unit_ids") or []]
    return "question_set", ids, {"path": path.as_posix(), "kind": "question_set", "questions": len(questions), "sha256": digest(path.read_bytes())}


def scope(units, grouped, bundle, sources=None, top_n=DEFAULT_TOP_N, split=None):
    """(unit IDs in document order, scope record). Without `sources`: every leaf unit with claims. With `sources`:
    the leaf units with claims of every Article that holds a gold unit of the question files or a top-N record of the
    retrieval runs (questions of `split` only, when given)."""
    by_id = {u["unit_id"]: u for u in units}
    order = {u["unit_id"]: (u["document_id"], u["source_start"]) for u in units}
    candidates = sorted(grouped, key=order.__getitem__)
    if not sources:
        return candidates, {"mode": "all", "units": len(candidates)}
    units_sha = digest((Path(bundle) / "units.jsonl").read_bytes())
    articles, records, above = set(), [], 0
    for path in sources:
        _, ids, record = _touched(path, units_sha, top_n, split)
        unknown = sorted({i for i in ids if i not in by_id})
        if unknown:
            raise ValueError(f"{Path(path).as_posix()} names units outside the bundle: {unknown[:3]}")
        found = [article_of(by_id[i], by_id) for i in dict.fromkeys(ids)]
        above += sum(a is None for a in found)
        articles |= {a["unit_id"] for a in found if a is not None}
        records.append(record | {"units_named": len(set(ids))})
    chosen = [u for u in candidates if group_id(by_id[u], by_id) in articles]
    return chosen, {"mode": "articles_touched", "split": split, "top_n": top_n, "sources": records, "articles": len(articles),
                    "sources_above_article_level": above, "units": len(chosen)}


def _norm(claim):
    slots = claim.get("slots") if isinstance(claim.get("slots"), dict) else {}
    entry = {"Tính quy phạm": MODALITY_LABELS.get(claim.get("modality"), str(claim.get("modality")))}
    for name, label in SLOT_LABELS.items():
        value = slots.get(name)
        if isinstance(value, str) and value.strip():
            entry[label] = value.strip()
    return entry


def unit_entry(unit, by_id, claims):
    """What the model reads about one unit: ID, the verbatim lead-in of its parent (an Article's lead-in without the
    heading, which the request gives once), its verbatim text and its distinct norms."""
    entry = {"unit_id": unit["unit_id"]}
    parent = by_id.get(unit["parent_id"]) if unit["parent_id"] else None
    if parent is not None:
        lead = parent["text"].split("\n", 1)[1] if parent["unit_type"] == "article" and "\n" in parent["text"] else ("" if parent["unit_type"] == "article" else parent["text"])
        if lead.strip():
            entry["context"] = lead.strip()
    entry["text"] = unit["text"].strip()
    norms = []
    for claim in claims:
        norm = _norm(claim)
        if norm not in norms:
            norms.append(norm)
    entry["norms"] = norms
    return entry


def batches(units, documents, grouped, unit_ids, batch_size=DEFAULT_BATCH_SIZE, prompt=PROMPT):
    """[{key, article_id, units: [{unit_id, claim_ids}], request, schema}] in document order; the key is the hash of
    the system prompt, request and schema, so a resumed run skips exactly the batches already answered."""
    if type(batch_size) is not int or batch_size < 1:
        raise ValueError("batch size must be a positive integer")
    by_id = {u["unit_id"]: u for u in units}
    titles = {d["document_id"]: d.get("title") for d in documents}
    system = system_prompt(prompt)
    groups = {}
    for unit_id in unit_ids:
        groups.setdefault(group_id(by_id[unit_id], by_id), []).append(unit_id)
    planned = []
    for article_id, members in groups.items():
        chunks, current, size = [], [], 0
        for unit_id in members:
            unit = by_id[unit_id]
            cost = len(unit["text"])
            if current and (len(current) >= batch_size or size + cost > MAX_BATCH_CHARS):
                chunks.append(current)
                current, size = [], 0
            current.append(unit_id)
            size += cost
        if current:
            chunks.append(current)
        article = by_id[article_id]
        for chunk in chunks:
            payload = {"document": titles.get(article["document_id"]), "article_heading": article["text"].splitlines()[0],
                       "units": [unit_entry(by_id[u], by_id, grouped[u]) for u in chunk]}
            request = json.dumps(payload, ensure_ascii=False)
            answer_schema = schema(chunk)
            planned.append({"key": digest(canonical({"system": system, "request": request, "schema": answer_schema})), "article_id": article_id,
                            "units": [{"unit_id": u, "claim_ids": [c["claim_id"] for c in grouped[u]]} for u in chunk],
                            "request": request, "schema": answer_schema})
    return planned


def plan(bundle, kb_run, *, sources=None, top_n=DEFAULT_TOP_N, split=None, batch_size=DEFAULT_BATCH_SIZE, prompt=PROMPT):
    """Everything a run needs, without any call: the bundle and KB hashes, the scope, the batches and the prompts."""
    bundle = Path(bundle)
    units, documents = read_jsonl(bundle / "units.jsonl"), read_jsonl(bundle / "documents.jsonl")
    claims, kb = load_kb(kb_run, bundle / "units.jsonl")
    grouped = claims_by_unit(units, claims)
    unit_ids, scope_record = scope(units, grouped, bundle, sources, top_n, split)
    planned = batches(units, documents, grouped, unit_ids, batch_size, prompt)
    system = system_prompt(prompt)
    chosen = set(unit_ids)
    texts = [u["text"] for u in units if u["unit_id"] in chosen]
    words = sum(len(t.split()) for t in texts)
    summary = {"units": len(unit_ids), "chars_per_word": round(sum(len(t) for t in texts) / words, 3) if words else None, "claims": sum(len(grouped[u]) for u in unit_ids), "batches": len(planned),
               "system_characters": len(system), "request_characters": sum(len(b["request"]) for b in planned),
               "schema_characters": sum(len(canonical(b["schema"])) for b in planned)}
    head = {"run_version": RUN_VERSION, "model_keys_version": MODEL_KEYS_VERSION, "bundle": bundle_info(bundle), "kb_run": kb,
            "prompt": {"file": prompt, "sha256": digest(system)}, "schema_template_sha256": SCHEMA_TEMPLATE_SHA256,
            "batch_size": batch_size, "max_batch_characters": MAX_BATCH_CHARS, "scope": scope_record,
            "plan_sha256": digest(canonical([b["key"] for b in planned]))}
    return head, summary, planned, system


def write_plan(output, head, summary, planned, system, estimate=None):
    """`plan.json`, the exact system prompt (`system.md`) and every request with its schema (`requests.jsonl`)."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "system.md").write_text(system, encoding="utf-8")
    write_jsonl(output / "requests.jsonl", [{"key": b["key"], "article_id": b["article_id"], "units": b["units"], "request": b["request"],
                                             "schema": b["schema"]} for b in planned])
    body = head | {"summary": summary, "batches": [{"key": b["key"], "article_id": b["article_id"], "unit_ids": [u["unit_id"] for u in b["units"]],
                                                    "request_characters": len(b["request"])} for b in planned]}
    if estimate is not None:
        body["estimate"] = estimate
    write_json(output / "plan.json", body)
    return body


def start(output, head, model, effort, provider="claude-code"):
    """Write the manifest of a new run directory, or check that a resumed run has the same inputs and plan."""
    output = Path(output)
    fixed = head | {"provider": provider, "model": model, "effort": effort}
    path = output / "manifest.json"
    if path.exists():
        earlier = json.loads(path.read_text(encoding="utf-8"))
        if {k: v for k, v in earlier.items() if k not in ("created_at", "usage", "limitations")} != fixed:
            raise ValueError("this run directory belongs to another bundle, knowledge base, scope, prompt or model; use a new directory")
        return earlier
    if output.exists() and any(output.iterdir()):
        raise ValueError("output must be a new, empty directory or an earlier run with the same inputs")
    manifest = fixed | {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "usage": None,
                        "limitations": ["Model answers are not reproducible by re-running; raw.jsonl is the record",
                                        "The keys are retrieval aids written by a model from the unit text and its DK3 claims: never evidence, never shown to the generator, not legal content",
                                        "Keys are per unit; DK4 keeps a unit's keys while at least one of its claims passed validation"]}
    write_json(path, manifest)
    return manifest


def reuse(planned, output, sources):
    """Copy into `output/raw.jsonl` the answered batches of earlier keys runs (`sources`) that this plan holds too,
    marked `reused_from`, so a full run after a pilot pays only for the new batches. A batch key hashes the system
    prompt, request and schema; the earlier run must also have the same model, effort and knowledge base. Returns the
    number of batches copied."""
    output = Path(output)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    raw_path = output / "raw.jsonl"
    done = {row["key"] for row in read_jsonl(raw_path) if row.get("status") == "ok"} if raw_path.exists() else set()
    rows = [row for row in reusable(planned, sources, manifest) if row["key"] not in done]
    with raw_path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(canonical(row) + "\n")
    return len(rows)


def _reuse_identity(manifest):
    """What must match for answers to be reused: provider, model, effort, prompt, schema shape and the hashes (not
    the paths) of the bundle and the knowledge base."""
    kb, bundle = manifest.get("kb_run") or {}, manifest.get("bundle") or {}
    return (manifest.get("provider"), manifest.get("model"), manifest.get("effort"), manifest.get("prompt"), manifest.get("schema_template_sha256"),
            bundle.get("bundle_sha256"), kb.get("manifest_sha256"), kb.get("dk3_sha256"))


def reusable(planned, sources, expected):
    """The answered rows of earlier keys runs whose batch key this plan holds (first answer per key wins), each marked
    `reused_from`; raises if an earlier run differs from `expected` in model, effort, prompt, knowledge base or bundle."""
    wanted = {batch["key"] for batch in planned}
    found = {}
    for source in sources or []:
        earlier = json.loads((Path(source) / "manifest.json").read_text(encoding="utf-8"))
        if _reuse_identity(earlier) != _reuse_identity(expected):
            raise ValueError(f"{Path(source).as_posix()} used another model, effort, prompt, knowledge base or bundle; its keys cannot be reused")
        for row in read_jsonl(Path(source) / "raw.jsonl"):
            if row.get("status") == "ok" and row["key"] in wanted and row["key"] not in found:
                found[row["key"]] = {k: v for k, v in row.items() if k != "reused_from"} | {"reused_from": row.get("reused_from") or Path(source).as_posix()}
    return list(found.values())


def generate(planned, system, provider, output, *, log=None):
    """Call the model for every batch not yet answered in `output/raw.jsonl`. Never retries a failed call; stops at
    the first budget or quota error, since every further call would fail the same way."""
    output = Path(output)
    raw_path = output / "raw.jsonl"
    done = {row["key"] for row in read_jsonl(raw_path) if row.get("status") == "ok"} if raw_path.exists() else set()
    counts = {"batches": len(planned), "already_done": 0, "called": 0, "failed": 0}
    with raw_path.open("a", encoding="utf-8") as handle:
        for number, batch in enumerate(planned, 1):
            if batch["key"] in done:
                counts["already_done"] += 1
                continue
            entry = {"key": batch["key"], "article_id": batch["article_id"], "units": batch["units"], "request_sha256": digest(batch["request"]),
                     "schema_sha256": digest(canonical(batch["schema"])), "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            started = time.monotonic()
            try:
                answer = provider.structured(system, batch["request"], batch["schema"], purpose="kb-keys")
                entry |= {"status": "ok", "output": answer["output"], "usage": answer.get("usage"), "cost_usd": answer.get("cost_usd"),
                          "served_by": answer.get("model")}
                counts["called"] += 1
            except ProviderError as exc:
                entry |= {"status": "error", "code": exc.code, "detail": getattr(exc, "detail", "")[:300]}
                counts["failed"] += 1
            entry["duration_ms"] = round((time.monotonic() - started) * 1000)
            handle.write(canonical(entry) + "\n")
            handle.flush()
            if log:
                log(f"{number}/{len(planned)} {batch['article_id']}: {entry['status']}")
            if entry["status"] == "error" and entry["code"] in STOP_CODES:
                break
    ledger = output / "ledger.jsonl"  # Calls of every session, with hashes, usage and cost.
    earlier = read_jsonl(ledger) if ledger.exists() else []
    write_jsonl(ledger, earlier + list(getattr(provider, "ledger", [])))
    return counts


def clean_keys(values):
    """(kept keys, [(key, reason)] dropped): whitespace collapsed, one short question each, no citation, no repeat."""
    kept, dropped = [], []
    for value in values if isinstance(values, list) else []:
        text = " ".join(value.split()) if isinstance(value, str) else ""
        reason = None
        if not text:
            reason = "empty"
        elif CITATION.search(text):
            reason = "citation"
        elif len(text) > MAX_KEY_CHARS or len(text.split()) > MAX_KEY_WORDS:
            reason = "too_long"
        elif text.casefold() in {k.casefold() for k in kept}:
            reason = "duplicate"
        elif len(kept) >= MAX_KEYS:
            reason = "too_many"
        if reason:
            dropped.append({"key": text, "reason": reason})
        else:
            kept.append(text)
    return kept, dropped


def materialize(output):
    """Rebuild keys.jsonl, gaps.jsonl and the manifest's usage block from raw.jsonl (offline, deterministic)."""
    output = Path(output)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    planned = [json.loads(line) for line in (output / "requests.jsonl").read_text(encoding="utf-8").splitlines() if line]
    raw_rows = read_jsonl(output / "raw.jsonl") if (output / "raw.jsonl").exists() else []
    latest = {}
    for row in raw_rows:  # The last answer per batch wins; a later success replaces an earlier error.
        if row["key"] not in latest or row.get("status") == "ok":
            latest[row["key"]] = row
    keys, gaps, dropped_counts = [], [], {}
    for batch in planned:
        row = latest.get(batch["key"])
        if row is None or row.get("status") != "ok":
            if row is None:
                reason = "not_called"
            else:  # Lexora's own budget stop raises before anything is sent.
                reason = f"{'not_sent' if row.get('code') == 'budget_exhausted' else 'call_failed'}:{row.get('code')}"
            gaps.extend({"unit_id": u["unit_id"], "reason": reason} for u in batch["units"])
            continue
        answers = {}
        for item in row["output"].get("units", []) if isinstance(row["output"], dict) else []:
            if isinstance(item, dict) and isinstance(item.get("unit_id"), str):
                answers.setdefault(item["unit_id"], item.get("questions"))
        for unit in batch["units"]:
            if unit["unit_id"] not in answers:
                gaps.append({"unit_id": unit["unit_id"], "reason": "missing_answer"})
                continue
            kept, dropped = clean_keys(answers[unit["unit_id"]])
            for entry in dropped:
                dropped_counts[entry["reason"]] = dropped_counts.get(entry["reason"], 0) + 1
            if not kept:
                gaps.append({"unit_id": unit["unit_id"], "reason": "no_valid_key", "dropped": dropped})
                continue
            keys.append({"unit_id": unit["unit_id"], "claim_ids": unit["claim_ids"], "keys": kept, "model": row.get("served_by") or manifest["model"],
                         "prompt_sha256": manifest["prompt"]["sha256"], "batch_key": batch["key"],
                         "model_keys_version": MODEL_KEYS_VERSION, **({"dropped": dropped} if dropped else {})})
    write_jsonl(output / "keys.jsonl", keys)
    write_jsonl(output / "gaps.jsonl", gaps)
    ok = [r for r in latest.values() if r.get("status") == "ok"]
    paid = [r for r in raw_rows if r.get("status") == "ok" and "reused_from" not in r]  # Calls of this run, not copied answers.
    usage = {"batches_ok": len(ok), "batches_reused": sum(1 for r in ok if "reused_from" in r),
             "call_errors": sum(1 for r in raw_rows if r.get("status") != "ok"),
             "units_with_keys": len(keys), "units_without_keys": len(gaps), "keys": sum(len(r["keys"]) for r in keys),
             "dropped_keys": dict(sorted(dropped_counts.items())),
             "input_tokens": sum(input_tokens(r.get("usage")) for r in paid),
             "output_tokens": sum((r.get("usage") or {}).get("output_tokens") or 0 for r in paid),
             "cost_usd": round(sum(r.get("cost_usd") or 0 for r in paid), 4),
             "keys_sha256": digest((output / "keys.jsonl").read_bytes())}
    write_json(output / "manifest.json", manifest | {"usage": usage})
    return usage


def input_tokens(usage):
    """All input tokens of one Claude Code answer: uncached, written to and read from the prompt cache."""
    usage = usage or {}
    return sum(usage.get(name) or 0 for name in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))

