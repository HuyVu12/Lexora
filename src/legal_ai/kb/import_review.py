"""Offline TXT extraction, per-knowledge-base review and immutable graph revisions.

A store holds several knowledge bases (KB). Each KB owns a linear chain of immutable
revisions. A draft targets either a new KB or one existing KB pinned to its current
revision; review decisions are saved incrementally and only applied on publish.
Curated edits never alter source text: every edited slot points to an exact quote.
"""

from collections import Counter
from copy import deepcopy
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import unicodedata
from uuid import uuid4

from legal_ai.common.io import canonical, digest
from legal_ai.extraction.norms import ClaimBuilder, leaf_units, sentences
from legal_ai.ingestion.parser import parse
from legal_ai.kb.graph import GRAPH_VERSION, make_graph
from legal_ai.normalization.text import normalize
from legal_ai.schemas.contract import MODALITIES, VERSION, validate_claim
from legal_ai.validation.evidence import check_evidence

STORE_VERSION = "kb-store-v1"
MAX_BYTES = 1_000_000
KINDS = {"Entity", "LegalConcept"}
DATA_CLASSES = {"public", "private"}
DEFAULT_KB_NAME = "Kho mặc định"
CLAIM_PAYLOAD_EXTRAS = ("validation", "semantic_extraction", "human_review", "curation")
SLOTS = ("actor", "action", "beneficiary", "recipient", "object", "outcome", "conditions", "exceptions", "quantities", "deadlines", "scope")
EXTRACTION_MODES = {"rules", "llm"}
EXTRACTION_BUSY = {"queued", "running"}
MANUAL_RUN = "manual-v1"


class Conflict(ValueError):
    """The target KB moved on since the draft was prepared (HTTP 409)."""


def now():
    return datetime.now(timezone.utc).isoformat()


def label_key(value):
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def finish_graph(nodes, edges, references, reports):
    content = {"graph_version": GRAPH_VERSION, "nodes": sorted(nodes.values(), key=lambda n: n["id"]),
               "edges": sorted(edges.values(), key=lambda e: e["id"]),
               "references": references, "extraction_report": reports}
    return {**content, "graph_hash": digest(canonical(content)), "summary": {
        "nodes": dict(Counter(n["kind"] for n in nodes.values())),
        "edges": dict(Counter(e["kind"] for e in edges.values())),
        "claim_decisions": dict(Counter(n["payload"].get("validation", {}).get("decision", "needs_review")
                                        for n in nodes.values() if n["kind"] == "NormClaim")),
        "approved_claims": sum(1 for n in nodes.values() if n["kind"] == "NormClaim"
                               and n["payload"].get("human_review", {}).get("decision") == "approved"),
        "reference_status": dict(Counter(r["status"] for r in references)),
        "synthetic": any(n["payload"]["synthetic"] for n in nodes.values() if n["kind"] == "Document"),
        "legal_status": "unknown"}}


def empty_graph():
    return finish_graph({}, {}, [], [])


def machine_claim(payload):
    return {k: v for k, v in payload.items() if k not in CLAIM_PAYLOAD_EXTRAS}


def is_approved(node):
    return node["kind"] == "NormClaim" and node["payload"].get("human_review", {}).get("decision") == "approved"


def claim_origin(run_id):
    if run_id.startswith("norm-llm-v1:"):
        return "ai"
    if run_id.startswith(MANUAL_RUN + ":"):
        return "manual"
    if run_id.endswith(":cue-sentence") or run_id.startswith("norm-candidate"):
        return "cue"
    return "rules"


def graph_parts(graph):
    """Source records and machine claims of a draft graph, ready for make_graph."""
    nodes = graph["nodes"]
    return ([n["payload"] for n in nodes if n["kind"] == "Document"],
            [n["payload"] for n in nodes if n["kind"] == "LegalUnit"],
            {n["payload"]["evidence_id"]: n["payload"] for n in nodes if n["kind"] == "Evidence"},
            [machine_claim(n["payload"]) for n in nodes if n["kind"] == "NormClaim"])


def sentence_anchor(claim, evidence):
    rows = [evidence[e] for e in claim["evidence_ids"] if e in evidence and evidence[e]["unit_version_id"] == claim["source_unit_version_ids"][0]]
    return max(rows, key=lambda r: (r["end"] - r["start"], -r["start"])) if rows else None


def coverage_gaps(graph):
    """Sentences of leaf units that no claim touches. Each must be covered or dismissed before publish."""
    _, units, evidence, claims = graph_parts(graph)
    covered = {}
    for claim in claims:
        for eid in claim["evidence_ids"]:
            row = evidence.get(eid)
            if row:
                covered.setdefault(row["unit_version_id"], []).append((row["start"], row["end"]))
    gaps = []
    for unit in leaf_units(units):
        spans = covered.get(unit["unit_version_id"], [])
        for start, end, text in sentences(unit):
            if not any(a < end and start < b for a, b in spans):
                gaps.append({"id": f"gap:{unit['unit_version_id']}:{start}", "unit_version_id": unit["unit_version_id"],
                             "unit_id": unit["unit_id"], "start": start, "end": end, "text": text})
    return gaps


def entity_suggestions(graph, existing):
    return {n["id"]: [e["id"] for e in existing if e["kind"] == n["kind"] and label_key(e["label"]) == label_key(n["label"])]
            for n in graph["nodes"] if n["kind"] in KINDS}


def primary_quote(graph_nodes, claim):
    evidence = {n["payload"]["evidence_id"]: n["payload"] for n in graph_nodes if n["kind"] == "Evidence"}
    anchors = [evidence[e] for e in claim["evidence_ids"] if e in evidence and evidence[e]["unit_version_id"] == claim["source_unit_version_ids"][0]]
    return max(anchors, key=lambda a: len(a["quote"])) if anchors else None


