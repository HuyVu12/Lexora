"""Research corpora for the DK1-DK4 experiments (`corpus-store-v1`), in the workspace SQLite file.

A corpus collects documents from vbpl.vn snapshots or uploaded files. Every added document is an immutable
row holding its source bytes, normalized text, parsed units and parser report; removing a document only hides
it from later versions. Freezing writes a numbered version that pins the exact document rows and their
hashes; question sets are annotated against a frozen version, and `export_version` writes it as a contract
bundle that `run-retrieval` reads. The contract keeps `legal_status = "unknown"`; the effect status vbpl.vn
reported at access time is kept in the document metadata and the version manifest.
"""

from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import secrets
import sqlite3
import threading

from legal_ai.common.io import canonical, digest, write_json, write_jsonl
from legal_ai.ingestion.catalog import fold
from legal_ai.ingestion.files import extract_text
from legal_ai.ingestion.parser import parse
from legal_ai.ingestion.vbpl_api import document_text, unwrap
from legal_ai.normalization.text import normalize
from legal_ai.schemas.contract import VERSION, validate_document, validate_unit
from legal_ai.validation.bundle import validate_bundle

STORE_VERSION = "corpus-store-v1"
MAX_DOCUMENTS = 200
_SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,79}")
SCHEMA = """
CREATE TABLE IF NOT EXISTS corpora (
  id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT NOT NULL, created_at TEXT NOT NULL, created_by TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS corpus_documents (
  id TEXT PRIMARY KEY, corpus_id TEXT NOT NULL REFERENCES corpora(id), document_id TEXT NOT NULL, title TEXT NOT NULL,
  source_kind TEXT NOT NULL, source_ref TEXT NOT NULL, source_url TEXT NOT NULL, source_sha256 TEXT NOT NULL, accessed_at TEXT NOT NULL,
  metadata TEXT NOT NULL, raw BLOB NOT NULL, normalized TEXT NOT NULL, units TEXT NOT NULL, report TEXT NOT NULL,
  added_at TEXT NOT NULL, added_by TEXT NOT NULL, removed_at TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS corpus_documents_live ON corpus_documents (corpus_id, document_id) WHERE removed_at IS NULL;
CREATE TABLE IF NOT EXISTS corpus_versions (
  id TEXT PRIMARY KEY, corpus_id TEXT NOT NULL REFERENCES corpora(id), number INTEGER NOT NULL, note TEXT NOT NULL,
  frozen_at TEXT NOT NULL, frozen_by TEXT NOT NULL, document_rows TEXT NOT NULL, manifest TEXT NOT NULL, UNIQUE (corpus_id, number));
"""


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slug(text):
    """A document ID candidate from a number or file name: `45/2019/QH14` -> `45-2019-qh14`."""
    value = re.sub(r"[^a-z0-9]+", "-", fold(text)).strip("-")[:80].strip("-")
    return value or "van-ban"


