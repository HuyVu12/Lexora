"""Local search catalog of Vietnamese legal documents (`catalog-v1`), keyed by vbpl.vn document ID.

Built once from two open datasets whose metadata comes from vbpl.vn:
- th1nhng0/vietnamese-legal-documents (CC BY 4.0): `metadata` (about 171k documents) and `relationships`.
- undertheseanlp/UTS_VLC (MIT): `database/vn_law.sqlite`, the Constitution, Codes and Laws.

The catalog only helps find a document; its text is always fetched from vbpl.vn (`vbpl_api.py`) so evidence
anchors to the official source. Searching is offline and accent-insensitive (SQLite FTS5 over folded text).
Building needs `pyarrow` (the `catalog` extra) to read Parquet; searching needs the standard library only.
"""

from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
import unicodedata

from legal_ai.common.io import digest

CATALOG_VERSION = "catalog-v1"
TH1NHNG0 = "th1nhng0/vietnamese-legal-documents"
UTS_VLC = "undertheseanlp/UTS_VLC"
# Normative types written in Điều/Khoản; ranked first because a corpus needs that structure.
STRUCTURED = ("Hiến pháp", "Bộ luật", "Luật", "Pháp lệnh", "Nghị định", "Nghị quyết", "Thông tư", "Thông tư liên tịch", "Văn bản hợp nhất")
# Types that usually have no Điều at all (a promulgation order, a directive, an official letter).
UNSTRUCTURED = {"Lệnh", "Chỉ thị", "Công văn"}
IN_FORCE = {"Còn hiệu lực", "Hết hiệu lực một phần", "Chưa có hiệu lực", "Ngưng hiệu lực một phần"}
FILES = {"metadata": "th1nhng0-metadata.parquet", "relationships": "th1nhng0-relationships.parquet", "uts": "uts_vlc-vn_law.sqlite"}
SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE documents (
  vbpl_id TEXT PRIMARY KEY, doc_num TEXT, title TEXT NOT NULL, doc_type TEXT, issue_date TEXT,
  effective_from TEXT, effective_to TEXT, effect_status TEXT, agency TEXT, scope TEXT,
  is_translation INTEGER NOT NULL, sources TEXT NOT NULL, folded_num TEXT, in_force INTEGER NOT NULL);
