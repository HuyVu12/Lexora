"""Chat over human-approved evidence of one or more pinned KB revisions, offline by default."""

from collections import Counter
from datetime import datetime, timezone
import json
import math
import threading
import unicodedata
from uuid import uuid4

from legal_ai.common.io import canonical, digest
from legal_ai.providers.pilot import ProviderError
from legal_ai.rag.dense import DenseIndex, fuse
from legal_ai.retrieval.bm25 import tokens
from legal_ai.validation.evidence import check_evidence

# This is a conservative lexical relevance gate, not a legal entailment test.
STOP = set("tôi em mình bạn xin hỏi là thì mà và của cho với về được những các một có không phải gì nào bao nhiêu như thế nào trong theo hay hãy biết giúp đang cần ai người lao động sử dụng".split())
MAX_CONTEXT_CHARS = 10_000
MAX_SESSION_KBS = 5
# Calibrated on gemini-embedding-001 (768 dims): related legal sentences ~0.8, unrelated ~0.6.
DENSE_MIN_SIMILARITY = 0.72
# In hybrid mode a passage, even a keyword match, is dropped when it is clearly less similar
# than the best passage; two shared words such as "thử việc" are not enough on their own.
DENSE_RELATIVE_MARGIN = 0.10


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
                         "human_review": claim["human_review"],
                         "edited": bool(claim["human_review"].get("edited"))})
    return passages


def lexical_scores(passages, question):
    """(BM25 score, passage index) for passages matching enough query terms."""
    query = set(terms(question)) - STOP
    if not query or not passages:
        return []
    docs = [Counter(terms(p["evidence"]["quote"] + " " + " ".join(s["quote"] for s in p["scope"]))) for p in passages]
    average = sum(sum(d.values()) for d in docs) / len(docs)
    ranked = []
    for index, counts in enumerate(docs):
        matched = query & counts.keys()
        if len(matched) < min(2, len(query)):
            continue
        score = 0.0
        for word in matched:
            frequency = counts[word]
            df = sum(word in d for d in docs)
            score += math.log(1 + (len(docs) - df + .5) / (df + .5)) * frequency * 2.5 / (frequency + 1.5 * (.25 + .75 * sum(counts.values()) / average))
        ranked.append((score, index))
    return ranked


def select(passages, ranked, top_k=3):
    """Take ranked (index, extra fields) rows into a citation bundle within the context budget."""
    result, used = [], 0
    for index, extra in ranked:
        passage = passages[index]
        size = len(passage["evidence"]["quote"]) + sum(len(s["quote"]) for s in passage["scope"])
        if size > MAX_CONTEXT_CHARS - used:
            continue  # Never cut off qualifiers to satisfy a prompt budget.
        result.append({**passage, "id": "C" + str(len(result) + 1), **extra})
        used += size
        if len(result) == top_k:
            break
    return result


def retrieve(passages, question, top_k=3):
    ranked = sorted(lexical_scores(passages, question), key=lambda pair: (-pair[0], passages[pair[1]]["claim_id"]))
    return select(passages, [(index, {"score": round(score, 6)}) for score, index in ranked], top_k)