class CorpusStore:
    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.Lock()
        with closing(self._connect()) as db, db:
            db.executescript(SCHEMA)

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    # Corpora -------------------------------------------------------------------------
    def create(self, name, description, actor):
        name, description = (name or "").strip(), (description or "").strip()
        if not 1 <= len(name) <= 120 or len(description) > 2000:
            raise ValueError("corpus name needs 1-120 characters, description at most 2000")
        corpus_id = "c" + secrets.token_hex(6)
        with self._lock, closing(self._connect()) as db, db:
            if db.execute("SELECT 1 FROM corpora WHERE name = ?", (name,)).fetchone():
                raise ValueError("a corpus with this name exists")
            db.execute("INSERT INTO corpora VALUES (?,?,?,?,?)", (corpus_id, name, description, _now(), actor))
        return self.corpus(corpus_id)

    def corpora(self):
        with closing(self._connect()) as db:
            rows = db.execute("""SELECT c.*, (SELECT COUNT(*) FROM corpus_documents d WHERE d.corpus_id = c.id AND d.removed_at IS NULL) AS documents,
                                 (SELECT MAX(number) FROM corpus_versions v WHERE v.corpus_id = c.id) AS latest_version
                                 FROM corpora c ORDER BY c.created_at DESC, c.id""").fetchall()
        return [dict(row) for row in rows]

    def corpus(self, corpus_id):
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM corpora WHERE id = ?", (corpus_id,)).fetchone()
            if row is None:
                raise ValueError("corpus not found")
            documents = [self._summary(d) for d in db.execute(
                "SELECT * FROM corpus_documents WHERE corpus_id = ? AND removed_at IS NULL ORDER BY added_at, id", (corpus_id,))]
            versions = [self._version_summary(v) for v in db.execute(
                "SELECT * FROM corpus_versions WHERE corpus_id = ? ORDER BY number DESC", (corpus_id,))]
        return dict(row) | {"documents": documents, "versions": versions, "changed_since_version": self._changed(documents, versions)}

    @staticmethod
    def _changed(documents, versions):
        return not versions or sorted(d["id"] for d in documents) != sorted(versions[0]["document_rows"])

    @staticmethod
    def _summary(row):
        units = json.loads(row["units"])
        report = json.loads(row["report"])
        parents = {u["parent_id"] for u in units}
        return {"id": row["id"], "document_id": row["document_id"], "title": row["title"], "source_kind": row["source_kind"],
                "source_ref": row["source_ref"], "source_url": row["source_url"], "source_sha256": row["source_sha256"],
                "accessed_at": row["accessed_at"], "metadata": json.loads(row["metadata"]), "added_at": row["added_at"], "added_by": row["added_by"],
                "unit_count": len(units), "article_count": sum(u["unit_type"] == "article" for u in units),
                "leaf_count": sum(u["unit_id"] not in parents for u in units), "audit_count": len(report["audit"]),
                "unassigned_characters": len(report["unassigned_text"]), "warnings": report.get("warnings", [])}

    @staticmethod
    def _version_summary(row):
        manifest = json.loads(row["manifest"])
        return {"id": row["id"], "number": row["number"], "note": row["note"], "frozen_at": row["frozen_at"], "frozen_by": row["frozen_by"],
                "document_rows": json.loads(row["document_rows"]), "bundle_sha256": manifest["bundle_sha256"],
                "document_count": len(manifest["documents"]), "unit_count": manifest["unit_count"]}

    # Documents -----------------------------------------------------------------------
    def _add(self, corpus_id, document_id, title, kind, ref, url, raw, accessed_at, metadata, text, warnings, actor):
        document_id = document_id.strip().lower()
        if not _SLUG.fullmatch(document_id):
            raise ValueError("document ID: lowercase letters, digits and dashes, at most 80 characters")
        normalized = normalize(text, f"{document_id}/source.txt")
        parsed = parse(normalized, document_id, normalized["normalized_sha256"])
        if not any(u["unit_type"] == "article" for u in parsed["units"]):
            raise ValueError("no Điều found; check that each article starts on its own line with “Điều N.”")
        for unit in parsed["units"]:
            validate_unit(unit)
        report = {"audit": parsed["audit"], "unassigned_text": parsed["unassigned_text"], "warnings": warnings}
        row_id = "d" + secrets.token_hex(8)
        with self._lock, closing(self._connect()) as db, db:
            if db.execute("SELECT 1 FROM corpora WHERE id = ?", (corpus_id,)).fetchone() is None:
                raise ValueError("corpus not found")
            live = db.execute("SELECT document_id, source_sha256 FROM corpus_documents WHERE corpus_id = ? AND removed_at IS NULL", (corpus_id,)).fetchall()
            if any(r["document_id"] == document_id for r in live):
                raise ValueError(f"document ID {document_id} is already in this corpus; choose another")
            if any(r["source_sha256"] == digest(raw) for r in live):
                raise ValueError("this exact source is already in the corpus")
            if len(live) >= MAX_DOCUMENTS:
                raise ValueError(f"a corpus holds at most {MAX_DOCUMENTS} documents")
            db.execute("INSERT INTO corpus_documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                row_id, corpus_id, document_id, title, kind, ref, url, digest(raw), accessed_at, canonical(metadata), raw,
                canonical(normalized), canonical(parsed["units"]), canonical(report), _now(), actor, None))
        return self.document(row_id)

    def add_vbpl(self, corpus_id, manifest, raw, actor, document_id=None):
        """Add a vbpl.vn snapshot fetched by `vbpl_api.fetch_document` (its manifest and stored bytes)."""
        if digest(raw) != manifest["source_sha256"]:
            raise ValueError("snapshot bytes do not match their manifest")
        document = unwrap(raw)
        meta = manifest["metadata"]
        if meta.get("is_translation"):
            raise ValueError("this is a translation; add the Vietnamese original")
        text = document_text(document)["text"]
        return self._add(corpus_id, document_id or slug(meta.get("doc_num") or meta["vbpl_id"]), meta.get("title") or meta["vbpl_id"], "vbpl",
                         meta["vbpl_id"], manifest["site_url"], raw, manifest["accessed_at"], meta, text, [], actor)

    def add_file(self, corpus_id, filename, data, actor, title=None, document_id=None):
        extracted = extract_text(filename, data)
        name = Path(filename).name
        stem = Path(name).stem
        meta = {"filename": name, "format": extracted["format"]}
        return self._add(corpus_id, document_id or slug(stem), (title or stem).strip() or stem, "file", name, f"file:{name}", bytes(data),
                         _now(), meta, extracted["text"], extracted["warnings"], actor)

    def document(self, row_id):
        """A document with its parsed units and parser report, for review."""
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM corpus_documents WHERE id = ?", (row_id,)).fetchone()
        if row is None:
            raise ValueError("document not found")
        report = json.loads(row["report"])
        return self._summary(row) | {"corpus_id": row["corpus_id"], "removed_at": row["removed_at"], "units": json.loads(row["units"]),
                                     "audit": report["audit"], "unassigned_text": report["unassigned_text"]}

    def remove(self, corpus_id, row_id):
        with self._lock, closing(self._connect()) as db, db:
            changed = db.execute("UPDATE corpus_documents SET removed_at = ? WHERE id = ? AND corpus_id = ? AND removed_at IS NULL",
                                 (_now(), row_id, corpus_id)).rowcount
        if not changed:
            raise ValueError("document not found in this corpus")
        return self.corpus(corpus_id)

    # Versions ------------------------------------------------------------------------
    def _rows(self, db, ids):
        rows = {r["id"]: r for r in db.execute(f"SELECT * FROM corpus_documents WHERE id IN ({','.join('?' * len(ids))})", ids)}
        return [rows[i] for i in ids]

    @staticmethod
    def _contract(row):
        meta = json.loads(row["metadata"])
        normalized = json.loads(row["normalized"])
        document = {"schema_version": VERSION, "document_id": row["document_id"], "document_version_id": normalized["normalized_sha256"],
                    "snapshot_id": row["source_sha256"], "title": row["title"], "source_url": row["source_url"], "accessed_at": row["accessed_at"],
                    "source_sha256": row["source_sha256"], "effective_from": meta.get("effective_from"), "effective_to": meta.get("effective_to"),
                    "legal_status": "unknown", "synthetic": False}
        return validate_document(document), json.loads(row["units"]), normalized

    def freeze(self, corpus_id, note, actor):
        note = (note or "").strip()
        if len(note) > 500:
            raise ValueError("note at most 500 characters")
        with self._lock, closing(self._connect()) as db, db:
            if db.execute("SELECT 1 FROM corpora WHERE id = ?", (corpus_id,)).fetchone() is None:
                raise ValueError("corpus not found")
            ids = [r["id"] for r in db.execute("SELECT id FROM corpus_documents WHERE corpus_id = ? AND removed_at IS NULL ORDER BY document_id", (corpus_id,))]
            if not ids:
                raise ValueError("add at least one document before freezing")
            latest = db.execute("SELECT * FROM corpus_versions WHERE corpus_id = ? ORDER BY number DESC LIMIT 1", (corpus_id,)).fetchone()
            if latest and sorted(json.loads(latest["document_rows"])) == sorted(ids):
                raise ValueError(f"nothing changed since version {latest['number']}")
            documents, units = [], []
            entries = []
            for row in self._rows(db, ids):
                document, doc_units, normalized = self._contract(row)
                documents.append(document)
                units.extend(doc_units)
                entries.append({"document_id": row["document_id"], "row": row["id"], "title": row["title"], "source_kind": row["source_kind"],
                                "source_ref": row["source_ref"], "source_url": row["source_url"], "source_sha256": row["source_sha256"],
                                "accessed_at": row["accessed_at"], "normalized_sha256": normalized["normalized_sha256"],
                                "effect_status": json.loads(row["metadata"]).get("effect_status"), "units": len(doc_units),
                                "audit_count": len(json.loads(row["report"])["audit"])})
            validate_bundle(documents, units, [], [])
            number = (latest["number"] if latest else 0) + 1
            manifest = {"store_version": STORE_VERSION, "schema_version": VERSION, "corpus_id": corpus_id, "number": number,
                        "documents": entries, "unit_count": len(units),
                        "bundle_sha256": digest(canonical({"documents": documents, "units": units})),
                        "limitations": ["Parser audits need human review", "legal_status stays unknown in the contract; effect_status is what vbpl.vn reported at access time"]}
            version_id = "v" + secrets.token_hex(6)
            db.execute("INSERT INTO corpus_versions VALUES (?,?,?,?,?,?,?,?)",
                       (version_id, corpus_id, number, note, _now(), actor, json.dumps(ids), canonical(manifest)))
        return self.version(version_id)

    def version(self, version_id):
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM corpus_versions WHERE id = ?", (version_id,)).fetchone()
        if row is None:
            raise ValueError("corpus version not found")
        return self._version_summary(row) | {"corpus_id": row["corpus_id"], "manifest": json.loads(row["manifest"])}

    def bundle(self, version_id):
        """(documents, units, texts) of a frozen version, the same shape `retrieval_run.load_bundle` returns."""
        version = self.version(version_id)
        with closing(self._connect()) as db:
            rows = self._rows(db, version["document_rows"])
        documents, units, texts = [], [], {}
        for row in rows:
            document, doc_units, normalized = self._contract(row)
            documents.append(document)
            units.extend(doc_units)
            texts[document["document_id"]] = normalized["text"]
        if digest(canonical({"documents": documents, "units": units})) != version["manifest"]["bundle_sha256"]:
            raise ValueError("stored corpus version does not match its hash")
        return documents, units, texts

    def export_version(self, version_id, output):
        """Write a frozen version as a contract bundle (+ source bytes) into a new, empty directory."""
        output = Path(output)
        if output.exists() and any(output.iterdir()):
            raise ValueError("output must be empty: use a new directory")
        version = self.version(version_id)
        documents, units, _ = self.bundle(version_id)
        with closing(self._connect()) as db:
            rows = self._rows(db, version["document_rows"])
        for row in rows:
            folder = output / row["document_id"]
            write_json(folder / "normalized.json", json.loads(row["normalized"]))
            suffix = ".json" if row["source_kind"] == "vbpl" else Path(row["source_ref"]).suffix.lower()
            folder.mkdir(parents=True, exist_ok=True)
            (folder / f"source{suffix}").write_bytes(row["raw"])
        write_jsonl(output / "documents.jsonl", documents)
        write_jsonl(output / "units.jsonl", units)
        write_jsonl(output / "evidence.jsonl", [])
        write_jsonl(output / "claims.jsonl", [])
        write_json(output / "manifest.json", version["manifest"] | {"version_id": version_id, "exported_at": _now()})
        return {"output": output.as_posix(), "version": version["number"], "documents": len(documents), "units": len(units)}
