"""Offline TXT extraction and explicitly reviewed, immutable graph revisions."""

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
from legal_ai.ingestion.parser import parse
from legal_ai.kb.graph import GRAPH_VERSION, make_graph
from legal_ai.normalization.text import normalize
from legal_ai.schemas.contract import VERSION

MAX_BYTES = 1_000_000
KINDS = {"Entity", "LegalConcept"}


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
        "reference_status": dict(Counter(r["status"] for r in references)),
        "synthetic": any(n["payload"]["synthetic"] for n in nodes.values() if n["kind"] == "Document"),
        "legal_status": "unknown"}}


class ReviewStore:
    def __init__(self, path, seed=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS revisions (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS drafts (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            if not db.execute("SELECT 1 FROM revisions LIMIT 1").fetchone():
                graph = json.loads(Path(seed).read_text(encoding="utf-8")) if seed else finish_graph({}, {}, [], [])
                if graph.get("graph_version") != GRAPH_VERSION:
                    raise ValueError("Seed graph version is unsupported")
                revision = {"schema_version": "import-review-v1", "id": uuid4().hex,
                            "parent": None, "created_at": now(), "reviewer": None,
                            "reason": "Initial review graph; existing candidates remain unverified",
                            "graph": graph, "review": None}
                db.execute("INSERT INTO revisions VALUES (?, ?)", (revision["id"], canonical(revision)))

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def current(self, db=None):
        if db is None:
            with self.connect() as connection:
                return self.current(connection)
        return json.loads(db.execute("SELECT body FROM revisions ORDER BY rowid DESC LIMIT 1").fetchone()[0])

    def revision(self, revision_id):
        with self.connect() as db:
            row = db.execute("SELECT body FROM revisions WHERE id=?", (revision_id,)).fetchone()
        if row is None:
            raise ValueError("Revision not found")
        return json.loads(row[0])

    def draft(self, draft_id, db=None):
        if db is None:
            with self.connect() as connection:
                return self.draft(draft_id, connection)
        row = db.execute("SELECT body FROM drafts WHERE id=?", (draft_id,)).fetchone()
        if row is None:
            raise ValueError("Draft not found")
        return json.loads(row[0])

    def state(self):
        with self.connect() as db:
            revisions = [json.loads(row[0]) for row in db.execute("SELECT body FROM revisions ORDER BY rowid DESC")]
            drafts = [json.loads(row[0]) for row in db.execute("SELECT body FROM drafts ORDER BY rowid DESC")]
        return {"schema_version": "import-review-v1", "current_revision": revisions[0]["id"],
                "summary": revisions[0]["graph"]["summary"],
                "revisions": [{k: r[k] for k in ("id", "parent", "created_at", "reviewer", "reason")} for r in revisions],
                "drafts": [{k: d[k] for k in ("id", "title", "base_revision", "created_at", "status")} for d in drafts]}

    def prepare(self, title, text, synthetic=False, source_url=None):
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
        normalized = normalize(text.lstrip("\ufeff"), "upload/source.txt")
        version = normalized["normalized_sha256"]
        document_id = "upload-" + version
        base = self.current()
        if any(n["kind"] == "Document" and n["payload"]["document_id"] == document_id for n in base["graph"]["nodes"]):
            raise ValueError("Tài liệu này đã có trong revision hiện tại; không nhập trùng")
        parsed = parse(normalized, document_id, version)
        if not parsed["units"]:
            raise ValueError("Chưa nhận diện được cấu trúc. TXT cần tiêu đề như ‘Điều 1. …’ trên một dòng riêng")
        # Reject malformed structure rather than publishing an incomplete source map.
        if any(a["code"] in {"orphan_heading", "duplicate_heading"} for a in parsed["audit"]):
            raise ValueError("Cấu trúc có heading trùng hoặc khoản/điểm thiếu cha; sửa TXT rồi nhập lại")
        document = {"schema_version": VERSION, "document_id": document_id, "document_version_id": version,
                    "snapshot_id": digest(text), "title": title.strip(), "source_url": source_url or "upload://" + document_id,
                    "accessed_at": now(), "source_sha256": digest(text), "effective_from": None,
                    "effective_to": None, "legal_status": "unknown", "synthetic": synthetic}
        graph = make_graph([document], parsed["units"], [], [], include_candidates=True, extraction_mode="norm-rules-v1")
        existing = [n for n in base["graph"]["nodes"] if n["kind"] in KINDS]
        suggestions = {n["id"]: [e["id"] for e in existing if e["kind"] == n["kind"] and label_key(e["label"]) == label_key(n["label"])]
                       for n in graph["nodes"] if n["kind"] in KINDS}
        draft = {"schema_version": "import-review-v1", "id": uuid4().hex, "title": title.strip(),
                 "base_revision": base["id"], "created_at": now(), "status": "draft", "raw_text": text,
                 "normalized": normalized, "parser_audit": parsed["audit"], "unassigned_text": parsed["unassigned_text"],
                 "graph": graph, "suggestions": suggestions,
                 "existing_entities": [{k: n[k] for k in ("id", "kind", "label")} for n in existing]}
        with self.connect() as db:
            db.execute("INSERT INTO drafts VALUES (?, ?)", (draft["id"], canonical(draft)))
        return draft

    def publish(self, draft_id, decisions, links, reviewer, reason):
        if not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer) > 200:
            raise ValueError("Cần tên người duyệt (tối đa 200 ký tự)")
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
            raise ValueError("Cần lý do duyệt (tối đa 2000 ký tự)")
        if not isinstance(decisions, dict) or not isinstance(links, dict):
            raise ValueError("Invalid review decisions")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            draft = self.draft(draft_id, db)
            base = self.current(db)
            if draft["status"] != "draft":
                raise ValueError("Draft đã được gộp; không thể publish lần hai")
            if draft["base_revision"] != base["id"]:
                raise ValueError("KB đã đổi revision. Nhập lại tài liệu để đối chiếu trên revision mới")
            graph = draft["graph"]
            claims = {n["id"] for n in graph["nodes"] if n["kind"] == "NormClaim"}
            if set(decisions) != claims or any(v not in ("approve", "reject") for v in decisions.values()):
                raise ValueError("Phải duyệt hoặc loại từng ứng viên quy phạm")
            approved = {key for key, value in decisions.items() if value == "approve"}
            if not approved:
                raise ValueError("Chưa duyệt quy phạm nào; KB chưa thay đổi")
            # Keep source structure/evidence, but never rejected claims or their semantic slots.
            kept = {n["id"]: deepcopy(n) for n in graph["nodes"]
                    if n["kind"] in {"Document", "LegalUnit", "Evidence", "ReferenceMention"}
                    or n["id"] in approved or any(n["id"].startswith(c + "/") for c in approved)}
            base_nodes = {n["id"]: n for n in base["graph"]["nodes"]}
            for source, target in links.items():
                if source not in kept or kept[source]["kind"] not in KINDS or target not in base_nodes or base_nodes[target]["kind"] != kept[source]["kind"]:
                    raise ValueError("Liên kết thực thể phải nối ứng viên đã duyệt với thực thể cùng loại trong KB hiện tại")
            for key in approved:
                kept[key]["payload"]["human_review"] = {"decision": "approved", "reviewer": reviewer.strip(), "reviewed_at": now(), "reason": reason.strip()}
            nodes = deepcopy(base_nodes)
            for key, node in kept.items():
                if key in nodes and nodes[key] != node:
                    raise ValueError("Graph identity collision")
                nodes[key] = node
            edges = {e["id"]: deepcopy(e) for e in base["graph"]["edges"]}
            for edge in graph["edges"]:
                if edge["source"] in kept and edge["target"] in kept:
                    edges[edge["id"]] = edge
            for source, target in links.items():
                proof = sorted(set(kept[source]["payload"]["evidence_ids"] + base_nodes[target]["payload"]["evidence_ids"]))
                edge_id = digest(canonical(["REVIEWED_ENTITY_LINK", source, target, proof]))
                edges[edge_id] = {"id": edge_id, "kind": "REVIEWED_ENTITY_LINK", "source": source, "target": target,
                                  "evidence_ids": proof, "reviewer": reviewer.strip(), "reason": reason.strip(),
                                  "note": "Human identity decision; quotes support mentions, not identity inference"}
            merged = finish_graph(nodes, edges, base["graph"]["references"] + graph["references"],
                                  base["graph"]["extraction_report"] + graph["extraction_report"])
            revision = {"schema_version": "import-review-v1", "id": uuid4().hex, "parent": base["id"],
                        "created_at": now(), "reviewer": reviewer.strip(), "reason": reason.strip(), "graph": merged,
                        "review": {"draft_id": draft_id, "decisions": decisions, "entity_links": links,
                                   "raw_sha256": digest(draft["raw_text"]), "legal_status": "unknown"}}
            db.execute("INSERT INTO revisions VALUES (?, ?)", (revision["id"], canonical(revision)))
            draft.update(status="merged", published_revision=revision["id"])
            db.execute("UPDATE drafts SET body=? WHERE id=?", (canonical(draft), draft_id))
        return revision
