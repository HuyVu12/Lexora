"""Norm-field queries for the enumeration questions (`norm-query-v1`): DK3-q and DK4-q of the research plan (WP5).

An enumeration question ("Người sử dụng lao động có những nghĩa vụ gì khi thử việc?") asks for every rule that meets a
criterion, which a passage ranker does not gather. Three steps, all deterministic except the first:

1. `analyze`: one structured model call per question (`prompts/query-slots-v1.md`, run once and shared by every
   condition) returns the modality sought, the actor phrase, the slots an answer must have (deadlines, quantities...)
   and a topic query in statutory wording. DK1 and DK2 rank with the same topic query.
2. `matches`: a claim of the knowledge base passes when its modality is the one sought (or any), every required slot
   is filled, and its actor matches the question's actor after accent folding, through a fixed alias table
   (`configs/experiments/actor-aliases.json`, frozen before any run); no actor in the question matches every claim.
3. The retrieval run ranks the units by the topic query as DK2 does and keeps the units holding a passing claim, in
   that order. The generator reads `norm_records`: one structure line per claim of the unit with the verbatim action
   slot, grouped per Article; block IDs still point at the leaf unit so the citation gate works as before.

DK4-q is the same design over the validated claims (a subset of DK3's). Nothing here changes the validator.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import unicodedata

from legal_ai.common.io import canonical, digest, read_jsonl, write_json
from legal_ai.indexing.records import compact_claim, structural_records, token_spans, unit_path

QUERY_VERSION = "norm-query-v1"
RUN_VERSION = "query-slots-run-v1"
PROMPTS = Path(__file__).resolve().parents[3] / "prompts"
MODALITIES = ("obligation", "prohibition", "entitlement", "permission", "any")
REQUIRED = ("deadlines", "quantities", "conditions", "exceptions", "beneficiary", "outcome")
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["modality", "actor", "required_slots", "topic_query"], "properties": {
    "modality": {"type": "string", "enum": list(MODALITIES)},
    "actor": {"type": ["string", "null"], "maxLength": 120},
    "required_slots": {"type": "array", "maxItems": 3, "items": {"type": "string", "enum": list(REQUIRED)}},
    "topic_query": {"type": "string", "minLength": 2, "maxLength": 200}}}


def fold(text):
    """Lower case, accents removed (đ -> d), spaces collapsed: the form actors are compared in."""
    text = unicodedata.normalize("NFD", (text or "").casefold().replace("đ", "d"))
    return " ".join("".join(c for c in text if unicodedata.category(c) != "Mn").split())


def clean(output):
    """The analysis of one model answer, or ValueError when it does not follow the schema."""
    if not isinstance(output, dict) or output.get("modality") not in MODALITIES or not isinstance(output.get("topic_query"), str):
        raise ValueError("invalid_analysis")
    topic = output["topic_query"].strip()[:200]
    if not topic:
        raise ValueError("empty_topic_query")
    actor = output.get("actor") if isinstance(output.get("actor"), str) and output["actor"].strip() else None
    slots = [s for s in dict.fromkeys(output.get("required_slots") or []) if s in REQUIRED][:3]
    return {"modality": output["modality"], "actor": actor.strip()[:120] if actor else None, "required_slots": slots, "topic_query": topic}


def analyze(questions_path, provider, output, prompt="query-slots-v1.md", log=None):
    """One analysis per question into `output/query_slots.jsonl`; resumes like the decomposition run."""
    from legal_ai.providers.pilot import ProviderError
    output = Path(output)
    system = (PROMPTS / prompt).read_text(encoding="utf-8")
    questions = json.loads(Path(questions_path).read_text(encoding="utf-8"))["questions"]
    manifest = {"run_version": RUN_VERSION, "query_version": QUERY_VERSION, "questions_sha256": digest(Path(questions_path).read_bytes()),
                "provider": getattr(provider, "provider", "claude-code"), "model": provider.model, "effort": getattr(provider, "effort", None),
                "prompt": prompt, "system_sha256": digest(system), "schema_sha256": digest(canonical(SCHEMA))}
    path = output / "manifest.json"
    if path.exists():
        earlier = json.loads(path.read_text(encoding="utf-8"))
        if {k: v for k, v in earlier.items() if k != "created_at"} != manifest:
            raise ValueError("this analysis run used other inputs, model or settings; use a new directory")
    else:
        if output.exists() and any(output.iterdir()):
            raise ValueError("output must be empty or an earlier analysis run with the same inputs")
        write_json(path, manifest | {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    rows_path = output / "query_slots.jsonl"
    done = {r["question_id"] for r in read_jsonl(rows_path) if r.get("error") is None} if rows_path.exists() else set()
    counts = {"questions": len(questions), "already_done": 0, "analyzed": 0, "failed": 0}
    with rows_path.open("a", encoding="utf-8") as handle:
        for number, question in enumerate(questions, 1):
            if question["question_id"] in done:
                counts["already_done"] += 1
                continue
            row = {"question_id": question["question_id"]}
            try:
                answer = provider.structured(system, json.dumps({"question": question["question"]}, ensure_ascii=False), SCHEMA, purpose="query_slots")
                row |= {"analysis": clean(answer["output"]), "served_by": answer.get("model"), "error": None}
                counts["analyzed"] += 1
            except ProviderError as exc:
                row |= {"error": exc.code}
                counts["failed"] += 1
            except ValueError as exc:
                row |= {"error": str(exc)}
                counts["failed"] += 1
            handle.write(canonical(row) + "\n")
            handle.flush()
            if log:
                log(f"{number}/{len(questions)} {question['question_id']}: {row.get('analysis', {}).get('modality') or row['error']}")
            if row.get("error") in ("budget_exhausted", "quota_exhausted"):
                break
    return counts


def load(folder, questions_path=None):
    """{question_id: analysis} of a finished analysis run, checked against the question file."""
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if questions_path is not None and manifest["questions_sha256"] != digest(Path(questions_path).read_bytes()):
        raise ValueError("the analysis run was made from another question file")
    return {r["question_id"]: r["analysis"] for r in read_jsonl(folder / "query_slots.jsonl") if r.get("error") is None}, manifest


def load_aliases(path):
    """{canonical name: [folded aliases]} from the frozen alias table; every canonical name is its own alias."""
    table = json.loads(Path(path).read_text(encoding="utf-8"))["actors"]
    return {name: sorted({fold(name), *(fold(a) for a in aliases)}, key=len, reverse=True) for name, aliases in table.items()}


def actor_keys(text, aliases):
    """Canonical actors named in a phrase: every canonical whose alias occurs in it as whole words."""
    folded = f" {fold(text)} "
    return {name for name, forms in aliases.items() if any(f" {form} " in folded for form in forms)}


def actor_matches(question_actor, claim_actor, aliases):
    if not question_actor:
        return True
    if not claim_actor:
        return False
    wanted, have = actor_keys(question_actor, aliases), actor_keys(claim_actor, aliases)
    if wanted:
        return bool(wanted & have)
    return fold(question_actor) in fold(claim_actor)  # An actor outside the table: plain folded containment.


def matches(claim, analysis, aliases):
    slots = claim.get("slots") if isinstance(claim.get("slots"), dict) else {}
    if analysis["modality"] != "any" and claim.get("modality") != analysis["modality"]:
        return False
    if any(not (isinstance(slots.get(s), str) and slots[s].strip()) for s in analysis["required_slots"]):
        return False
    return actor_matches(analysis.get("actor"), slots.get("actor"), aliases)


ACTION_WORDS = 24


def norm_line(claim):
    """One line per claim: the compact structure and the verbatim action slot (cut to a few dozen words)."""
    slots = claim.get("slots") if isinstance(claim.get("slots"), dict) else {}
    action = slots.get("action") if isinstance(slots.get("action"), str) else ""
    words = action.split()
    quoted = " ".join(words[:ACTION_WORDS]) + ("…" if len(words) > ACTION_WORDS else "")
    return compact_claim(claim) + (f" · Hành vi: «{quoted}»" if quoted else "")


def norm_records(condition, documents, units, texts, claims, max_tokens=384):
    """DK3-q/DK4-q records: one per leaf unit that holds at least one claim. `index_text` is the unit's DK2 index text
    (what the topic query ranks); the generator reads `generator_text` (title, path, then one `norm_line` per claim),
    and `pack_layout` splits it into the Article header and the unit's own lines for article packing."""
    by_id = {u["unit_id"]: u for u in units}
    titles = {d["document_id"]: d["title"] for d in documents}
    attached = {}
    for claim in claims:
        attached.setdefault(claim.get("unit_id"), []).append(claim)
    records = []
    for row in structural_records(documents, units, texts, max_tokens):
        unit_id = row["unit_ids"][0]
        mine = sorted((c for c in attached.get(unit_id, []) if row["source_start"] <= c["sentence"]["start"] < row["source_end"]),
                      key=lambda c: (c["sentence"]["start"], c["claim_id"]))
        if not mine:
            continue
        leaf = by_id[unit_id]
        path, chain = unit_path(leaf, by_id)
        lines = [f"[Quy phạm {n}] {norm_line(c)}" for n, c in enumerate(mine, 1)]
        labels = path.split(" > ")
        cut = next((n + 1 for n, u in enumerate(chain + [leaf]) if u["unit_type"] == "article"), len(labels))
        header = f"{titles[row['document_id']]}\n{' > '.join(labels[:cut])}"
        own = " > ".join(labels[cut:])
        body = (f"{own}\n" if own else "") + "\n".join(lines)
        article = next((u for u in chain + [leaf] if u["unit_type"] == "article"), leaf)
        records.append({**row, "condition": condition, "record_id": f"{condition.lower()}:{row['record_id'].split(':', 1)[1]}",
                        "generator_text": f"{header}\n{body}", "token_count": sum(len(token_spans(line)) for line in lines),
                        "claim_ids": [c["claim_id"] for c in mine], "claims": [{k: c.get(k) for k in ("claim_id", "modality", "slots")} for c in mine],
                        "pack_layout": {"group": [row["document_id"], article["unit_id"]], "header": header, "body": body}})
    return records


def filter_ranked(ranked, records, analysis, aliases):
    """The ranked (index, score) pairs whose record holds a claim passing the analysis, in rank order."""
    return [(i, s) for i, s in ranked if any(matches(c, analysis, aliases) for c in records[i]["claims"])]


def coverage(questions, claims):
    """Share of gold units of the enumeration questions that hold at least one knowledge-base claim (extraction
    coverage, the first number of the 19/11 gate), with the uncovered units listed."""
    with_claims = {c["unit_id"] for c in claims}
    gold = sorted({u for q in questions for u in q["relevant_unit_ids"]})
    covered = [u for u in gold if u in with_claims or any(w.startswith(u + "/") for w in with_claims)]
    return {"gold_units": len(gold), "covered": len(covered), "coverage": len(covered) / len(gold) if gold else None,
            "uncovered": [u for u in gold if u not in set(covered)]}
