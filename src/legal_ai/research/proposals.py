"""Model proposals for question sets: label suggestions and question drafts, through a structured provider.

Candidates come from BM25 over the DK2 records (leaf units with their path and lead text) of the set's frozen
corpus version, so the model only ever sees exact statute text. The answer schema lists the allowed unit IDs
as an enum, and the store drops anything outside the corpus version anyway. Prompts are versioned files in
`prompts/`; their SHA-256 goes with every call. Proposals are suggestions for people to keep or change.
"""

from pathlib import Path
import threading

from legal_ai.common.io import digest
from legal_ai.indexing.records import structural_records
from legal_ai.providers.claude_code import ProviderError
from legal_ai.research.questions import QUESTION_TYPES, STATUSES
from legal_ai.retrieval.bm25 import BM25, tokens

PROMPTS = Path(__file__).resolve().parents[3] / "prompts"
LABEL_PROMPT, DRAFT_PROMPT = "question-label-v1.md", "question-draft-v1.md"
MAX_DRAFT_UNITS, MAX_DRAFTS = 40, 8
_cache, _cache_lock = {}, threading.Lock()


def prompt(name):
    text = (PROMPTS / name).read_text(encoding="utf-8")
    return text, {"prompt_file": name, "prompt_sha256": digest(text)}


def _records(corpora, version_id):
    """DK2 records of a frozen version and their BM25 index, built once per version (versions never change)."""
    with _cache_lock:
        if version_id not in _cache:
            documents, units, texts = corpora.bundle(version_id)
            records = structural_records(documents, units, texts)
            _cache[version_id] = (records, BM25([tokens(r["index_text"]) for r in records]), {u["unit_id"]: u for u in units})
        return _cache[version_id]


def _path(record):
    return record["index_text"].split("\n", 2)[1]


def candidates(corpora, version_id, question, k=8):
    """Up to `k` distinct leaf units for a question: unit ID, path and the exact text (split parts joined)."""
    records, index, _ = _records(corpora, version_id)
    found = {}
    for position, _score in index.rank(tokens(question)):
        record = records[position]
        unit_id = record["unit_ids"][0]
        if unit_id in found:
            continue
        found[unit_id] = {"unit_id": unit_id, "path": _path(record), "text": "".join(r["text"] for r in records if r["unit_ids"] == [unit_id])}
        if len(found) == k:
            break
    return list(found.values())


def _units_block(items):
    return "\n\n".join(f"[{c['unit_id']}] {c['path']}\n{c['text'].strip()}" for c in items)


def label_schema(unit_ids):
    units = {"type": "array", "items": {"type": "string", "enum": unit_ids}, "uniqueItems": True} if unit_ids else {"type": "array", "maxItems": 0}
    return {"type": "object", "additionalProperties": False, "required": ["question_type", "expected_status", "relevant_unit_ids", "rationale"],
            "properties": {"question_type": {"type": "string", "enum": list(QUESTION_TYPES)}, "expected_status": {"type": "string", "enum": list(STATUSES)},
                           "relevant_unit_ids": units, "rationale": {"type": "string", "maxLength": 600}}}


def propose_label(provider, store, set_id, question_id, k=8):
    """Ask the model for one question's labels; the proposal (or the failed call) is stored."""
    summary, question = store.summary(set_id), store.question(question_id)
    found = candidates(store.corpora, summary["corpus_version_id"], question["text"], k)
    system, meta = prompt(LABEL_PROMPT)
    body = f"Câu hỏi:\n{question['text']}\n\nĐơn vị ứng viên ({len(found)}):\n\n{_units_block(found) or '(không có ứng viên nào khớp từ khóa)'}"
    try:
        answer = provider.structured(system, body, label_schema([c["unit_id"] for c in found]), purpose="question-label")
    except ProviderError as exc:
        store.log_call(set_id, provider.ledger[-1] | meta | {"question_id": question_id} if provider.ledger else {"purpose": "question-label", "status": "error", "code": exc.code})
        raise
    record = {k: v for k, v in provider.ledger[-1].items() if k != "output"} | meta | {"question_id": question_id}
    call_id = store.log_call(set_id, record)
    output = answer["output"]
    return store.add_proposal(set_id, question_id, output, output.get("rationale", ""), [c["unit_id"] for c in found], record | {"call_id": call_id})


def draft_schema(unit_ids, count):
    return {"type": "object", "additionalProperties": False, "required": ["questions"],
            "properties": {"questions": {"type": "array", "minItems": 1, "maxItems": count, "items": {
                "type": "object", "additionalProperties": False, "required": ["text", "question_type", "relevant_unit_ids", "paraphrases", "rationale"],
                "properties": {"text": {"type": "string", "minLength": 5, "maxLength": 500},
                               "question_type": {"type": "string", "enum": ["lookup", "synthesis"]},
                               "relevant_unit_ids": {"type": "array", "minItems": 1, "items": {"type": "string", "enum": unit_ids}, "uniqueItems": True},
                               "paraphrases": {"type": "array", "maxItems": 2, "items": {"type": "string", "minLength": 5, "maxLength": 500}},
                               "rationale": {"type": "string", "maxLength": 600}}}}}}


def draft_questions(provider, store, set_id, unit_ids, count=4):
    """Ask the model for up to `count` questions answerable from the given units (Articles expand to their leaves)."""
    if not 1 <= count <= MAX_DRAFTS:
        raise ValueError(f"Số câu nháp mỗi lần từ 1 đến {MAX_DRAFTS}")
    summary = store.summary(set_id)
    records, _, units = _records(store.corpora, summary["corpus_version_id"])
    chosen = [u for u in unit_ids if u in units]
    if not chosen or len(chosen) != len(unit_ids):
        raise ValueError("Chọn các đơn vị có trong phiên bản corpus của bộ câu hỏi")
    leaves = []
    for record in records:
        leaf = record["unit_ids"][0]
        if any(leaf == u or leaf.startswith(u + "/") for u in chosen) and leaf not in {x["unit_id"] for x in leaves}:
            leaves.append({"unit_id": leaf, "path": _path(record), "text": "".join(r["text"] for r in records if r["unit_ids"] == [leaf])})
    if len(leaves) > MAX_DRAFT_UNITS:
        raise ValueError(f"Chọn ít đơn vị hơn: tối đa {MAX_DRAFT_UNITS} đơn vị lá mỗi lần")
    system, meta = prompt(DRAFT_PROMPT)
    ids = [x["unit_id"] for x in leaves]
    body = f"Số câu hỏi cần soạn: {count}\n\nĐơn vị văn bản ({len(leaves)}):\n\n{_units_block(leaves)}"
    try:
        answer = provider.structured(system, body, draft_schema(ids, count), purpose="question-draft")
    except ProviderError as exc:
        store.log_call(set_id, provider.ledger[-1] | meta if provider.ledger else {"purpose": "question-draft", "status": "error", "code": exc.code})
        raise
    record = {k: v for k, v in provider.ledger[-1].items() if k != "output"} | meta | {"unit_ids": chosen}
    call_id = store.log_call(set_id, record)
    drafts = [d | {"relevant_unit_ids": [u for u in d["relevant_unit_ids"] if u in ids]} for d in answer["output"]["questions"]]
    return store.save_drafts(set_id, call_id, ids, [d for d in drafts if d["relevant_unit_ids"]])