def hybrid_retrieve(passages, question, similarities, top_k=3):
    fused = fuse(lexical_scores(passages, question), similarities, min_similarity=DENSE_MIN_SIMILARITY)
    if fused:
        best = max(row["similarity"] for _, row in fused)
        fused = [(index, row) for index, row in fused if row["similarity"] >= best - DENSE_RELATIVE_MARGIN]
    return select(passages, [(index, {"score": round(row["score"], 6), "lexical_rank": row["lexical_rank"],
                                      "dense_rank": row["dense_rank"], "similarity": row["similarity"]}) for index, row in fused], top_k)


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
    def __init__(self, store, provider=None, embedder=None):
        self.store, self.provider = store, provider
        self.dense = DenseIndex(store, embedder) if embedder is not None else None
        self._lock = threading.Lock()
        with store.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS chat_sessions (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            legacy = [(i, json.loads(b)) for i, b in db.execute("SELECT id, body FROM chat_sessions").fetchall()]
        for session_id, session in legacy:
            if "bindings" in session:
                continue
            # review-chat-v1 sessions pinned one revision; keep that pin inside its migrated KB.
            revision = store.revision(session.pop("revision"))
            session.update(schema_version="review-chat-v2", bindings=[{"kb_id": revision["kb_id"], "revision_id": revision["id"]}])
            with store.connect() as db:
                db.execute("UPDATE chat_sessions SET body=? WHERE id=?", (canonical(session), session_id))

    def _kbs(self):
        return {kb["id"]: kb for kb in self.store.knowledge_bases()}

    def _named(self, bindings):
        kbs = self._kbs()
        return [{**b, "kb_name": kbs.get(b["kb_id"], {}).get("name")} for b in bindings]

    def sessions(self):
        with self.store.connect() as db:
            rows = [json.loads(r[0]) for r in db.execute("SELECT body FROM chat_sessions ORDER BY rowid DESC")]
        return [{"id": r["id"], "created_at": r["created_at"], "turns": len(r["turns"]),
                 "bindings": self._named(r["bindings"])} for r in rows]

    def session(self, session_id):
        with self.store.connect() as db:
            row = db.execute("SELECT body FROM chat_sessions WHERE id=?", (session_id,)).fetchone() if isinstance(session_id, str) else None
        if row is None:
            raise ValueError("chat_session_not_found")
        session = json.loads(row[0])
        session["bindings"] = self._named(session["bindings"])
        return session

    def start(self, kb_ids):
        if not isinstance(kb_ids, list) or not 1 <= len(kb_ids) <= MAX_SESSION_KBS or len(set(map(str, kb_ids))) != len(kb_ids):
            raise ValueError(f"Chọn từ 1 đến {MAX_SESSION_KBS} kho tri thức khác nhau")
        bindings = []
        for kb_id in kb_ids:
            kb = self.store.knowledge_base(kb_id)
            if kb["archived_at"]:
                raise ValueError("Kho “" + kb["name"] + "” đã được lưu trữ")
            revision = self.store.revision(kb["current_revision"], kb_id)
            if not approved_passages(revision["graph"]):
                raise ValueError("Kho “" + kb["name"] + "” chưa có quy phạm được duyệt. Hãy duyệt và công bố trước khi hỏi đáp")
            bindings.append({"kb_id": kb_id, "revision_id": revision["id"]})
        session = {"schema_version": "review-chat-v2", "id": uuid4().hex, "bindings": bindings,
                   "created_at": datetime.now(timezone.utc).isoformat(), "turns": []}
        with self.store.connect() as db:
            db.execute("INSERT INTO chat_sessions VALUES (?, ?)", (session["id"], canonical(session)))
        return self.session(session["id"])

    def _passages(self, bindings):
        """Approved passages of every pinned revision; one entry per exact quote, listing all KBs holding it."""
        merged, kbs = {}, []
        for binding in bindings:
            kb = self.store.knowledge_base(binding["kb_id"])
            if kb["archived_at"]:
                raise ValueError("Kho “" + kb["name"] + "” đã được lưu trữ; hãy tạo cuộc trò chuyện mới")
            revision = self.store.revision(binding["revision_id"], binding["kb_id"])
            kbs.append(kb)
            for passage in approved_passages(revision["graph"]):
                e = passage["evidence"]
                key = (e["normalized_sha256"], e["unit_version_id"], e["start"], e["end"])
                source = {"kb_id": kb["id"], "kb_name": kb["name"], "revision": revision["id"],
                          "claim_id": passage["claim_id"], "edited": passage["edited"]}
                if key in merged:
                    merged[key]["sources"].append(source)
                    merged[key]["edited"] = merged[key]["edited"] or passage["edited"]
                else:
                    merged[key] = {**passage, "sources": [source]}
        return list(merged.values()), kbs

    def _retrieve(self, passages, kbs, question, semantic):
        """Hybrid ranking only when asked, configured and every bound KB is public; lexical otherwise."""
        if not semantic:
            return retrieve(passages, question), {"mode": "lexical", "reason": "not_requested"}
        if self.dense is None:
            return retrieve(passages, question), {"mode": "lexical", "reason": "embedding_disabled"}
        if any(kb["data_class"] != "public" for kb in kbs):
            return retrieve(passages, question), {"mode": "lexical", "reason": "private_kb"}
        try:
            similarities = self.dense.similarities(passages, question.strip()) if passages else []
        except ProviderError as exc:
            return retrieve(passages, question), {"mode": "lexical", "reason": "embedding_error", "error_code": exc.code}
        return hybrid_retrieve(passages, question, similarities), {"mode": "hybrid", "model": self.dense.model}

    def ask(self, session_id, question, mode="extractive", allow_public_transfer=False, semantic=False):
        if not isinstance(question, str) or not 1 <= len(question.strip()) <= 1500:
            raise ValueError("Câu hỏi cần có nội dung, tối đa 1500 ký tự")
        if mode not in {"extractive", "llm"}:
            raise ValueError("invalid_chat_mode")
        # Serialize updates to avoid losing turns and never hold SQLite locks over network I/O.
        with self._lock:
            session = self.session(session_id)
            passages, kbs = self._passages(session["bindings"])
            citations, retrieval = self._retrieve(passages, kbs, question, semantic is True)
            response = {"schema_version": "review-chat-v2", "mode": mode, "retrieval": retrieval,
                        "bindings": [{k: b[k] for k in ("kb_id", "kb_name", "revision_id")} for b in session["bindings"]],
                        "question": question.strip(), "citations": citations, "statements": [], "legal_status": "unknown",
                        "status": "sources_found" if citations else "insufficient_evidence",
                        "note": ("Tra cứu đoạn đã duyệt theo từ khóa và ngữ nghĩa" if retrieval["mode"] == "hybrid" else "Tra cứu đoạn đã duyệt theo từ khóa")
                                + "; chưa phải câu trả lời tổng hợp. Hãy đối chiếu nguyên văn, không suy ra hiệu lực hiện hành."}
            if mode == "llm":
                if self.provider is None:
                    response.update(status="provider_disabled", note="Chưa bật model. Bạn vẫn có thể tra cứu nguồn local.")
                elif any(kb["data_class"] != "public" for kb in kbs):
                    response.update(status="private_transfer_blocked", note="Cuộc trò chuyện có kho riêng tư nên không gửi dữ liệu sang model. Bạn vẫn có thể tra cứu nguồn local.")
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
            with self.store.connect() as db:
                body = json.loads(db.execute("SELECT body FROM chat_sessions WHERE id=?", (session_id,)).fetchone()[0])
                body["turns"].append(response)
                db.execute("UPDATE chat_sessions SET body=? WHERE id=?", (canonical(body), session_id))
        return response
