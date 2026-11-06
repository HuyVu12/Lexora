"""Revision-bound chat over human-approved evidence only, offline by default."""

from collections import Counter
from datetime import datetime, timezone
import json
import math
import threading
import unicodedata
from uuid import uuid4

from legal_ai.common.io import canonical, digest
from legal_ai.providers.pilot import ProviderError
from legal_ai.retrieval.bm25 import tokens
from legal_ai.validation.evidence import check_evidence

# This is a conservative lexical relevance gate, not a legal entailment test.
STOP = set("tôi em mình bạn xin hỏi là thì mà và của cho với về được những các một có không phải gì nào bao nhiêu như thế nào trong theo hay hãy biết giúp đang cần ai người lao động sử dụng".split())
MAX_CONTEXT_CHARS = 10_000


def terms(text):
    # Search may ignore accents; source quotes and evidence identities never do.
    folded = "".join(c for c in unicodedata.normalize("NFD", text.casefold().replace("đ", "d")) if not unicodedata.combining(c))
    return tokens(folded)


STOP = set(terms(" ".join(STOP)))


def approved_passages(graph):
    content = {k: graph[k] for k in ("graph_version", "nodes", "edges", "references", "extraction_report")}
    if digest(canonical(content)) != graph["graph_hash"]:
        raise ValueError("graph_integrity_error")
    units = [n["payload"] for n in graph["nodes"] if n["kind"] == "LegalUnit"]
    evidence = {n["payload"]["evidence_id"]: n["payload"] for n in graph["nodes"] if n["kind"] == "Evidence"}
    documents = {n["payload"]["document_id"]: n["payload"] for n in graph["nodes"] if n["kind"] == "Document"}
    passages = []
    for node in graph["nodes"]:
        claim = node["payload"]
        if node["kind"] != "NormClaim" or claim.get("human_review", {}).get("decision") != "approved":
            continue
        # Never expand to the whole leaf: it may contain unparsed/rejected sentences.
        anchors = []
        for eid in claim["evidence_ids"]:
            anchor = evidence.get(eid)
            if anchor is None or check_evidence(anchor, units):
                raise ValueError("approved_evidence_integrity_error")
            if anchor["unit_version_id"] == claim["source_unit_version_ids"][0]:
                anchors.append(anchor)
        if not anchors:
            raise ValueError("approved_claim_missing_primary_evidence")
        primary = max(anchors, key=lambda a: len(a["quote"]))
        scope = [evidence[eid] for eid in claim.get("slots", {}).get("scope", {}).get("evidence_ids", [])]
        document = documents[primary["document_id"]]
        passages.append({"claim_id": node["id"], "evidence": primary, "scope": scope,
                         "title": document["title"], "source_url": document["source_url"],
                         "source_sha256": document["source_sha256"], "synthetic": document["synthetic"],
                         "human_review": claim["human_review"]})
    return passages


def retrieve(passages, question, top_k=3):
    query = set(terms(question)) - STOP
    if not query:
        return []
    docs = [Counter(terms(p["evidence"]["quote"] + " " + " ".join(s["quote"] for s in p["scope"]))) for p in passages]
    if not docs:
        return []
    average = sum(sum(d.values()) for d in docs) / len(docs)
    ranked = []
    for passage, counts in zip(passages, docs):
        matched = query & counts.keys()
        if len(matched) < min(2, len(query)):
            continue
        score = 0.0
        for word in matched:
            frequency = counts[word]
            df = sum(word in d for d in docs)
            score += math.log(1 + (len(docs) - df + .5) / (df + .5)) * frequency * 2.5 / (frequency + 1.5 * (.25 + .75 * sum(counts.values()) / average))
        ranked.append((score, passage))
    result, used = [], 0
    for score, passage in sorted(ranked, key=lambda pair: (-pair[0], pair[1]["claim_id"])):
        size = len(passage["evidence"]["quote"]) + sum(len(s["quote"]) for s in passage["scope"])
        if size > MAX_CONTEXT_CHARS - used:
            continue  # Never cut off qualifiers to satisfy a prompt budget.
        result.append({**passage, "id": "C" + str(len(result) + 1), "score": round(score, 6)})
        used += size
        if len(result) == top_k:
            break
    return result