CREATE VIRTUAL TABLE documents_fts USING fts5(vbpl_id UNINDEXED, folded, tokenize = 'unicode61');
CREATE TABLE relationships (doc_id TEXT NOT NULL, other_doc_id TEXT NOT NULL, relationship TEXT NOT NULL);
CREATE INDEX relationships_doc ON relationships (doc_id);
CREATE INDEX relationships_other ON relationships (other_doc_id);
"""


def fold(text):
    """Lower case, without Vietnamese diacritics (đ -> d), for accent-insensitive matching."""
    text = unicodedata.normalize("NFD", (text or "").replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in text if unicodedata.category(c) != "Mn").lower()


def _iso(value):
    """DD/MM/YYYY or YYYY-MM-DD... to YYYY-MM-DD; anything else to None."""
    if not value:
        return None
    if match := re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", value.strip()):
        return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
    return value[:10] if re.match(r"\d{4}-\d{2}-\d{2}", value) else None


def _translation(row):
    return row["doc_type"] == "Bản dịch văn bản" or row["vbpl_id"].startswith("vbpqta_")


def build_catalog(raw_dir, output):
    """Build a new catalog file from the dataset files in `raw_dir` (see FILES) and `revisions.json`."""
    import pyarrow.parquet as pq  # Only the build step reads Parquet.
    raw_dir, output = Path(raw_dir), Path(output)
    if output.exists():
        raise ValueError("output exists: build a new catalog file")
    revisions = json.loads((raw_dir / "revisions.json").read_text(encoding="utf-8"))
    rows = {}
    for item in pq.read_table(raw_dir / FILES["metadata"]).to_pylist():
        row = {"vbpl_id": item["id"], "doc_num": item["so_ky_hieu"], "title": (item["title"] or "").strip(), "doc_type": item["loai_van_ban"],
               "issue_date": _iso(item["ngay_ban_hanh"]), "effective_from": _iso(item["ngay_co_hieu_luc"]), "effective_to": _iso(item["ngay_het_hieu_luc"]),
               "effect_status": item["tinh_trang_hieu_luc"], "agency": item["co_quan_ban_hanh"], "scope": item["pham_vi"], "sources": [TH1NHNG0]}
        if row["vbpl_id"] and row["title"]:
            rows[row["vbpl_id"]] = row
    with closing(sqlite3.connect(raw_dir / FILES["uts"])) as uts:
        for vbpl_id, doc_num, title, doc_type, issue, eff_from, eff_to, status, agency in uts.execute(
                "SELECT id, doc_num, title, doc_type, issue_date, eff_from, eff_to, status_name, agency FROM laws"):
            if vbpl_id in rows:
                rows[vbpl_id]["sources"].append(UTS_VLC)
            elif vbpl_id and title:
                rows[vbpl_id] = {"vbpl_id": vbpl_id, "doc_num": doc_num, "title": title.strip(), "doc_type": doc_type, "issue_date": _iso(issue),
                                 "effective_from": _iso(eff_from), "effective_to": _iso(eff_to), "effect_status": status, "agency": agency,
                                 "scope": "Trung ương", "sources": [UTS_VLC]}
    relationships = pq.read_table(raw_dir / FILES["relationships"]).to_pylist()
    output.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(output)) as db, db:
        db.executescript(SCHEMA)
        db.executemany("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [
            (r["vbpl_id"], r["doc_num"], r["title"], r["doc_type"], r["issue_date"], r["effective_from"], r["effective_to"], r["effect_status"],
             r["agency"], r["scope"], int(_translation(r)), ",".join(r["sources"]), fold(r["doc_num"]).strip() or None,
             int(r["effect_status"] in IN_FORCE)) for r in sorted(rows.values(), key=lambda r: r["vbpl_id"])])
        db.executemany("INSERT INTO documents_fts VALUES (?, ?)", [(r["vbpl_id"], fold(f"{r['title']} {r['doc_num'] or ''}")) for r in rows.values()])
        db.executemany("INSERT INTO relationships VALUES (?,?,?)", [(r["doc_id"], r["other_doc_id"], r["relationship"]) for r in relationships])
        meta = {"catalog_version": CATALOG_VERSION, "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "revisions": revisions, "files": {name: digest((raw_dir / file).read_bytes()) for name, file in FILES.items()},
                "documents": len(rows), "relationships": len(relationships),
                "licenses": {TH1NHNG0: "CC BY 4.0", UTS_VLC: "MIT"}}
        db.executemany("INSERT INTO meta VALUES (?, ?)", [(key, json.dumps(value, ensure_ascii=False)) for key, value in meta.items()])
    return meta


class Catalog:
    """Read-only search over a built catalog file."""

    def __init__(self, path):
        self.path = Path(path)
        if not self.path.is_file():
            raise ValueError(f"catalog not found: {path}")
        with closing(self._connect()) as db:
            version = json.loads(db.execute("SELECT value FROM meta WHERE key = 'catalog_version'").fetchone()[0])
        if version != CATALOG_VERSION:
            raise ValueError(f"unsupported catalog version: {version}")

    def _connect(self):
        db = sqlite3.connect(f"file:{self.path.as_posix()}?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        return db

    def info(self):
        with closing(self._connect()) as db:
            return {key: json.loads(value) for key, value in db.execute("SELECT key, value FROM meta")}

    def search(self, query, limit=20, include_translations=False, doc_type=None):
        """Documents whose title or number holds every query word, accents ignored; only the last word may be
        a prefix (still being typed). Order: exact document number, the words as one phrase, normative types written
        in Điều (laws, decrees, circulars...), documents in force (incl. partly expired or not yet effective), FTS5 rank,
        newest first."""
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        words = re.findall(r"[0-9a-z]+", fold(query))[:12]
        if not words:
            return []
        terms = [f'"{word}"' for word in words[:-1]] + [f'"{words[-1]}"*']
        filters = ("" if include_translations else " AND d.is_translation = 0") + (" AND d.doc_type = ?" if doc_type else "")
        structured = ", ".join("'" + kind + "'" for kind in STRUCTURED)
        sql = ("SELECT d.*, (d.folded_num = ?) AS exact, bm25(documents_fts) AS rank "
               "FROM documents_fts JOIN documents d USING (vbpl_id) WHERE documents_fts MATCH ?" + filters
               + f" ORDER BY exact DESC, (d.doc_type IN ({structured})) DESC, d.in_force DESC, rank, d.issue_date DESC, d.vbpl_id LIMIT ?")
        number = fold(query).strip()
        # Two passes, since FTS5 allows one MATCH per query: the words as one phrase first, then all words anywhere.
        queries = [" + ".join(terms), " AND ".join(terms)] if len(words) > 1 else [" AND ".join(terms)]
        hidden = {"rank", "exact", "folded_num"}
        found = {}
        with closing(self._connect()) as db:
            for match in queries:
                parameters = [number, match] + ([doc_type] if doc_type else []) + [limit]
                for row in db.execute(sql, parameters):
                    found.setdefault(row["vbpl_id"], (row["exact"], {key: row[key] for key in row.keys() if key not in hidden}
                                                      | {"sources": row["sources"].split(","), "in_force": bool(row["in_force"]),
                                                         "usually_no_articles": row["doc_type"] in UNSTRUCTURED}))
        exact = [row for flag, row in found.values() if flag]
        return (exact + [row for flag, row in found.values() if not flag])[:limit]

    def document(self, vbpl_id):
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM documents WHERE vbpl_id = ?", (vbpl_id,)).fetchone()
            return {k: row[k] for k in row.keys() if k != "folded_num"} | {"sources": row["sources"].split(","), "in_force": bool(row["in_force"])} if row else None

    def relationships(self, vbpl_id, limit=50):
        """Edges from and to a document, with the other document's number and title when the catalog has it."""
        with closing(self._connect()) as db:
            rows = db.execute(
                "SELECT 'out' AS direction, r.relationship, r.other_doc_id AS other_id, d.doc_num, d.title FROM relationships r "
                "LEFT JOIN documents d ON d.vbpl_id = r.other_doc_id WHERE r.doc_id = ? "
                "UNION ALL SELECT 'in', r.relationship, r.doc_id, d.doc_num, d.title FROM relationships r "
                "LEFT JOIN documents d ON d.vbpl_id = r.doc_id WHERE r.other_doc_id = ? LIMIT ?", (vbpl_id, vbpl_id, limit))
            return [dict(row) for row in rows]
