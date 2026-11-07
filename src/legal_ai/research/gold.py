"""Extraction gold sets for RQ1 (`gold-store-v1`), annotated by two people independently in the workspace SQLite file.

A gold set is bound to one frozen corpus version and a list of articles; its rows are every sentence of the leaf
units under those articles (`extraction_gold.template`), so the rows are the same on every machine. Each annotator
records, per sentence, the norms it states (modality, optional cue, slot values copied verbatim from the sentence)
or that it states none; saving checks every value is an exact quote. A set pack moves the set and its corpus
version to the second machine, label files move back, the comparison reports agreement (`extraction_gold.agreement`)
and each disagreement, and the adjudicated rows form the gold file `cli gold-score` reads. Annotations are research
labels, not legal advice.
"""

from contextlib import closing
from datetime import datetime, timezone
import json
import secrets
import sqlite3
import threading

from legal_ai.common.io import canonical, digest
from legal_ai.evaluation import extraction_gold
from legal_ai.extraction.llm_norms import LLM_SLOTS, MODALITIES

STORE_VERSION = "gold-store-v1"
PACK_FORMAT = "lexora-gold-pack-v1"
LABELS_FORMAT = "lexora-gold-labels-v1"
MAX_NORMS = 8
SLOT_NAMES_VI = {"actor": "Chủ thể", "action": "Hành vi", "object": "Đối tượng", "beneficiary": "Bên thụ hưởng", "recipient": "Bên nhận",
                 "conditions": "Điều kiện", "exceptions": "Ngoại lệ", "deadlines": "Thời hạn", "quantities": "Định lượng", "outcome": "Kết quả"}
MAX_ARTICLES = 120
SCHEMA = """
CREATE TABLE IF NOT EXISTS gold_sets (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, corpus_version_id TEXT NOT NULL, articles TEXT NOT NULL, rows TEXT NOT NULL,
  created_by TEXT NOT NULL, created_at TEXT NOT NULL, imported INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS gold_labels (
  set_id TEXT NOT NULL, row_key TEXT NOT NULL, annotator TEXT NOT NULL, annotator_name TEXT NOT NULL, imported INTEGER NOT NULL,
  norms TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY (set_id, row_key, annotator));
CREATE TABLE IF NOT EXISTS gold_final (
  set_id TEXT NOT NULL, row_key TEXT NOT NULL, norms TEXT NOT NULL, decided_by TEXT NOT NULL, decided_at TEXT NOT NULL,
  PRIMARY KEY (set_id, row_key));
"""


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _norm_set(norms):
    """Norms compared as a set, slot values normalized as in strict matching."""
    return sorted(canonical({"modality": n["modality"], "slots": {k: extraction_gold.normalize(v) for k, v in n["slots"].items()}}) for n in norms)


def row_key(row):
    return f"{row['unit_id']}@{row['sentence']['start']}-{row['sentence']['end']}"


