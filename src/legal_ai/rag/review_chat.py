"""Chat over human-approved evidence of one or more pinned KB revisions, offline by default."""

from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
import json
import math
import threading
import unicodedata
from uuid import uuid4

from legal_ai.common.cache import BoundedCache
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
PASSAGE_CACHE_SIZE = 16  # Approved passages of one revision: small next to the revision itself.
# Evidence gate of the chat (docs/features/reviewed-kb-chat.md, "Cổng căn cứ"). Besides sharing two content words with
# the question, a passage may answer it only when it holds, on its own, one of:
# - at least GATE_SHARE of the question's IDF mass (a word absent from every approved passage weighs the most, so
#   "bitcoin" or "xăng" cannot be outvoted by common words such as "hợp", "pháp", "giá");
# - GATE_PHRASES whole two-syllable words of the question (adjacent content words such as "thử việc", "kỷ luật");
# - GATE_LONG_WORDS content words covering GATE_LONG_SHARE of the mass (long questions told as a story).
# Thresholds come from an offline check over the pilot base (hand-written in/out-of-scope questions and the labelled
# question set); see the doc. This gate is the chat's only; the DK1-DK4 retrieval runs do not use it.
GATE_SHARE = 0.5
GATE_PHRASES = 2
GATE_LONG_WORDS = 5
GATE_LONG_SHARE = 0.2
# Vietnamese tone marks (huyền, sắc, ngã, hỏi, nặng); vowel-quality marks (ă, â, ê, ô, ơ, ư) are kept.
TONE_MARKS = {"\u0300", "\u0301", "\u0303", "\u0309", "\u0323"}
TITLE_MAX = 120  # A conversation title typed by its owner.
DEFAULT_TITLE_CHARS = 70  # The first question, cut on a word boundary, names a conversation without a title.
SUGGESTION_COUNT = 4
SUGGESTION_COVERAGE = 0.6
# Everyday questions offered on an empty conversation, kept only when the chosen bases hold approved passages that
# match them (offline lexical retrieval, never a model call). Statute language, so they stay Vietnamese in every locale.
SUGGESTED_QUESTIONS = (
    "Tiền lương thử việc ít nhất bằng bao nhiêu?",
    "Thời gian thử việc tối đa là bao lâu?",
    "Người lao động được nghỉ hằng năm bao nhiêu ngày?",
    "Hợp đồng lao động phải có những nội dung chủ yếu nào?",
    "Số giờ làm thêm tối đa trong một tháng là bao nhiêu?",
    "Người lao động được đơn phương chấm dứt hợp đồng lao động khi nào?",
    "Trợ cấp thôi việc được tính như thế nào?",
    "Lao động nữ được nghỉ thai sản bao lâu?",
)
# Article headings too generic to make a useful question.
GENERIC_HEADINGS = {"phạm vi điều chỉnh", "đối tượng áp dụng", "giải thích từ ngữ", "hiệu lực thi hành",
                    "trách nhiệm thi hành", "điều khoản chuyển tiếp", "quy định chuyển tiếp", "tổ chức thực hiện"}


def terms(text):
    # Search may ignore accents; source quotes and evidence identities never do.
    folded = "".join(c for c in unicodedata.normalize("NFD", text.casefold().replace("đ", "d")) if not unicodedata.combining(c))
    return tokens(folded)


# Stopwords are matched on the accented word, so "tôi" goes but "tối" (tối đa), and "động" (người lao động) goes but
# "đồng" (hợp đồng) stays. Only a word typed without any accent is compared accent-folded, as it cannot be told apart.
STOP_FOLDED = set(terms(" ".join(STOP)))


def query_terms(question):
    kept = []
    for word in tokens(question.casefold()):
        folded = terms(word)
        if word in STOP or (word.isascii() and folded and folded[0] in STOP_FOLDED):
            continue
        kept.extend(folded)
    return set(kept)


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