class ReviewStore:
    def __init__(self, path, seed=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS knowledge_bases (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS revisions (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS drafts (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS review_decisions (draft_id TEXT NOT NULL, item_id TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY (draft_id, item_id))")
            if "kb_id" not in {row[1] for row in db.execute("PRAGMA table_info(revisions)")}:
                db.execute("ALTER TABLE revisions ADD COLUMN kb_id TEXT")
            self._migrate(db)
            if seed and not db.execute("SELECT 1 FROM knowledge_bases LIMIT 1").fetchone():
                graph = json.loads(Path(seed).read_text(encoding="utf-8"))
                if graph.get("graph_version") != GRAPH_VERSION:
                    raise ValueError("Seed graph version is unsupported")
                kb = self._insert_kb(db, DEFAULT_KB_NAME, "Khởi tạo từ graph seed; các ứng viên trong seed chưa được duyệt", "public")
                self._insert_revision(db, kb["id"], None, graph, None,
                                      "Initial review graph; existing candidates remain unverified", None)
            db.execute("INSERT OR REPLACE INTO meta VALUES ('store_version', ?)", (STORE_VERSION,))

    # Storage helpers -------------------------------------------------------

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _migrate(self, db):
        """Move a single-chain import-review-v1 store into one default KB. Never edits revision bodies."""
        if not db.execute("SELECT 1 FROM revisions WHERE kb_id IS NULL LIMIT 1").fetchone():
            return
        kb = self._insert_kb(db, DEFAULT_KB_NAME, "Chuyển từ kho một chuỗi revision trước đây", "public")
        db.execute("UPDATE revisions SET kb_id=? WHERE kb_id IS NULL", (kb["id"],))
        for draft_id, body in db.execute("SELECT id, body FROM drafts").fetchall():
            draft = json.loads(body)
            if "target" not in draft:
                draft.update(target={"mode": "merge", "kb_id": kb["id"]}, kb_id=kb["id"])
                db.execute("UPDATE drafts SET body=? WHERE id=?", (canonical(draft), draft_id))

    def _insert_kb(self, db, name, description, data_class):
        kb = {"id": uuid4().hex, "name": name, "description": description, "data_class": data_class,
              "created_at": now(), "archived_at": None}
        db.execute("INSERT INTO knowledge_bases VALUES (?, ?)", (kb["id"], canonical(kb)))
        return kb

    def _insert_revision(self, db, kb_id, parent, graph, reviewer, reason, review):
        revision = {"schema_version": "import-review-v1", "id": uuid4().hex, "kb_id": kb_id, "parent": parent,
                    "created_at": now(), "reviewer": reviewer, "reason": reason, "graph": graph, "review": review}
        db.execute("INSERT INTO revisions (id, body, kb_id) VALUES (?, ?, ?)", (revision["id"], canonical(revision), kb_id))
        return revision

    def _kb(self, db, kb_id, *, active=True):
        row = db.execute("SELECT body FROM knowledge_bases WHERE id=?", (kb_id,)).fetchone() if isinstance(kb_id, str) else None
        if row is None:
            raise ValueError("Không tìm thấy kho tri thức")
        kb = json.loads(row[0])
        if active and kb["archived_at"]:
            raise ValueError("Kho tri thức đã được lưu trữ")
        return kb

    def _kbs(self, db):
        return [json.loads(r[0]) for r in db.execute("SELECT body FROM knowledge_bases ORDER BY rowid")]

    @staticmethod
    def _read_revision(body, kb_id):
        revision = json.loads(body)
        revision.setdefault("kb_id", kb_id)
        return revision

    def _current(self, db, kb_id):
        row = db.execute("SELECT body, kb_id FROM revisions WHERE kb_id=? ORDER BY rowid DESC LIMIT 1", (kb_id,)).fetchone()
        if row is None:
            raise ValueError("Kho tri thức chưa có revision")
        return self._read_revision(*row)

    def _check_name(self, db, name):
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
            raise ValueError("Nhập tên kho tri thức (tối đa 100 ký tự)")
        if any(label_key(k["name"]) == label_key(name) for k in self._kbs(db) if not k["archived_at"]):
            raise ValueError("Đã có kho cùng tên; hãy chọn tên khác hoặc gộp vào kho đó")
        return name.strip()

    def _target(self, db, target):
        if not isinstance(target, dict) or target.get("mode") not in {"new", "merge"}:
            raise ValueError("Chọn đích nhập: tạo kho mới hoặc gộp vào kho có sẵn")
        if target["mode"] == "merge":
            kb = self._kb(db, target.get("kb_id"))
            return {"mode": "merge", "kb_id": kb["id"]}
        description = target.get("description") or ""
        data_class = target.get("data_class", "private")
        if not isinstance(description, str) or len(description) > 500:
            raise ValueError("Mô tả kho tối đa 500 ký tự")
        if data_class not in DATA_CLASSES:
            raise ValueError("Phân loại dữ liệu phải là công khai hoặc riêng tư")
        return {"mode": "new", "name": self._check_name(db, target.get("name")), "description": description.strip(),
                "data_class": data_class}

    def _decisions(self, db, draft_id):
        return {item: json.loads(body) for item, body in db.execute(
            "SELECT item_id, body FROM review_decisions WHERE draft_id=?", (draft_id,))}

    # Read API ---------------------------------------------------------------

    def current(self, kb_id):
        with self.connect() as db:
            self._kb(db, kb_id, active=False)
            return self._current(db, kb_id)

    def revision(self, revision_id, kb_id=None):
        with self.connect() as db:
            row = db.execute("SELECT body, kb_id FROM revisions WHERE id=?", (revision_id,)).fetchone() if isinstance(revision_id, str) else None
        if row is None:
            raise ValueError("Không tìm thấy revision")
        revision = self._read_revision(*row)
        if kb_id is not None and revision["kb_id"] != kb_id:
            raise ValueError("Revision không thuộc kho tri thức đã chọn")
        return revision

    def knowledge_base(self, kb_id):
        with self.connect() as db:
            kb = self._kb(db, kb_id, active=False)
            rows = db.execute("SELECT body, kb_id FROM revisions WHERE kb_id=? ORDER BY rowid DESC", (kb_id,)).fetchall()
        revisions = [self._read_revision(*r) for r in rows]
        current = revisions[0]
        documents = [{k: n["payload"].get(k) for k in ("document_id", "title", "source_url", "synthetic", "legal_status", "source_sha256", "accessed_at")}
                     for n in current["graph"]["nodes"] if n["kind"] == "Document"]
        return {**kb, "current_revision": current["id"], "updated_at": current["created_at"],
                "approved_claims": sum(1 for n in current["graph"]["nodes"] if is_approved(n)),
                "documents": documents,
                "revisions": [{k: r[k] for k in ("id", "parent", "created_at", "reviewer", "reason")} for r in revisions]}

    def knowledge_bases(self):
        with self.connect() as db:
            ids = [k["id"] for k in self._kbs(db)]
        result = []
        for kb_id in ids:
            detail = self.knowledge_base(kb_id)
            result.append({k: detail[k] for k in ("id", "name", "description", "data_class", "created_at", "archived_at",
                                                  "current_revision", "updated_at", "approved_claims")}
                          | {"documents": len(detail["documents"]), "revisions": len(detail["revisions"])})
        return result

    def draft(self, draft_id):
        with self.connect() as db:
            return self._draft(db, draft_id)

    def _draft(self, db, draft_id):
        row = db.execute("SELECT body FROM drafts WHERE id=?", (draft_id,)).fetchone() if isinstance(draft_id, str) else None
        if row is None:
            raise ValueError("Không tìm thấy bản nháp")
        return json.loads(row[0])

    def state(self):
        kbs = self.knowledge_bases()
        names = {k["id"]: k["name"] for k in kbs}
        with self.connect() as db:
            drafts = [json.loads(r[0]) for r in db.execute("SELECT body FROM drafts ORDER BY rowid DESC")]
            counts = {d: n for d, n in db.execute("SELECT draft_id, COUNT(*) FROM review_decisions WHERE item_id LIKE 'claim:%' AND item_id NOT LIKE '%/slot/%' GROUP BY draft_id")}
        return {"schema_version": STORE_VERSION, "knowledge_bases": kbs,
                "drafts": [{"id": d["id"], "title": d["title"], "status": d["status"], "created_at": d["created_at"],
                            "target": d["target"], "kb_name": names.get(d.get("kb_id")) or d["target"].get("name"),
                            "extraction_state": d.get("extraction", {}).get("state", "done"),
                            "claims": sum(1 for n in d["graph"]["nodes"] if n["kind"] == "NormClaim"),
                            "decided": counts.get(d["id"], 0)} for d in drafts]}

    # Draft creation -----------------------------------------------------------

    def prepare(self, title, text, synthetic=False, source_url=None, *, target, extraction="rules", extraction_model=None):
        if source_url is not None:
            from urllib.parse import urlsplit
            parsed_url = urlsplit(source_url)
            if parsed_url.scheme != "https" or parsed_url.hostname not in {"vbpl.vn", "www.vbpl.vn", "vanban.chinhphu.vn"} or parsed_url.username or parsed_url.password:
                raise ValueError("Nguồn thư viện phải là HTTPS trên host chính thức đã duyệt")
        if type(synthetic) is not bool:
            raise ValueError("Synthetic flag must be boolean")
        if not isinstance(title, str) or not title.strip() or len(title) > 200:
            raise ValueError("Nhập tên tài liệu (tối đa 200 ký tự)")
        if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > MAX_BYTES or "\x00" in text:
            raise ValueError("TXT phải có nội dung UTF-8, không chứa NUL, tối đa 1 MB")
        if extraction not in EXTRACTION_MODES:
            raise ValueError("Cách tách quy phạm không hợp lệ")
        if extraction == "llm" and (not isinstance(extraction_model, str) or not extraction_model.strip()):
            raise ValueError("Chưa bật model tách quy phạm")
        with self.connect() as db:
            target = self._target(db, target)
            base = self._current(db, target["kb_id"]) if target["mode"] == "merge" else None
            data_class = self._kb(db, target["kb_id"])["data_class"] if target["mode"] == "merge" else target["data_class"]
        if extraction == "llm" and data_class != "public":
            raise ValueError("Kho riêng tư không gửi nội dung ra dịch vụ AI bên ngoài; hãy dùng cách tách theo quy tắc")
        base_graph = base["graph"] if base else empty_graph()
        normalized = normalize(text.lstrip("﻿"), "upload/source.txt")
        version = normalized["normalized_sha256"]
        document_id = "upload-" + version
        if any(n["kind"] == "Document" and n["payload"]["document_id"] == document_id for n in base_graph["nodes"]):
            raise ValueError("Tài liệu này đã có trong kho đích; không nhập trùng")
        parsed = parse(normalized, document_id, version)
        if not parsed["units"]:
            raise ValueError("Chưa nhận diện được cấu trúc. TXT cần tiêu đề như ‘Điều 1. …’ trên một dòng riêng")
        # Reject malformed structure rather than publishing an incomplete source map.
        if any(a["code"] in {"orphan_heading", "duplicate_heading"} for a in parsed["audit"]):
            raise ValueError("Cấu trúc có heading trùng hoặc khoản/điểm thiếu cha; sửa TXT rồi nhập lại")
        if any(a["code"] == "quoted_text" for a in parsed["audit"]):
            raise ValueError("Văn bản có Điều sửa đổi văn bản khác (trích dẫn chứa Điều/khoản/điểm); kho tri thức chưa nhận loại này")
        document = {"schema_version": VERSION, "document_id": document_id, "document_version_id": version,
                    "snapshot_id": digest(text), "title": title.strip(), "source_url": source_url or "upload://" + document_id,
                    "accessed_at": now(), "source_sha256": digest(text), "effective_from": None,
                    "effective_to": None, "legal_status": "unknown", "synthetic": synthetic}
        graph = make_graph([document], parsed["units"], [], [], include_candidates=True, extraction_mode="norm-rules-v2")
        existing = [{k: n[k] for k in ("id", "kind", "label")} for n in base_graph["nodes"] if n["kind"] in KINDS]
        draft = {"schema_version": "import-review-v2", "id": uuid4().hex, "title": title.strip(),
                 "target": target, "kb_id": target.get("kb_id"), "base_revision": base["id"] if base else None,
                 "created_at": now(), "status": "draft", "raw_text": text,
                 "normalized": normalized, "parser_audit": parsed["audit"], "unassigned_text": parsed["unassigned_text"],
                 "graph": graph, "suggestions": entity_suggestions(graph, existing), "existing_entities": existing,
                 "extraction": {"mode": "rules", "state": "done"} if extraction == "rules" else
                               {"mode": "llm", "model": extraction_model.strip(), "state": "queued", "done": 0, "total": 0, "errors": []}}
        with self.connect() as db:
            db.execute("INSERT INTO drafts VALUES (?, ?)", (draft["id"], canonical(draft)))
        return draft

    def discard(self, draft_id):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            draft = self._draft(db, draft_id)
            if draft["status"] != "draft":
                raise ValueError("Chỉ hủy được bản nháp đang chờ duyệt")
            draft["status"] = "discarded"
            db.execute("UPDATE drafts SET body=? WHERE id=?", (canonical(draft), draft_id))

    # AI extraction lifecycle -----------------------------------------------------

    def _save_draft(self, db, draft):
        db.execute("UPDATE drafts SET body=? WHERE id=?", (canonical(draft), draft["id"]))

    def _rebuild(self, draft, claims, evidence):
        """Replace the draft's machine claims; source units, references and the rule report stay."""
        documents, units, _, _ = graph_parts(draft["graph"])
        graph = make_graph(documents, units, list(evidence.values()), claims,
                           extraction_report=draft["graph"]["extraction_report"])
        draft["graph"] = graph
        draft["suggestions"] = entity_suggestions(graph, draft["existing_entities"])

    def start_extraction(self, draft_id):
        """Mark an AI extraction as running and return its input: units plus sentences rules did not structure."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            draft = self._draft(db, draft_id)
            job = draft.get("extraction") or {}
            if draft["status"] != "draft" or job.get("mode") != "llm":
                raise ValueError("Bản nháp không dùng cách tách bằng AI")
            if job.get("state") == "running":
                raise ValueError("Đang tách quy phạm bằng AI")
            if db.execute("SELECT 1 FROM review_decisions WHERE draft_id=? LIMIT 1", (draft_id,)).fetchone():
                raise ValueError("Bản nháp đã có quyết định duyệt; không chạy lại tách bằng AI")
            _, units, _, _ = graph_parts(draft["graph"])
            targets = [{"unit_version_id": row["unit_version_id"], **sentence}
                       for row in draft["graph"]["extraction_report"] if "unit_version_id" in row
                       for sentence in row.get("cue_sentences", []) + row.get("unparsed_sentences", [])]
            draft["extraction"] = {**job, "state": "running", "done": 0, "total": 0, "errors": [], "started_at": now()}
            self._save_draft(db, draft)
        return units, targets

    def extraction_progress(self, draft_id, done, total):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            draft = self._draft(db, draft_id)
            if draft.get("extraction", {}).get("state") == "running":
                draft["extraction"].update(done=done, total=total)
                self._save_draft(db, draft)

    def finish_extraction(self, draft_id, claims, evidence, reports, errors):
        """Replace cue-sentence candidates by verified AI claims for the sentences the model covered."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            draft = self._draft(db, draft_id)
            job = draft.get("extraction") or {}
            if draft["status"] != "draft" or job.get("state") != "running":
                return
            _, _, old_evidence, old_claims = graph_parts(draft["graph"])
            covered = {(r["unit_version_id"], r["start"], r["end"]) for r in reports if r.get("status") == "norms"}
            kept = []
            for claim in old_claims:
                anchor = sentence_anchor(claim, old_evidence)
                if claim_origin(claim["extraction_run_id"]) == "cue" and anchor and (anchor["unit_version_id"], anchor["start"], anchor["end"]) in covered:
                    continue
                kept.append(claim)
            merged = {**old_evidence, **{row["evidence_id"]: row for row in evidence}}
            self._rebuild(draft, kept + list(claims), merged)
            failed = sum(1 for r in reports if r.get("status") == "failed")
            state = "failed" if reports and failed == len(reports) else "partial" if errors else "done"
            draft["extraction"] = {**job, "state": state, "errors": sorted(set(errors)), "sentences": reports,
                                   "ai_claims": len(claims), "checked": len(reports), "finished_at": now()}
            self._save_draft(db, draft)

    def fail_extraction(self, draft_id, code):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            draft = self._draft(db, draft_id)
            if draft.get("extraction", {}).get("state") in EXTRACTION_BUSY:
                draft["extraction"].update(state="failed", errors=[code], finished_at=now())
                self._save_draft(db, draft)

    def interrupt_extractions(self):
        """After a restart no job is alive: unblock drafts and keep their rule results."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            for (body,) in db.execute("SELECT body FROM drafts").fetchall():
                draft = json.loads(body)
                if draft["status"] == "draft" and draft.get("extraction", {}).get("state") in EXTRACTION_BUSY:
                    draft["extraction"].update(state="interrupted")
                    self._save_draft(db, draft)

    # Review ---------------------------------------------------------------------

    def review(self, draft_id, item_id, decision, payload=None):
        """Save one review decision (or one batch) immediately so review can stop and resume."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            draft = self._draft(db, draft_id)
            if draft["status"] != "draft":
                raise ValueError("Bản nháp không còn ở trạng thái chờ duyệt")
            if draft.get("extraction", {}).get("state") in EXTRACTION_BUSY:
                raise ValueError("Đang tách quy phạm bằng AI; đợi hoàn tất rồi duyệt")
            graph = draft["graph"]
            nodes = {n["id"]: n for n in graph["nodes"]}
            saved = self._decisions(db, draft_id)
            stamp = now()

            def put(key, body):
                db.execute("INSERT OR REPLACE INTO review_decisions VALUES (?, ?, ?)", (draft_id, key, canonical({**body, "decided_at": stamp})))

            if decision == "approve_article":
                article = (payload or {}).get("article_id")
                units = self._units(graph)
                if article not in units or units[article]["unit_type"] != "article":
                    raise ValueError("Không tìm thấy Điều cần duyệt")
                for node in graph["nodes"]:
                    if node["kind"] == "NormClaim" and node["id"] not in saved and self._article_of(units, self._unit_by_version(units, node["payload"]["source_unit_version_ids"][0])) == article:
                        put(node["id"], {"decision": "approve", "decision_mode": "batch"})
            elif decision == "no_norm_article":
                article = (payload or {}).get("article_id")
                units = self._units(graph)
                if article not in units or units[article]["unit_type"] != "article":
                    raise ValueError("Không tìm thấy Điều")
                for gap in coverage_gaps(graph):
                    if gap["id"] not in saved and self._article_of(units, units[gap["unit_id"]]) == article:
                        put(gap["id"], {"decision": "no_norm", "decision_mode": "batch"})
            elif decision == "add_claim":
                self._add_claim(db, draft, payload or {})
            elif isinstance(item_id, str) and item_id.startswith("gap:"):
                if item_id not in {g["id"] for g in coverage_gaps(graph)} and item_id not in saved:
                    raise ValueError("Đoạn này đã có quy phạm")
                if decision == "no_norm":
                    put(item_id, {"decision": "no_norm", "decision_mode": "single"})
                elif decision == "clear":
                    db.execute("DELETE FROM review_decisions WHERE draft_id=? AND item_id=?", (draft_id, item_id))
                else:
                    raise ValueError("Quyết định không hợp lệ cho đoạn chưa có quy phạm")
            elif item_id in nodes and nodes[item_id]["kind"] == "NormClaim" and decision == "remove_claim":
                if claim_origin(nodes[item_id]["payload"]["extraction_run_id"]) != "manual":
                    raise ValueError("Chỉ xóa được quy phạm do người duyệt thêm; quy phạm máy tách hãy chọn Loại")
                _, _, evidence, claims = graph_parts(graph)
                self._rebuild(draft, [c for c in claims if "claim:" + digest(canonical([c["extraction_run_id"], c["claim_id"]])) != item_id], evidence)
                db.execute("DELETE FROM review_decisions WHERE draft_id=? AND (item_id=? OR item_id LIKE ?)", (draft_id, item_id, item_id + "/%"))
                self._save_draft(db, draft)
            elif item_id in nodes and nodes[item_id]["kind"] == "NormClaim":
                current = saved.get(item_id, {})
                if decision == "clear":
                    db.execute("DELETE FROM review_decisions WHERE draft_id=? AND item_id=?", (draft_id, item_id))
                elif decision in {"approve", "reject"}:
                    put(item_id, {**current, "decision": decision, "decision_mode": "single"})
                elif decision == "edit":
                    body = self._apply_edit(graph, nodes[item_id], current, payload or {}, stamp)
                    put(item_id, body)
                    # A link decided on the old slot text is no longer reviewed for the new text.
                    field = (payload or {}).get("slot")
                    if field:
                        db.execute("DELETE FROM review_decisions WHERE draft_id=? AND item_id=?", (draft_id, item_id + "/slot/" + field))
                else:
                    raise ValueError("Quyết định không hợp lệ cho quy phạm")
            elif item_id in nodes and nodes[item_id]["kind"] in KINDS:
                if decision == "clear":
                    db.execute("DELETE FROM review_decisions WHERE draft_id=? AND item_id=?", (draft_id, item_id))
                elif decision == "no_link":
                    put(item_id, {"decision": "no_link"})
                elif decision == "link":
                    target = (payload or {}).get("target")
                    allowed = {e["id"] for e in draft["existing_entities"] if e["kind"] == nodes[item_id]["kind"]}
                    if target not in allowed:
                        raise ValueError("Chỉ liên kết với thực thể cùng loại trong kho đích")
                    put(item_id, {"decision": "link", "target": target})
                else:
                    raise ValueError("Quyết định không hợp lệ cho thực thể")
            else:
                raise ValueError("Không tìm thấy mục cần duyệt trong bản nháp")
        return self.draft_view(draft_id)

    def _add_claim(self, db, draft, payload):
        """A reviewer-created claim anchored to an exact sentence; its slots are then filled with Sửa."""
        _, units, evidence, claims = graph_parts(draft["graph"])
        leaves = {u["unit_version_id"]: u for u in leaf_units(units)}
        version, start, end = payload.get("unit_version_id"), payload.get("start"), payload.get("end")
        unit = leaves.get(version)
        if unit is None:
            raise ValueError("Chỉ thêm quy phạm từ một khoản hoặc điểm không có đơn vị con")
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(unit["text"]):
            raise ValueError("Vị trí câu trích không hợp lệ")
        quote = unit["text"][start:end]
        if not quote.strip() or quote != quote.strip():
            raise ValueError("Câu trích không được rỗng hoặc bắt đầu/kết thúc bằng khoảng trắng")
        builder = ClaimBuilder(units)
        claim = builder.build(unit, (start, end), {}, "unknown", None, run=MANUAL_RUN, rule="reviewer")
        claim["extraction_scope"] = "reviewer-selected source sentence; slots added by the reviewer as exact quotes"
        if any(c["claim_id"] == claim["claim_id"] for c in claims):
            raise ValueError("Đã có quy phạm thêm thủ công cho đúng đoạn này")
        self._rebuild(draft, claims + [claim], {**evidence, **builder.evidence})
        self._save_draft(db, draft)

    @staticmethod
    def _units(graph):
        return {n["payload"]["unit_id"]: n["payload"] for n in graph["nodes"] if n["kind"] == "LegalUnit"}

    @staticmethod
    def _unit_by_version(units, version):
        return next((u for u in units.values() if u["unit_version_id"] == version), None)

    @staticmethod
    def _article_of(units, unit):
        while unit is not None and unit["unit_type"] != "article" and unit["parent_id"]:
            unit = units.get(unit["parent_id"])
        return unit["unit_id"] if unit is not None else None

    def _apply_edit(self, graph, node, current, payload, stamp):
        machine = machine_claim(node["payload"])
        field = payload.get("field")
        if field == "restore":
            return {"decision": current.get("decision", "approve"), "decision_mode": "single"}
        curated = deepcopy(current.get("curated") or machine)
        new_evidence = dict(current.get("new_evidence") or {})
        edits = list(current.get("edits") or [])
        note = current.get("reviewer_note")
        units = self._units(graph)
        allowed = set(machine["source_unit_version_ids"])
        for version in machine["source_unit_version_ids"]:
            unit = self._unit_by_version(units, version)
            while unit is not None and unit["parent_id"]:
                unit = units.get(unit["parent_id"])
                if unit is not None:
                    allowed.add(unit["unit_version_id"])

        def anchor():
            version, start, end = payload.get("unit_version_id"), payload.get("start"), payload.get("end")
            if version not in allowed:
                raise ValueError("Chỉ chọn câu trích trong đơn vị nguồn của quy phạm hoặc đơn vị cha")
            unit = self._unit_by_version(units, version)
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(unit["text"]):
                raise ValueError("Vị trí câu trích không hợp lệ")
            quote = unit["text"][start:end]
            if not quote.strip() or quote != quote.strip():
                raise ValueError("Câu trích không được rỗng hoặc bắt đầu/kết thúc bằng khoảng trắng")
            row = {"evidence_id": digest(canonical([version, start, quote])), "document_id": unit["document_id"],
                   "unit_id": unit["unit_id"], "unit_version_id": version, "quote": quote, "start": start, "end": end,
                   "normalized_sha256": unit["normalized_sha256"]}
            errors = check_evidence(row, list(units.values()))
            if errors:
                raise ValueError("Câu trích không khớp nguồn: " + ", ".join(errors))
            new_evidence[row["evidence_id"]] = row
            return row

        if field == "slot":
            name, state = payload.get("slot"), payload.get("state")
            if name not in SLOTS:
                raise ValueError("Thành phần quy phạm không hợp lệ")
            before = curated["slots"].get(name, {"state": "unknown", "text": None, "evidence_ids": []})
            if state == "present":
                row = anchor()
                after = {"state": "present", "text": row["quote"], "evidence_ids": [row["evidence_id"]]}
                curated["evidence_ids"] = sorted(set(curated["evidence_ids"]) | {row["evidence_id"]})
            elif state in {"unknown", "not_present"}:
                after = {"state": state, "text": None, "evidence_ids": []}
            else:
                raise ValueError("Trạng thái thành phần không hợp lệ")
            curated["slots"][name] = after
            edits.append({"field": "slot", "slot": name, "before": before.get("text"), "after": after["text"], "state": state, "at": stamp})
        elif field == "modality":
            value = payload.get("modality")
            if value not in MODALITIES:
                raise ValueError("Loại quy phạm không hợp lệ")
            before = curated["modality"]
            if value == "unknown":
                curated["modality_evidence_ids"] = []
            else:
                row = anchor()
                curated["modality_evidence_ids"] = [row["evidence_id"]]
                curated["evidence_ids"] = sorted(set(curated["evidence_ids"]) | {row["evidence_id"]})
            curated["modality"] = value
            edits.append({"field": "modality", "before": before, "after": value, "at": stamp})
        elif field == "note":
            text = payload.get("text")
            if not isinstance(text, str) or len(text) > 1000:
                raise ValueError("Ghi chú tối đa 1000 ký tự")
            note = text.strip() or None
        else:
            raise ValueError("Kiểu chỉnh sửa không hợp lệ")
        validate_claim(curated)
        body = {"decision": "approve", "decision_mode": "single"}
        if curated != machine:
            body.update(curated=curated, new_evidence=new_evidence, edits=edits)
        if note:
            body["reviewer_note"] = note
        return body

    def draft_view(self, draft_id):
        with self.connect() as db:
            draft = self._draft(db, draft_id)
            saved = self._decisions(db, draft_id)
            base = self.revision(draft["base_revision"]) if draft["base_revision"] else None
            kb = self._kb(db, draft["kb_id"], active=False) if draft.get("kb_id") else None
        graph = draft["graph"]
        units = self._units(graph)
        base_graph = base["graph"] if base else empty_graph()
        base_quotes = {}
        for n in base_graph["nodes"]:
            if is_approved(n):
                anchor = primary_quote(base_graph["nodes"], n["payload"])
                if anchor:
                    base_quotes[label_key(anchor["quote"])] = n["id"]
        order = {u["unit_id"]: (u["source_start"], i) for i, u in enumerate(units.values())}
        evidence = {n["payload"]["evidence_id"]: n["payload"] for n in graph["nodes"] if n["kind"] == "Evidence"}
        job = draft.get("extraction") or {"mode": "rules", "state": "done"}
        ai_verdicts = {(r["unit_version_id"], r["start"], r["end"]): r for r in job.get("sentences", [])}
        claims = []
        for node in graph["nodes"]:
            if node["kind"] != "NormClaim":
                continue
            decision = saved.get(node["id"], {})
            effective = decision.get("curated") or machine_claim(node["payload"])
            unit = self._unit_by_version(units, effective["source_unit_version_ids"][0])
            anchor = primary_quote(graph["nodes"], node["payload"])
            slots = {}
            for name, slot in effective["slots"].items():
                rows = [evidence.get(e) or (decision.get("new_evidence") or {}).get(e) for e in slot["evidence_ids"]]
                slots[name] = {**slot, "evidence": [r for r in rows if r]}
            reasons = []
            incomplete = any(effective["slots"].get(k, {}).get("state") == "unknown" for k in ("actor", "action"))
            if incomplete:
                reasons.append("Chưa tách đủ chủ thể, hành vi hoặc loại quy phạm; bổ sung bằng Sửa hoặc Loại nếu không phải quy phạm")
            elif effective["modality"] in {"permission", "unknown"}:
                reasons.append("Loại quy phạm cần xác nhận")
            if anchor and ("không" in anchor["quote"].casefold().split() or "trừ" in anchor["quote"].casefold().split()):
                reasons.append("Có phủ định hoặc ngoại lệ")
            duplicate = bool(anchor and label_key(anchor["quote"]) in base_quotes)
            if duplicate:
                reasons.append("Trùng nội dung với quy phạm đã có trong kho")
            origin = claim_origin(node["payload"]["extraction_run_id"])
            sentence = sentence_anchor(machine_claim(node["payload"]), evidence)
            verdict = ai_verdicts.get((sentence["unit_version_id"], sentence["start"], sentence["end"])) if sentence else None
            ai_note = None
            if verdict and origin == "cue":
                ai_note = {"no_norm": "AI cho rằng câu này không nêu quy phạm.",
                           "rejected": "AI đề xuất quy phạm nhưng không khớp nguyên văn nên bị bỏ.",
                           "failed": "AI chưa xử lý được câu này."}.get(verdict["status"])
            claims.append({"id": node["id"], "label": node["label"], "unit_id": unit["unit_id"] if unit else None,
                           "origin": origin, "ai_note": ai_note,
                           "article_id": self._article_of(units, unit), "modality": effective["modality"],
                           "modality_evidence": [evidence.get(e) or (decision.get("new_evidence") or {}).get(e) for e in effective.get("modality_evidence_ids", [])],
                           "slots": slots, "quote": anchor, "decision": decision.get("decision"),
                           "decision_mode": decision.get("decision_mode"), "edited": "curated" in decision,
                           "edits": decision.get("edits", []), "reviewer_note": decision.get("reviewer_note"),
                           "duplicate": duplicate, "priority": len(reasons), "reasons": reasons,
                           "source_unit_version_ids": effective["source_unit_version_ids"]})
        # Document order keeps a claim in place while it is edited; priority is shown as an attention marker.
        claims.sort(key=lambda c: (order.get(c["unit_id"], (0, 0)), (c["quote"] or {}).get("start", 0), c["id"]))
        claim_by_id = {c["id"]: c for c in claims}
        base_nodes = {n["id"]: n for n in base_graph["nodes"]}

        def quote_of(graph_nodes, ids):
            rows = {n["payload"]["evidence_id"]: n["payload"]["quote"] for n in graph_nodes if n["kind"] == "Evidence"}
            return next((rows[e] for e in ids if e in rows), None)

        def base_context(target):
            owner = base_nodes.get(target.split("/slot/")[0])
            anchor = primary_quote(base_graph["nodes"], owner["payload"]) if owner and owner["kind"] == "NormClaim" else None
            return anchor["quote"] if anchor else None

        entities = []
        for node in graph["nodes"]:
            if node["kind"] not in KINDS:
                continue
            owner = node["id"].split("/slot/")[0]
            decision = saved.get(node["id"], {})
            entities.append({"id": node["id"], "kind": node["kind"], "label": node["label"], "claim_id": owner,
                             "claim_decision": claim_by_id.get(owner, {}).get("decision"),
                             "quote": quote_of(graph["nodes"], node["payload"]["evidence_ids"]),
                             "context": (claim_by_id.get(owner, {}).get("quote") or {}).get("quote"),
                             "decision": decision.get("decision"), "target": decision.get("target"),
                             "suggestions": [{"id": t, "label": base_nodes[t]["label"], "quote": quote_of(base_graph["nodes"], base_nodes[t]["payload"]["evidence_ids"]),
                                              "context": base_context(t)}
                                             for t in draft["suggestions"].get(node["id"], []) if t in base_nodes]})
        articles = []
        for unit in sorted(units.values(), key=lambda u: order[u["unit_id"]]):
            article = self._article_of(units, unit)
            if not articles or articles[-1]["id"] != article:
                head = units[article]
                articles.append({"id": article, "label": head["text"].splitlines()[0], "units": []})
            articles[-1]["units"].append({k: unit[k] for k in ("unit_id", "unit_version_id", "unit_type", "label", "text")})
        gaps = []
        for gap in coverage_gaps(graph):
            verdict = ai_verdicts.get((gap["unit_version_id"], gap["start"], gap["end"]))
            gaps.append({**gap, "article_id": self._article_of(units, units[gap["unit_id"]]),
                         "decision": saved.get(gap["id"], {}).get("decision"),
                         "ai_note": {"no_norm": "AI cũng không thấy quy phạm trong câu này.",
                                     "rejected": "AI đề xuất quy phạm nhưng không khớp nguyên văn nên bị bỏ.",
                                     "failed": "AI chưa xử lý được câu này."}.get(verdict["status"]) if verdict else None})
        progress = Counter("edited" if c["edited"] else c["decision"] or "undecided" for c in claims)
        approved = [c for c in claims if c["decision"] == "approve"]
        document = next(n["payload"] for n in graph["nodes"] if n["kind"] == "Document")
        possible_versions = [n["payload"]["title"] for n in base_graph["nodes"] if n["kind"] == "Document"
                             and label_key(n["payload"]["title"]) == label_key(document["title"])]
        linked = [e for e in entities if e["decision"] == "link" and claim_by_id.get(e["claim_id"], {}).get("decision") == "approve"]
        new_entities = [e for e in entities if claim_by_id.get(e["claim_id"], {}).get("decision") == "approve" and e["decision"] != "link"]
        base_approved = sum(1 for n in base_graph["nodes"] if is_approved(n))
        base_documents = sum(1 for n in base_graph["nodes"] if n["kind"] == "Document")
        warnings = []
        if possible_versions:
            warnings.append("Kho đích đã có tài liệu cùng tên nhưng khác nội dung; kiểm tra đây có phải phiên bản khác không.")
        if any(c["duplicate"] and c["decision"] == "approve" for c in claims):
            warnings.append("Một số quy phạm được duyệt trùng nội dung với quy phạm đã có trong kho.")
        unlinked = [e for e in new_entities if e["suggestions"] and e["decision"] is None]
        if unlinked:
            warnings.append(f"{len(unlinked)} thực thể có gợi ý trùng tên trong kho nhưng chưa được quyết định liên kết.")
        diff = {"documents_before": base_documents, "documents_after": base_documents + 1,
                "claims_before": base_approved, "claims_after": base_approved + len(approved),
                "approved": len(approved), "rejected": progress["reject"], "edited": progress["edited"],
                "undecided": progress["undecided"], "duplicates": sum(1 for c in approved if c["duplicate"]),
                "entities_new": len(new_entities), "entities_linked": len(linked), "warnings": warnings}
        return {"id": draft["id"], "title": draft["title"], "status": draft["status"], "created_at": draft["created_at"],
                "target": draft["target"], "kb": kb, "base_revision": draft["base_revision"],
                "published_revision": draft.get("published_revision"), "document": document,
                "articles": articles, "claims": claims, "entities": entities,
                "progress": {"total": len(claims), "approved": progress["approve"] + progress["edited"],
                             "rejected": progress["reject"], "edited": progress["edited"], "undecided": progress["undecided"],
                             "gaps": len(gaps), "gaps_open": sum(1 for g in gaps if not g["decision"])},
                "gaps": gaps, "extraction": {k: v for k, v in job.items() if k != "sentences"},
                "diff": diff, "unassigned_text": draft["unassigned_text"], "parser_audit": draft["parser_audit"],
                "extraction_report": graph["extraction_report"]}

    # Publish ---------------------------------------------------------------------

    @staticmethod
    def _final_graph(draft, curated):
        """Rebuild the draft graph with curated claims; uncurated drafts are used unchanged."""
        graph = draft["graph"]
        if not curated:
            return graph, {}
        nodes = graph["nodes"]
        documents = [n["payload"] for n in nodes if n["kind"] == "Document"]
        units = [n["payload"] for n in nodes if n["kind"] == "LegalUnit"]
        evidence = {n["payload"]["evidence_id"]: n["payload"] for n in nodes if n["kind"] == "Evidence"}
        claims, renamed = [], {}
        for node in nodes:
            if node["kind"] != "NormClaim":
                continue
            machine = machine_claim(node["payload"])
            if node["id"] in curated:
                body = curated[node["id"]]
                claim = deepcopy(body["curated"])
                claim["claim_id"] = digest(canonical([machine["claim_id"], claim]))
                evidence.update(body.get("new_evidence") or {})
                renamed[node["id"]] = "claim:" + digest(canonical([claim["extraction_run_id"], claim["claim_id"]]))
                claims.append(claim)
            else:
                claims.append(machine)
        return make_graph(documents, units, list(evidence.values()), claims, extraction_report=graph["extraction_report"]), renamed

    def publish(self, draft_id, reviewer, reason, *, decisions=None, links=None):
        if not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer) > 200:
            raise ValueError("Cần tên người duyệt (tối đa 200 ký tự)")
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
            raise ValueError("Cần lý do duyệt (tối đa 2000 ký tự)")
        if not isinstance(decisions or {}, dict) or not isinstance(links or {}, dict):
            raise ValueError("Invalid review decisions")
        reviewer, reason = reviewer.strip(), reason.strip()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            draft = self._draft(db, draft_id)
            if draft["status"] != "draft":
                raise ValueError("Bản nháp đã được công bố hoặc đã hủy; không thể công bố lần nữa")
            if draft.get("extraction", {}).get("state") in EXTRACTION_BUSY:
                raise ValueError("Đang tách quy phạm bằng AI; đợi hoàn tất rồi duyệt")
            target = draft["target"]
            if target["mode"] == "merge":
                self._kb(db, target["kb_id"])
                base = self._current(db, target["kb_id"])
                if draft["base_revision"] != base["id"]:
                    raise Conflict("Kho đã có revision mới kể từ khi tạo bản nháp. Nhập lại tài liệu để đối chiếu trên revision mới")
                base_graph = base["graph"]
            else:
                self._check_name(db, target["name"])
                base, base_graph = None, empty_graph()
            saved = self._decisions(db, draft_id)
            graph = draft["graph"]
            claim_ids = {n["id"] for n in graph["nodes"] if n["kind"] == "NormClaim"}
            effective = {k: v["decision"] for k, v in saved.items() if k in claim_ids and "decision" in v}
            effective.update(decisions or {})
            if set(effective) != claim_ids or any(v not in ("approve", "reject") for v in effective.values()):
                raise ValueError("Phải duyệt hoặc loại từng quy phạm trước khi công bố")
            open_gaps = [g for g in coverage_gaps(graph) if saved.get(g["id"], {}).get("decision") != "no_norm"]
            if open_gaps:
                raise ValueError(f"Còn {len(open_gaps)} đoạn chưa có quy phạm: thêm quy phạm hoặc đánh dấu không phải quy phạm trước khi công bố")
            approved = {key for key, value in effective.items() if value == "approve"}
            if not approved:
                raise ValueError("Chưa duyệt quy phạm nào; kho chưa thay đổi")
            entity_ids = {n["id"] for n in graph["nodes"] if n["kind"] in KINDS}
            stored_links = {k: v["target"] for k, v in saved.items() if k in entity_ids and v.get("decision") == "link"
                            and k.split("/slot/")[0] in approved}
            curated = {k: v for k, v in saved.items() if k in approved and "curated" in v}
            final, renamed = self._final_graph(draft, curated)

            def rename(node_id):
                for old, new in renamed.items():
                    if node_id == old or node_id.startswith(old + "/"):
                        return new + node_id[len(old):]
                return node_id

            approved_final = {rename(k) for k in approved}
            all_links = {**{rename(k): v for k, v in stored_links.items()}, **{rename(k): v for k, v in (links or {}).items()}}
            # Keep source structure/evidence, but never rejected claims or their semantic slots.
            kept = {n["id"]: deepcopy(n) for n in final["nodes"]
                    if n["kind"] in {"Document", "LegalUnit", "Evidence", "ReferenceMention"}
                    or n["id"] in approved_final or any(n["id"].startswith(c + "/") for c in approved_final)}
            base_nodes = {n["id"]: n for n in base_graph["nodes"]}
            for source, target_id in all_links.items():
                if source not in kept or kept[source]["kind"] not in KINDS or target_id not in base_nodes or base_nodes[target_id]["kind"] != kept[source]["kind"]:
                    raise ValueError("Liên kết thực thể phải nối ứng viên đã duyệt với thực thể cùng loại trong kho đích")
            original = {rename(k): k for k in approved}
            for key in approved_final:
                source = original[key]
                record = saved.get(source, {})
                kept[key]["payload"]["human_review"] = {"decision": "approved", "reviewer": reviewer, "reviewed_at": now(),
                                                        "reason": reason, "decision_mode": record.get("decision_mode", "single"),
                                                        "edited": source in curated}
                if source in curated or record.get("reviewer_note"):
                    kept[key]["payload"]["curation"] = {"derived_from": source, "edits": record.get("edits", []),
                                                        "reviewer_note": record.get("reviewer_note")}
            nodes = deepcopy(base_nodes)
            for key, node in kept.items():
                if key in nodes and nodes[key] != node:
                    raise ValueError("Graph identity collision")
                nodes[key] = node
            edges = {e["id"]: deepcopy(e) for e in base_graph["edges"]}
            for edge in final["edges"]:
                if edge["source"] in kept and edge["target"] in kept:
                    edges[edge["id"]] = edge
            for source, target_id in all_links.items():
                proof = sorted(set(kept[source]["payload"]["evidence_ids"] + base_nodes[target_id]["payload"]["evidence_ids"]))
                edge_id = digest(canonical(["REVIEWED_ENTITY_LINK", source, target_id, proof]))
                edges[edge_id] = {"id": edge_id, "kind": "REVIEWED_ENTITY_LINK", "source": source, "target": target_id,
                                  "evidence_ids": proof, "reviewer": reviewer, "reason": reason,
                                  "note": "Human identity decision; quotes support mentions, not identity inference"}
            merged = finish_graph(nodes, edges, base_graph["references"] + final["references"],
                                  base_graph["extraction_report"] + final["extraction_report"])
            if target["mode"] == "new":
                kb_id = self._insert_kb(db, target["name"], target["description"], target["data_class"])["id"]
            else:
                kb_id = target["kb_id"]
            review = {"draft_id": draft_id, "decisions": effective, "entity_links": all_links,
                      "dismissed_gaps": sorted(k for k, v in saved.items() if k.startswith("gap:") and v.get("decision") == "no_norm"),
                      "extraction": {k: v for k, v in (draft.get("extraction") or {}).items() if k != "sentences"},
                      "edited_claims": sorted(rename(k) for k in curated), "raw_sha256": digest(draft["raw_text"]),
                      "legal_status": "unknown"}
            revision = self._insert_revision(db, kb_id, base["id"] if base else None, merged, reviewer, reason, review)
            draft.update(status="merged", published_revision=revision["id"], kb_id=kb_id)
            db.execute("UPDATE drafts SET body=? WHERE id=?", (canonical(draft), draft_id))
        return revision