class GoldStore:
    def __init__(self, path, corpora):
        self.path, self.corpora = path, corpora
        self._lock = threading.Lock()
        with closing(self._connect()) as db, db:
            db.executescript(SCHEMA)

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    def _set_row(self, db, set_id):
        row = db.execute("SELECT * FROM gold_sets WHERE id = ?", (set_id,)).fetchone()
        if row is None:
            raise ValueError("Không tìm thấy bộ gold")
        return row

    def _units(self, version_id):
        return self.corpora.bundle(version_id)[1]

    # Sets ------------------------------------------------------------------------------------
    def create(self, name, corpus_version_id, actor, articles=None, sample=None, seed="lexora-gold-v1"):
        name = (name or "").strip()
        if not 1 <= len(name) <= 120:
            raise ValueError("Tên bộ gold cần 1-120 ký tự")
        units = self._units(corpus_version_id)
        if articles:
            chosen = sorted(set(articles))
        elif sample:
            if not 1 <= int(sample) <= MAX_ARTICLES:
                raise ValueError(f"Số Điều lấy mẫu cần từ 1 đến {MAX_ARTICLES}")
            chosen = extraction_gold.sample_articles(units, int(sample), seed)
        else:
            raise ValueError("Chọn các Điều hoặc số Điều lấy mẫu")
        if len(chosen) > MAX_ARTICLES:
            raise ValueError(f"Một bộ gold tối đa {MAX_ARTICLES} Điều")
        rows = extraction_gold.template(units, chosen)
        set_id = "g" + secrets.token_hex(6)
        with self._lock, closing(self._connect()) as db, db:
            db.execute("INSERT INTO gold_sets VALUES (?,?,?,?,?,?,?,?)", (set_id, name, corpus_version_id, canonical(chosen), canonical(rows), actor, _now(), 0))
        return self.summary(set_id)

    def _summary(self, row, db):
        version = self.corpora.version(row["corpus_version_id"])
        rows = json.loads(row["rows"])
        counts = {r["annotator"]: r["n"] for r in db.execute(
            "SELECT annotator, COUNT(*) AS n FROM gold_labels WHERE set_id = ? GROUP BY annotator", (row["id"],))}
        final = db.execute("SELECT COUNT(*) FROM gold_final WHERE set_id = ?", (row["id"],)).fetchone()[0]
        return {"id": row["id"], "name": row["name"], "corpus_version_id": row["corpus_version_id"], "corpus_version": version["number"],
                "articles": len(json.loads(row["articles"])), "sentences": len(rows), "created_by": row["created_by"],
                "created_at": row["created_at"], "imported": bool(row["imported"]), "labelled": counts, "adjudicated": final}

    def sets(self):
        with closing(self._connect()) as db:
            return [self._summary(r, db) for r in db.execute("SELECT * FROM gold_sets ORDER BY created_at DESC, id")]

    def summary(self, set_id):
        with closing(self._connect()) as db:
            return self._summary(self._set_row(db, set_id), db)

    def workspace(self, set_id, annotator):
        """The set, its sentences with document titles and paths, and this annotator's labels."""
        with closing(self._connect()) as db:
            row = self._set_row(db, set_id)
            mine = {r["row_key"]: json.loads(r["norms"]) for r in db.execute(
                "SELECT row_key, norms FROM gold_labels WHERE set_id = ? AND annotator = ? AND imported = 0", (set_id, annotator))}
            summary = self._summary(row, db)
        documents, units, _ = self.corpora.bundle(row["corpus_version_id"])
        titles = {d["document_id"]: d["title"] for d in documents}
        by_id = {u["unit_id"]: u for u in units}
        from legal_ai.indexing.records import unit_path
        items = []
        for gold_row in json.loads(row["rows"]):
            unit = by_id[gold_row["unit_id"]]
            path, chain = unit_path(unit, by_id)
            parent = by_id.get(unit["parent_id"])
            items.append({"key": row_key(gold_row), "unit_id": gold_row["unit_id"], "text": gold_row["text"], "path": path,
                          "document_title": titles[unit["document_id"]],
                          "context": parent["text"].strip().split("\n")[0][:600] if parent is not None and parent["unit_type"] != "chapter" else None,
                          "norms": mine.get(row_key(gold_row))})
        return summary | {"items": items, "annotator": annotator, "slots": list(LLM_SLOTS), "modalities": list(MODALITIES)}

    # Labels ------------------------------------------------------------------------------------
    def _rows(self, db, set_id):
        row = self._set_row(db, set_id)
        return row, {row_key(r): r for r in json.loads(row["rows"])}

    def _clean(self, gold_row, norms, units):
        if not isinstance(norms, list) or len(norms) > MAX_NORMS:
            raise ValueError(f"Mỗi câu tối đa {MAX_NORMS} quy phạm")
        clean = []
        for norm in norms:
            if not isinstance(norm, dict):
                raise ValueError("Quy phạm không hợp lệ")
            slots = {name: str(value).strip() for name, value in (norm.get("slots") or {}).items()
                     if name in LLM_SLOTS and isinstance(value, str) and value.strip()}
            cue = norm.get("modality_cue")
            clean.append({"modality": norm.get("modality"), "modality_cue": cue.strip() if isinstance(cue, str) and cue.strip() else None, "slots": slots})
        unit = next(u for u in units if u["unit_id"] == gold_row["unit_id"])
        start, end = gold_row["sentence"]["start"] - unit["source_start"], gold_row["sentence"]["end"] - unit["source_start"]
        for number, norm in enumerate(clean, 1):
            if norm["modality"] not in MODALITIES:
                raise ValueError(f"Quy phạm {number}: chọn tính quy phạm")
            if not any(norm["slots"].get(name) for name in ("action", "object", "conditions", "exceptions", "quantities", "deadlines", "outcome")):
                raise ValueError(f"Quy phạm {number}: điền ít nhất một ô nội dung (hành vi, đối tượng, điều kiện, ngoại lệ, định lượng, thời hạn hoặc kết quả)")
            for name, value in [("modality_cue", norm["modality_cue"])] + list(norm["slots"].items()):
                if value and extraction_gold.locate(unit["text"], start, end, value) is None:
                    label = "Từ tình thái" if name == "modality_cue" else SLOT_NAMES_VI[name]
                    raise ValueError(f"Quy phạm {number}: ô “{label}” phải là cụm chép nguyên văn từ chính câu này")
        problems = extraction_gold.check([gold_row | {"norms": clean}], units)
        if problems:
            raise ValueError("; ".join(p.split(": ", 1)[1] for p in problems))
        return clean

    def save(self, set_id, key, annotator, annotator_name, norms):
        """Store one annotator's norms for one sentence; [] records that the sentence states no norm."""
        with closing(self._connect()) as db:
            row, rows = self._rows(db, set_id)
        if key not in rows:
            raise ValueError("Không tìm thấy câu này trong bộ gold")
        clean = self._clean(rows[key], norms, self._units(row["corpus_version_id"]))
        with self._lock, closing(self._connect()) as db, db:
            db.execute("INSERT OR REPLACE INTO gold_labels VALUES (?,?,?,?,?,?,?)", (set_id, key, annotator, annotator_name, 0, canonical(clean), _now()))
        return {"key": key, "norms": clean}

    def export_pack(self, set_id):
        with closing(self._connect()) as db:
            row = self._set_row(db, set_id)
        body = {"format": PACK_FORMAT, "set": {k: row[k] for k in ("id", "name", "corpus_version_id", "created_by", "created_at")},
                "articles": json.loads(row["articles"]), "rows": json.loads(row["rows"]),
                "corpus": self.corpora.version_payload(row["corpus_version_id"]), "exported_at": _now()}
        return body | {"rows_sha256": digest(canonical(body["rows"]))}

    def import_pack(self, pack, actor):
        if pack.get("format") != PACK_FORMAT:
            raise ValueError("Tệp không phải gói gold Lexora")
        if digest(canonical(pack["rows"])) != pack.get("rows_sha256"):
            raise ValueError("Các câu trong gói không khớp mã băm")
        info = pack["set"]
        version = self.corpora.import_version(pack["corpus"], actor)
        if version["id"] != info["corpus_version_id"]:
            raise ValueError("Gói gold trỏ tới phiên bản corpus khác")
        if extraction_gold.template(self._units(version["id"]), pack["articles"]) != pack["rows"]:
            raise ValueError("Các câu trong gói không khớp phiên bản corpus")
        with self._lock, closing(self._connect()) as db, db:
            if db.execute("SELECT 1 FROM gold_sets WHERE id = ?", (info["id"],)).fetchone() is None:
                db.execute("INSERT INTO gold_sets VALUES (?,?,?,?,?,?,?,?)", (info["id"], info["name"], info["corpus_version_id"], canonical(pack["articles"]),
                                                                            canonical(pack["rows"]), info["created_by"], info["created_at"], 1))
        return self.summary(info["id"])

    def export_labels(self, set_id, annotator):
        with closing(self._connect()) as db:
            row = self._set_row(db, set_id)
            labels = db.execute("SELECT * FROM gold_labels WHERE set_id = ? AND annotator = ? AND imported = 0 ORDER BY row_key", (set_id, annotator)).fetchall()
        if not labels:
            raise ValueError("Bạn chưa gán nhãn câu nào trong bộ gold này")
        items = [{"key": l["row_key"], "norms": json.loads(l["norms"]), "updated_at": l["updated_at"]} for l in labels]
        body = {"format": LABELS_FORMAT, "set_id": set_id, "corpus_version_id": row["corpus_version_id"], "annotator": annotator,
                "annotator_name": labels[0]["annotator_name"], "labels": items, "exported_at": _now()}
        return body | {"labels_sha256": digest(canonical(items))}

    def import_labels(self, payload, importer):
        if payload.get("format") != LABELS_FORMAT:
            raise ValueError("Tệp không phải tệp nhãn gold Lexora")
        if digest(canonical(payload["labels"])) != payload.get("labels_sha256"):
            raise ValueError("Tệp nhãn không khớp mã băm")
        if payload["annotator"] == importer:
            raise ValueError("Đây là nhãn của chính bạn; hãy nhập tệp của người gán nhãn còn lại")
        with closing(self._connect()) as db:
            row, rows = self._rows(db, payload["set_id"])
        if payload["corpus_version_id"] != row["corpus_version_id"]:
            raise ValueError("Tệp nhãn thuộc phiên bản corpus khác")
        units = self._units(row["corpus_version_id"])
        values = []
        for item in payload["labels"]:
            if item["key"] not in rows:
                raise ValueError("Tệp nhãn có câu không thuộc bộ gold này")
            values.append((payload["set_id"], item["key"], payload["annotator"], payload["annotator_name"], 1,
                           canonical(self._clean(rows[item["key"]], item["norms"], units)), item["updated_at"]))
        with self._lock, closing(self._connect()) as db, db:
            db.execute("DELETE FROM gold_labels WHERE set_id = ? AND annotator = ? AND imported = 1", (payload["set_id"], payload["annotator"]))
            db.executemany("INSERT OR REPLACE INTO gold_labels VALUES (?,?,?,?,?,?,?)", values)
        return {"annotator": payload["annotator"], "annotator_name": payload["annotator_name"], "labels": len(values)}

    def annotators(self, set_id):
        with closing(self._connect()) as db:
            return [dict(r) for r in db.execute("""SELECT annotator, annotator_name, MAX(imported) AS imported, COUNT(*) AS labels
                                                   FROM gold_labels WHERE set_id = ? GROUP BY annotator, annotator_name ORDER BY annotator""", (set_id,))]

    # Comparison and adjudication -------------------------------------------------------------
    def comparison(self, set_id, first, second):
        with closing(self._connect()) as db:
            row, rows = self._rows(db, set_id)
            labels = {}
            for r in db.execute("SELECT * FROM gold_labels WHERE set_id = ? AND annotator IN (?, ?)", (set_id, first, second)):
                labels.setdefault(r["row_key"], {})[r["annotator"]] = json.loads(r["norms"])
            final = {r["row_key"]: {"norms": json.loads(r["norms"]), "decided_by": r["decided_by"]}
                     for r in db.execute("SELECT * FROM gold_final WHERE set_id = ?", (set_id,))}
        both = [key for key in rows if first in labels.get(key, {}) and second in labels.get(key, {})]
        agreement = extraction_gold.agreement([rows[k] | {"norms": labels[k][first]} for k in both],
                                              [rows[k] | {"norms": labels[k][second]} for k in both]) if both else None
        items = []
        for key, gold_row in rows.items():
            a, b = labels.get(key, {}).get(first), labels.get(key, {}).get(second)
            same = a is not None and b is not None and _norm_set(a) == _norm_set(b)
            items.append({"key": key, "unit_id": gold_row["unit_id"], "text": gold_row["text"], "first": a, "second": b, "agree": same, "final": final.get(key)})
        return {"first": first, "second": second, "sentences": len(rows), "labelled_by_both": len(both), "agreement": agreement,
                "adjudicated": len(final), "items": items}

    def adjudicate(self, set_id, key, norms, actor):
        with closing(self._connect()) as db:
            row, rows = self._rows(db, set_id)
        if key not in rows:
            raise ValueError("Không tìm thấy câu này trong bộ gold")
        clean = self._clean(rows[key], norms, self._units(row["corpus_version_id"]))
        with self._lock, closing(self._connect()) as db, db:
            db.execute("INSERT OR REPLACE INTO gold_final VALUES (?,?,?,?,?)", (set_id, key, canonical(clean), actor, _now()))
        return {"key": key, "norms": clean}

    def gold_file(self, set_id):
        """The adjudicated gold rows (`extraction-gold-v1`); every sentence must be adjudicated."""
        with closing(self._connect()) as db:
            row, rows = self._rows(db, set_id)
            final = {r["row_key"]: json.loads(r["norms"]) for r in db.execute("SELECT * FROM gold_final WHERE set_id = ?", (set_id,))}
        missing = [key for key in rows if key not in final]
        if missing:
            raise ValueError(f"Còn {len(missing)} câu chưa chốt nhãn cuối")
        return [gold_row | {"norms": final[key]} for key, gold_row in rows.items()]