@lru_cache(maxsize=8192)
def passage_terms(text):
    """Term counts of one passage text; shared between questions, so callers must not modify them."""
    return Counter(terms(text))


def toned(word):
    """A word with its accents, wherever the tone mark sits: "hòa" and "hoà", "thủy" and "thuỷ" give one key."""
    chars = unicodedata.normalize("NFD", word.casefold())
    tone = "".join(c for c in chars if c in TONE_MARKS)
    return unicodedata.normalize("NFC", "".join(c for c in chars if c not in TONE_MARKS)) + ("#" + tone if tone else "")


def word_key(word, exact):
    """Accented words match their exact accented form ("vé" never meets "về", "đá" never "đa"); a word typed without
    any accent can only be compared accent-folded."""
    return "t:" + toned(word) if exact else "f:" + "".join(terms(word))


@lru_cache(maxsize=8192)
def passage_index(text):
    """Key counts (accented and folded form of every word) and adjacent word pairs of one passage. Shared: read only."""
    words = tokens(text)
    counts = Counter()
    for word in words:
        counts[word_key(word, True)] += 1
        counts[word_key(word, False)] += 1
    pairs = frozenset((word_key(a, exact), word_key(b, exact)) for a, b in zip(words, words[1:]) for exact in (True, False))
    return counts, pairs


def question_index(question):
    """The question's content keys (stopwords removed) and the adjacent pairs of content words in it."""
    keys, pairs, previous = set(), set(), None
    for word in tokens(question.casefold()):
        folded = terms(word)
        if word in STOP or (word.isascii() and folded and folded[0] in STOP_FOLDED) or not folded:
            previous = None
            continue
        keys.add(word_key(word, not word.isascii()))
        if previous is not None:
            exact = not (word.isascii() or previous.isascii())
            pairs.add((word_key(previous, exact), word_key(word, exact)))
        previous = word
    return keys, pairs


def passage_text(passage):
    return passage["evidence"]["quote"] + " " + " ".join(s["quote"] for s in passage["scope"])


def gated(passages, question):
    """(BM25 score, passage index, IDF share) of the passages that pass the evidence gate (see GATE_SHARE)."""
    query, phrases = question_index(question)
    if not query or not passages:
        return []
    docs = [passage_index(passage_text(p)) for p in passages]
    lengths = [sum(counts.values()) for counts, _ in docs]
    average = sum(lengths) / len(docs)
    idf = {key: math.log(1 + (len(docs) - df + .5) / (df + .5))
           for key in query for df in [sum(key in counts for counts, _ in docs)]}
    mass = sum(idf.values())
    ranked = []
    for index, (counts, pairs) in enumerate(docs):
        matched = query & counts.keys()
        if len(matched) < min(2, len(query)):
            continue
        share = sum(idf[key] for key in matched) / mass
        if not (share >= GATE_SHARE or len(phrases & pairs) >= GATE_PHRASES or (len(matched) >= GATE_LONG_WORDS and share >= GATE_LONG_SHARE)):
            continue
        score = 0.0
        for key in matched:
            frequency = counts[key]
            score += idf[key] * frequency * 2.5 / (frequency + 1.5 * (.25 + .75 * lengths[index] / average))
        ranked.append((score, index, share))
    return ranked


def lexical_scores(passages, question):
    """(BM25 score, passage index) for passages that pass the evidence gate."""
    return [(score, index) for score, index, _ in gated(passages, question)]


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


def default_title(session):
    """The first question, cut on a word boundary; None for a conversation without questions."""
    if not session["turns"]:
        return None
    text = " ".join(session["turns"][0]["question"].split())
    if len(text) <= DEFAULT_TITLE_CHARS:
        return text
    cut = text[:DEFAULT_TITLE_CHARS].rsplit(" ", 1)[0] or text[:DEFAULT_TITLE_CHARS]
    return cut.rstrip(",;:.") + "…"