def validate_generation(content, citations):
    """Technical citation gate only. Does not certify semantic/legal entailment."""
    if not isinstance(content, str) or len(content) > 40_000:
        raise ValueError("invalid_answer_schema")
    value = json.loads(content)
    if not isinstance(value, dict) or set(value) != {"status", "statements"}:
        raise ValueError("invalid_answer_schema")
    rows = value["statements"]
    if value["status"] == "insufficient_evidence" and rows == []:
        return value
    if value["status"] != "answered" or not isinstance(rows, list) or not 1 <= len(rows) <= 8:
        raise ValueError("invalid_answer_schema")
    valid_ids = {c["id"] for c in citations}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"text", "citation_ids"} or not isinstance(row["text"], str) or not 1 <= len(row["text"].strip()) <= 3000:
            raise ValueError("invalid_answer_schema")
        ids = row["citation_ids"]
        if not isinstance(ids, list) or not ids or not all(isinstance(i, str) and i in valid_ids for i in ids):
            raise ValueError("citation_outside_bundle")
    return value


class ChatService:
    def __init__(self, store, provider=None):
        self.store, self.provider = store, provider
        self._lock = threading.Lock()
        with store.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS chat_sessions (id TEXT PRIMARY KEY, body TEXT NOT NULL)")

    def sessions(self):
        with self.store.connect() as db:
            rows = [json.loads(r[0]) for r in db.execute("SELECT body FROM chat_sessions ORDER BY rowid DESC")]
        return [{k: r[k] for k in ("id", "revision", "created_at")} for r in rows]

    def session(self, session_id):
        with self.store.connect() as db:
            row = db.execute("SELECT body FROM chat_sessions WHERE id=?", (session_id,)).fetchone()
        if row is None:
            raise ValueError("chat_session_not_found")
        return json.loads(row[0])

    def start(self, revision_id):
        revision = self.store.revision(revision_id)
        if not approved_passages(revision["graph"]):
            raise ValueError("KB chưa có quy phạm được người dùng duyệt. Hãy duyệt gộp trước khi hỏi đáp")
        session = {"schema_version": "review-chat-v1", "id": uuid4().hex, "revision": revision_id,
                   "created_at": datetime.now(timezone.utc).isoformat(), "turns": []}
        with self.store.connect() as db:
            db.execute("INSERT INTO chat_sessions VALUES (?, ?)", (session["id"], canonical(session)))
        return session

    def ask(self, session_id, question, mode="extractive", allow_public_transfer=False):
        if not isinstance(question, str) or not 1 <= len(question.strip()) <= 1500:
            raise ValueError("Câu hỏi cần có nội dung, tối đa 1500 ký tự")
        if mode not in {"extractive", "llm"}:
            raise ValueError("invalid_chat_mode")
        # Serialize updates to avoid losing turns and never hold SQLite locks over network I/O.
        with self._lock:
            session = self.session(session_id)
            revision = self.store.revision(session["revision"])
            passages = approved_passages(revision["graph"])
            citations = retrieve(passages, question)
            response = {"schema_version": "review-chat-v1", "mode": mode, "revision": session["revision"],
                        "question": question.strip(), "citations": citations, "statements": [], "legal_status": "unknown",
                        "status": "sources_found" if citations else "insufficient_evidence",
                        "note": "Tra cứu đoạn đã duyệt theo từ khóa; chưa phải câu trả lời tổng hợp. Hãy đối chiếu nguyên văn, không suy ra hiệu lực hiện hành."}
            if mode == "llm":
                if self.provider is None:
                    response.update(status="provider_disabled", note="Chưa bật model. Bạn vẫn có thể tra cứu nguồn local.")
                elif allow_public_transfer is not True:
                    response.update(status="transfer_not_approved", note="Cần xác nhận cho từng lượt gửi câu hỏi và trích đoạn công khai sang 9Router.")
                elif citations:
                    try:
                        result = self.provider.generate(question.strip(), citations)
                        validated = validate_generation(result["content"], citations)
                        response.update(**validated, usage=result.get("usage", {}),
                                        note="Câu trả lời do model tạo. Đã kiểm tra citation thuộc bundle, chưa xác minh ngữ nghĩa hoặc hiệu lực pháp luật.")
                    except ProviderError as exc:
                        response.update(status="provider_error", error_code=exc.code, note="Model chưa trả lời được; có thể xem các đoạn nguồn local bên dưới.")
                    except (ValueError, TypeError):
                        response.update(status="answer_rejected", note="Đầu ra model không đạt schema/citation gate; không hiển thị câu trả lời chưa đạt. Có thể xem nguyên văn bên dưới.")
            response["id"] = uuid4().hex
            response["created_at"] = datetime.now(timezone.utc).isoformat()
            session["turns"].append(response)
            with self.store.connect() as db:
                db.execute("UPDATE chat_sessions SET body=? WHERE id=?", (canonical(session), session_id))
        return response