def heading(unit):
    """First line of an article or chapter text without its number: "Điều 26. Thử việc" gives "Thử việc"."""
    line = unit["text"].splitlines()[0].strip() if unit.get("text") else ""
    words = line.split(" ", 2)
    if len(words) >= 2 and words[0] in {"Điều", "Chương", "Mục"}:
        line = words[2] if len(words) == 3 else ""
    return line.strip(" .:") or None


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
        # Approved passages per (revision, KB), checked once: revisions are immutable, so the integrity checks of
        # `approved_passages` hold for as long as the ID exists. Entries are shared; callers copy before changing.
        self._approved = BoundedCache(PASSAGE_CACHE_SIZE)
        self._units = BoundedCache(PASSAGE_CACHE_SIZE)
        with store.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS chat_sessions (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            # Owner-facing metadata kept beside the immutable record: a title the owner typed, and when the owner
            # removed the conversation from view. Hiding never deletes the turns, so audits and usage counts stay whole.
            db.execute("CREATE TABLE IF NOT EXISTS chat_session_meta (id TEXT PRIMARY KEY, title TEXT, hidden_at TEXT)")
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

    @staticmethod
    def _named(bindings, kbs):
        return [{**b, "kb_name": kbs.get(b["kb_id"], {}).get("name")} for b in bindings]

    def _meta(self, db, ids=None):
        if ids is None:
            rows = db.execute("SELECT id, title, hidden_at FROM chat_session_meta").fetchall()
        else:
            rows = []
            for at in range(0, len(ids), 500):
                chunk = ids[at:at + 500]
                rows += db.execute(f"SELECT id, title, hidden_at FROM chat_session_meta WHERE id IN ({','.join('?' * len(chunk))})", chunk).fetchall()
        return {r[0]: {"title": r[1], "hidden_at": r[2]} for r in rows}

    @staticmethod
    def _titled(session, meta):
        custom = (meta or {}).get("title")
        updated = session["turns"][-1]["created_at"] if session["turns"] else session["created_at"]
        return {"title": custom or default_title(session), "custom_title": bool(custom), "updated_at": updated}

    def sessions(self, ids=None):
        """Visible sessions, most recently active first; with `ids`, only those (the signed-in account's), so others
        are never read. Hidden sessions are left out but stay stored."""
        with self.store.connect() as db:
            if ids is None:
                rows = db.execute("SELECT body, rowid FROM chat_sessions").fetchall()
                meta = self._meta(db)
            else:
                ids = sorted(i for i in ids if isinstance(i, str))
                rows = []
                for at in range(0, len(ids), 500):
                    chunk = ids[at:at + 500]
                    rows += db.execute(f"SELECT body, rowid FROM chat_sessions WHERE id IN ({','.join('?' * len(chunk))})", chunk).fetchall()
                meta = self._meta(db, ids)
        if not rows:
            return []
        kbs = self._kbs()
        result = []
        for body, rowid in rows:
            r = json.loads(body)
            if meta.get(r["id"], {}).get("hidden_at"):
                continue
            result.append((rowid, {"id": r["id"], "created_at": r["created_at"], "turns": len(r["turns"]),
                                   **self._titled(r, meta.get(r["id"])), "bindings": self._named(r["bindings"], kbs)}))
        result.sort(key=lambda pair: (pair[1]["updated_at"], pair[0]), reverse=True)
        return [summary for _, summary in result]

    def hidden(self, session_id):
        """True when the owner removed this conversation from view."""
        with self.store.connect() as db:
            row = db.execute("SELECT hidden_at FROM chat_session_meta WHERE id=?", (session_id,)).fetchone() if isinstance(session_id, str) else None
        return bool(row and row[0])

    def session(self, session_id):
        with self.store.connect() as db:
            row = db.execute("SELECT body FROM chat_sessions WHERE id=?", (session_id,)).fetchone() if isinstance(session_id, str) else None
            meta = self._meta(db, [session_id]).get(session_id) if row is not None else None
        if row is None or (meta and meta["hidden_at"]):
            raise ValueError("chat_session_not_found")
        session = json.loads(row[0])
        session["bindings"] = self._named(session["bindings"], self._kbs())
        session.update(self._titled(session, meta))
        return session

    def rename(self, session_id, title):
        """Set the owner's title; an empty title goes back to the first question. Turns are never touched."""
        if not isinstance(title, str):
            raise ValueError("Tên cuộc trò chuyện không hợp lệ")
        title = " ".join(title.split())
        if len(title) > TITLE_MAX:
            raise ValueError(f"Tên cuộc trò chuyện tối đa {TITLE_MAX} ký tự")
        self.session(session_id)  # Exists and is still visible.
        with self.store.connect() as db:
            db.execute("INSERT INTO chat_session_meta (id, title) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET title=excluded.title",
                       (session_id, title or None))
        return self.session(session_id)

    def hide(self, session_id):
        """Remove a conversation from its owner's view. The record and its turns stay in the store."""
        self.session(session_id)
        with self.store.connect() as db:
            db.execute("INSERT INTO chat_session_meta (id, hidden_at) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET hidden_at=excluded.hidden_at",
                       (session_id, datetime.now(timezone.utc).isoformat()))
        return {"hidden": session_id}

    def _unit_index(self, revision_id, kb_id):
        """Legal units of one pinned revision by version ID and by unit ID (revisions are immutable, so cached)."""
        def build():
            units = [n["payload"] for n in self.store.revision(revision_id, kb_id)["graph"]["nodes"] if n["kind"] == "LegalUnit"]
            return {u["unit_version_id"]: u for u in units}, {u["unit_id"]: u for u in units}
        return self._units.get((revision_id, kb_id), build)

    def source(self, session_id, turn_index, citation_id):
        """One cited passage of a conversation inside its source unit of the pinned revision: the unit's exact text
        with the quote's offsets, its path in the document and the bases holding it. The unit text is the published
        source text readers can already open in the base's graph; only the quote is approved evidence."""
        session = self.session(session_id)
        if not isinstance(turn_index, int) or not 0 <= turn_index < len(session["turns"]):
            raise ValueError("chat_turn_not_found")
        citation = next((c for c in session["turns"][turn_index]["citations"] if c["id"] == citation_id), None)
        if citation is None:
            raise ValueError("chat_citation_not_found")
        evidence = citation["evidence"]
        first = citation["sources"][0] if citation.get("sources") else {}
        kb_id = first.get("kb_id") or session["bindings"][0]["kb_id"]
        revision_id = first.get("revision") or next(b["revision_id"] for b in session["bindings"] if b["kb_id"] == kb_id)
        by_version, by_id = self._unit_index(revision_id, kb_id)
        unit = by_version.get(evidence["unit_version_id"])
        if unit is None or unit["text"][evidence["start"]:evidence["end"]] != evidence["quote"]:
            raise ValueError("source_integrity_error")
        path, at = [], unit
        while at is not None and len(path) < 8:
            path.append({"unit_id": at["unit_id"], "unit_type": at["unit_type"], "label": at.get("label"),
                         "heading": heading(at) if at["unit_type"] in {"article", "chapter", "section"} else None})
            at = by_id.get(at["parent_id"]) if at.get("parent_id") else None
        return {"citation_id": citation["id"], "title": citation["title"], "source_url": citation.get("source_url"),
                "synthetic": citation.get("synthetic", False), "edited": citation.get("edited", False),
                "kb_id": kb_id, "revision_id": revision_id,
                "sources": [{"kb_id": s.get("kb_id"), "kb_name": s.get("kb_name"), "revision": s.get("revision")} for s in citation.get("sources", [])],
                "unit_id": unit["unit_id"], "unit_type": unit["unit_type"], "text": unit["text"],
                "start": evidence["start"], "end": evidence["end"], "quote": evidence["quote"],
                "scope": [s["quote"] for s in citation.get("scope", [])], "path": path[::-1]}

    def suggestions(self, kb_ids):
        """Up to four starter questions for the current revisions of the chosen bases, without any model call:
        everyday questions that find approved passages there, then questions made from the headings of the articles
        holding the most approved passages."""
        if not isinstance(kb_ids, list) or not 1 <= len(kb_ids) <= MAX_SESSION_KBS or len(set(map(str, kb_ids))) != len(kb_ids):
            raise ValueError(f"Chọn từ 1 đến {MAX_SESSION_KBS} kho tri thức khác nhau")
        bindings = []
        for kb_id in kb_ids:
            kb = self.store.knowledge_base(kb_id)
            if not kb["archived_at"] and kb.get("current_revision"):
                bindings.append({"kb_id": kb_id, "revision_id": kb["current_revision"]})
        if not bindings:
            return {"suggestions": []}
        passages, _ = self._passages(bindings)

        def covered(question):
            # Stricter than the answer gate: one approved passage holds most of the question's information.
            return max((share for _, _, share in gated(passages, question)), default=0) >= SUGGESTION_COVERAGE
        picked = [q for q in SUGGESTED_QUESTIONS if covered(q)][:SUGGESTION_COUNT]
        if len(picked) < SUGGESTION_COUNT:
            counts = Counter()
            for passage in passages:
                source = passage["sources"][0]
                _, by_id = self._unit_index(source["revision"], source["kb_id"])
                at = by_id.get(passage["evidence"]["unit_id"])
                while at is not None and at["unit_type"] != "article":
                    at = by_id.get(at["parent_id"]) if at.get("parent_id") else None
                title = heading(at) if at is not None else None
                if title and title.casefold() not in GENERIC_HEADINGS and not title.isupper() and len(title) <= 90:
                    counts[title] += 1
            for title, _ in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])):
                question = f"Pháp luật quy định thế nào về {title[0].lower() + title[1:]}?"
                if question not in picked:
                    picked.append(question)
                if len(picked) == SUGGESTION_COUNT:
                    break
        return {"suggestions": picked}

    def _approved_passages(self, revision_id, kb_id):
        return self._approved.get((revision_id, kb_id), lambda: approved_passages(self.store.revision(revision_id, kb_id)["graph"]))

    def start(self, kb_ids):
        if not isinstance(kb_ids, list) or not 1 <= len(kb_ids) <= MAX_SESSION_KBS or len(set(map(str, kb_ids))) != len(kb_ids):
            raise ValueError(f"Chọn từ 1 đến {MAX_SESSION_KBS} kho tri thức khác nhau")
        bindings = []
        for kb_id in kb_ids:
            kb = self.store.knowledge_base(kb_id)
            if kb["archived_at"]:
                raise ValueError("Kho “" + kb["name"] + "” đã được lưu trữ")
            if not self._approved_passages(kb["current_revision"], kb_id):
                raise ValueError("Kho “" + kb["name"] + "” chưa có quy phạm được duyệt. Hãy duyệt và công bố trước khi hỏi đáp")
            bindings.append({"kb_id": kb_id, "revision_id": kb["current_revision"]})
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
            revision_id = binding["revision_id"]
            passages = self._approved_passages(revision_id, binding["kb_id"])
            kbs.append(kb)
            for passage in passages:
                e = passage["evidence"]
                key = (e["normalized_sha256"], e["unit_version_id"], e["start"], e["end"])
                source = {"kb_id": kb["id"], "kb_name": kb["name"], "revision": revision_id,
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
                        if validated["status"] == "insufficient_evidence":
                            # Passages were found; the model judged that they do not answer the question.
                            response.update(status="model_insufficient",
                                            note="Model cho rằng các đoạn tìm được chưa đủ để trả lời. Hãy xem nguyên văn bên dưới hoặc hỏi cụ thể hơn.")
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
