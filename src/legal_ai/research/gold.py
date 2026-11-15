"""Extraction gold sets for RQ1 (`gold-store-v1`), annotated by two people independently in the workspace SQLite file.

A gold set is bound to one frozen corpus version and a list of articles; its rows are every sentence of the leaf
units under those articles (`extraction_gold.template`), so the rows are the same on every machine. Each annotator
records, per sentence, the norms it states (modality, optional cue, slot values copied verbatim from the sentence)
or that it states none; saving checks every value is an exact quote. A set pack moves the set and its corpus
version to the second machine, label files move back, the comparison reports agreement (`extraction_gold.agreement`)
and each disagreement, and the adjudicated rows form the gold file `cli gold-score` reads. Annotations are research
labels, not legal advice.

Partial double annotation (decision of 15/11/2026): a set may declare, once, an agreement sample
(`extraction_gold.agreement_sample`, stored in `gold_samples` with who, when, share and seed). Declaring is refused
once two annotators have labels in the set, so the sample cannot be picked after seeing them. Rows in the sample
need labels of two people; rows outside it may carry one. `finalise` records in bulk, without any judgement, the
rows every labeller labelled identically (`agreed:<a>+<b>`) and, outside the sample, the rows with exactly one
label (`single:<a>`); a person's adjudication is `adjudicated:<who>` (older stores hold a bare user name, read the
same way). A later label on a row drops its bulk final, so a provenance never outlives the labels it was made from.
Without a sample a set keeps the full double-annotation rules.
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
CREATE TABLE IF NOT EXISTS gold_samples (
  set_id TEXT PRIMARY KEY, method TEXT NOT NULL, share TEXT NOT NULL, seed TEXT NOT NULL, articles TEXT NOT NULL,
  declared_by TEXT NOT NULL, declared_at TEXT NOT NULL);
"""
AGREED, SINGLE, ADJUDICATED = "agreed", "single", "adjudicated"
# Finals written by `finalise`; a new label on their row removes them.
AUTO_FINAL = f"(decided_by LIKE '{AGREED}:%' OR decided_by LIKE '{SINGLE}:%')"
STATUSES = ("final", "agreed", "single", "disagree", "missing_second", "unlabelled")
BLOCKER_MESSAGES = {"sample_short": "{n} câu trong mẫu đồng thuận chưa có đủ nhãn của hai người",
                    "disagree": "{n} câu hai người gán khác nhau, cần đối soát từng câu",
                    AGREED: "{n} câu hai người gán giống nhau chưa được chốt (bấm Chốt hàng loạt)",
                    SINGLE: "{n} câu ngoài mẫu có nhãn của một người chưa được chốt (bấm Chốt hàng loạt)",
                    "outside_unlabelled": "{n} câu ngoài mẫu chưa ai gán",
                    "unfinished": "Còn {n} câu chưa chốt nhãn cuối"}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _norm_set(norms):
    """Norms compared as a set, slot values normalized as in strict matching."""
    return sorted(canonical({"modality": n["modality"], "slots": {k: extraction_gold.normalize(v) for k, v in n["slots"].items()}}) for n in norms)


def row_key(row):
    return f"{row['unit_id']}@{row['sentence']['start']}-{row['sentence']['end']}"


def provenance(decided_by):
    """{"kind": agreed | single | adjudicated, "people": [user names]} of a `gold_final.decided_by` value; a bare user
    name (stores before 15/11/2026) is an adjudication by that user. User names never contain ':' or '+'."""
    kind, sep, rest = decided_by.partition(":")
    if sep and kind in (AGREED, SINGLE, ADJUDICATED):
        return {"kind": kind, "people": rest.split("+")}
    return {"kind": ADJUDICATED, "people": [decided_by]}


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

    # Agreement sample and the state of every row ------------------------------------------------
    @staticmethod
    def _sample(db, set_id):
        row = db.execute("SELECT * FROM gold_samples WHERE set_id = ?", (set_id,)).fetchone()
        return None if row is None else dict(row) | {"articles": json.loads(row["articles"])}

    @staticmethod
    def _public_sample(sample, rows):
        if sample is None:
            return None
        chosen = set(sample["articles"])
        return {k: sample[k] for k in ("method", "share", "seed", "articles", "declared_by", "declared_at")} | {
            "article_count": len(chosen), "sentences": sum(1 for r in rows if extraction_gold.article_id(r["unit_id"]) in chosen)}

    def _state(self, db, set_id):
        """The set, its rows by key, its sample, every annotator's labels and the final rows."""
        row, rows = self._rows(db, set_id)
        labels = {}
        for r in db.execute("SELECT row_key, annotator, norms FROM gold_labels WHERE set_id = ?", (set_id,)):
            labels.setdefault(r["row_key"], {})[r["annotator"]] = json.loads(r["norms"])
        final = {r["row_key"]: {"norms": json.loads(r["norms"]), "decided_by": r["decided_by"]}
                 for r in db.execute("SELECT row_key, norms, decided_by FROM gold_final WHERE set_id = ?", (set_id,))}
        return {"set": row, "rows": rows, "sample": self._sample(db, set_id), "labels": labels, "final": final}

    @staticmethod
    def _in_sample(state, key):
        """True or False with a declared sample, None without one."""
        sample = state["sample"]
        return None if sample is None else extraction_gold.article_id(state["rows"][key]["unit_id"]) in sample["articles"]

    @classmethod
    def _status(cls, state, key):
        """final | agreed (equal labels of every labeller, ready for bulk finalising) | single (one label outside the
        sample, ready) | disagree (needs a person) | missing_second (a sample row, or any row of a set without a
        sample, that still lacks a second label) | unlabelled (no label, outside the sample or without one)."""
        if key in state["final"]:
            return "final"
        labels = list(state["labels"].get(key, {}).values())
        in_sample = cls._in_sample(state, key)
        if len(labels) >= 2:
            return AGREED if all(_norm_set(n) == _norm_set(labels[0]) for n in labels[1:]) else "disagree"
        if in_sample:
            return "missing_second"
        if len(labels) == 1:
            return SINGLE if in_sample is False else "missing_second"
        return "unlabelled"

    @classmethod
    def _plan(cls, state):
        counts = dict.fromkeys(STATUSES, 0)
        for key in state["rows"]:
            counts[cls._status(state, key)] += 1
        return counts

    @classmethod
    def _blockers(cls, state):
        """What still stops the gold file: [{"kind", "n", "message"}] in a fixed order, the message in Vietnamese (the
        UI localizes by kind); empty when the file can be exported."""
        rows, labels, final = state["rows"], state["labels"], state["final"]
        if state["sample"] is None:
            tally = {"unfinished": sum(1 for key in rows if key not in final)}
        else:
            tally = dict.fromkeys(BLOCKER_MESSAGES, 0)
            del tally["unfinished"]
            for key in rows:
                status = cls._status(state, key)
                if cls._in_sample(state, key) and len(labels.get(key, {})) < 2:
                    tally["sample_short"] += 1
                elif status == "unlabelled":
                    tally["outside_unlabelled"] += 1
                elif status in tally:
                    tally[status] += 1
        return [{"kind": kind, "n": n, "message": BLOCKER_MESSAGES[kind].format(n=n)} for kind, n in tally.items() if n]

    def declare_sample(self, set_id, actor, share=extraction_gold.SAMPLE_SHARE, seed=extraction_gold.SAMPLE_SEED):
        """Pick and store the agreement sample once, before a second annotator has any label in the set."""
        share, seed = str(share).strip(), (seed or "").strip()
        try:
            extraction_gold.sample_share(share)
        except ValueError:
            raise ValueError("Tỉ lệ mẫu cần lớn hơn 0 và không quá 1") from None
        if not 1 <= len(seed) <= 80:
            raise ValueError("Hạt giống cần 1-80 ký tự")
        with self._lock, closing(self._connect()) as db, db:
            row, rows = self._rows(db, set_id)
            existing = self._sample(db, set_id)
            if existing is not None:
                raise ValueError(f"Bộ gold này đã có mẫu đồng thuận do {existing['declared_by']} chọn lúc {existing['declared_at']}; mẫu không đổi được")
            people = [r[0] for r in db.execute("SELECT DISTINCT annotator FROM gold_labels WHERE set_id = ? ORDER BY annotator", (set_id,))]
            if len(people) >= 2:
                raise ValueError(f"Bộ gold đã có nhãn của {len(people)} người ({', '.join(people)}); mẫu đồng thuận phải được chọn "
                                 "trước khi người gán thứ hai bắt đầu, nên không chọn được nữa")
            chosen = extraction_gold.agreement_sample(json.loads(row["articles"]), share, seed)
            db.execute("INSERT INTO gold_samples VALUES (?,?,?,?,?,?,?)",
                       (set_id, extraction_gold.SAMPLE_METHOD, share, seed, canonical(chosen), actor, _now()))
            return self._public_sample(self._sample(db, set_id), list(rows.values()))

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
        sample = self._public_sample(self._sample(db, row["id"]), rows)
        return {"id": row["id"], "name": row["name"], "corpus_version_id": row["corpus_version_id"], "corpus_version": version["number"],
                "articles": len(json.loads(row["articles"])), "sentences": len(rows), "created_by": row["created_by"],
                "created_at": row["created_at"], "imported": bool(row["imported"]), "labelled": counts, "adjudicated": final,
                "sample_size": None if sample is None else {"articles": sample["article_count"], "sentences": sample["sentences"]}}

    def sets(self):
        with closing(self._connect()) as db:
            return [self._summary(r, db) for r in db.execute("SELECT * FROM gold_sets ORDER BY created_at DESC, id")]

    def summary(self, set_id):
        with closing(self._connect()) as db:
            return self._summary(self._set_row(db, set_id), db)

    def workspace(self, set_id, annotator):
        """The set, its sentences with document titles and paths (each marked in or out of the agreement sample),
        this annotator's labels, the sample, whether it can still be declared and what still stops the gold file."""
        with closing(self._connect()) as db:
            row = self._set_row(db, set_id)
            mine = {r["row_key"]: json.loads(r["norms"]) for r in db.execute(
                "SELECT row_key, norms FROM gold_labels WHERE set_id = ? AND annotator = ? AND imported = 0", (set_id, annotator))}
            summary = self._summary(row, db)
            state = self._state(db, set_id)
        people = {who for labels in state["labels"].values() for who in labels}
        documents, units, _ = self.corpora.bundle(row["corpus_version_id"])
        titles = {d["document_id"]: d["title"] for d in documents}
        by_id = {u["unit_id"]: u for u in units}
        from legal_ai.indexing.records import unit_path
        items = []
        for gold_row in json.loads(row["rows"]):
            unit = by_id[gold_row["unit_id"]]
            path, chain = unit_path(unit, by_id)
            parent = by_id.get(unit["parent_id"])
            key = row_key(gold_row)
            items.append({"key": key, "unit_id": gold_row["unit_id"], "text": gold_row["text"], "path": path,
                          "document_title": titles[unit["document_id"]],
                          "context": parent["text"].strip().split("\n")[0][:600] if parent is not None and parent["unit_type"] != "chapter" else None,
                          "in_sample": self._in_sample(state, key) is True, "norms": mine.get(key)})
        sample = self._public_sample(state["sample"], list(state["rows"].values()))
        return summary | {"items": items, "annotator": annotator, "slots": list(LLM_SLOTS), "modalities": list(MODALITIES),
                          "sample": sample, "sample_declarable": sample is None and len(people) < 2,
                          "sample_defaults": {"share": extraction_gold.SAMPLE_SHARE, "seed": extraction_gold.SAMPLE_SEED,
                                              "articles": len(extraction_gold.agreement_sample(json.loads(row["articles"])))},
                          "blockers": self._blockers(state)}

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
        """Store one annotator's norms for one sentence; [] records that the sentence states no norm. A bulk final of
        the row is dropped, since the labels it was made from changed."""
        with closing(self._connect()) as db:
            row, rows = self._rows(db, set_id)
        if key not in rows:
            raise ValueError("Không tìm thấy câu này trong bộ gold")
        clean = self._clean(rows[key], norms, self._units(row["corpus_version_id"]))
        with self._lock, closing(self._connect()) as db, db:
            db.execute("INSERT OR REPLACE INTO gold_labels VALUES (?,?,?,?,?,?,?)", (set_id, key, annotator, annotator_name, 0, canonical(clean), _now()))
            db.execute(f"DELETE FROM gold_final WHERE set_id = ? AND row_key = ? AND {AUTO_FINAL}", (set_id, key))
        return {"key": key, "norms": clean}

    def export_pack(self, set_id):
        with closing(self._connect()) as db:
            row = self._set_row(db, set_id)
            sample = self._sample(db, set_id)
        body = {"format": PACK_FORMAT, "set": {k: row[k] for k in ("id", "name", "corpus_version_id", "created_by", "created_at")},
                "articles": json.loads(row["articles"]), "rows": json.loads(row["rows"]),
                "corpus": self.corpora.version_payload(row["corpus_version_id"]), "exported_at": _now()}
        if sample is not None:
            body["sample"] = {k: sample[k] for k in ("method", "share", "seed", "articles", "declared_by", "declared_at")}
        return body | {"rows_sha256": digest(canonical(body["rows"]))}

    def import_pack(self, pack, actor):
        """Add the set (and its agreement sample, recomputed to check it) from a pack; importing a newer pack of a known
        set adds a sample declared after the first pack."""
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
        sample = pack.get("sample")
        if sample is not None and (sample.get("method") != extraction_gold.SAMPLE_METHOD
                                   or extraction_gold.agreement_sample(pack["articles"], sample["share"], sample["seed"]) != sample["articles"]):
            raise ValueError("Mẫu đồng thuận trong gói không khớp các Điều của bộ gold")
        with self._lock, closing(self._connect()) as db, db:
            if db.execute("SELECT 1 FROM gold_sets WHERE id = ?", (info["id"],)).fetchone() is None:
                db.execute("INSERT INTO gold_sets VALUES (?,?,?,?,?,?,?,?)", (info["id"], info["name"], info["corpus_version_id"], canonical(pack["articles"]),
                                                                            canonical(pack["rows"]), info["created_by"], info["created_at"], 1))
            if sample is not None:
                existing = self._sample(db, info["id"])
                if existing is None:
                    db.execute("INSERT INTO gold_samples VALUES (?,?,?,?,?,?,?)", (info["id"], sample["method"], sample["share"], sample["seed"],
                                                                                 canonical(sample["articles"]), sample["declared_by"], sample["declared_at"]))
                elif existing["articles"] != sample["articles"]:
                    raise ValueError("Máy này đã có một mẫu đồng thuận khác cho bộ gold này")
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
            touched = {r[0] for r in db.execute("SELECT row_key FROM gold_labels WHERE set_id = ? AND annotator = ? AND imported = 1",
                                                (payload["set_id"], payload["annotator"]))} | {item["key"] for item in payload["labels"]}
            db.execute("DELETE FROM gold_labels WHERE set_id = ? AND annotator = ? AND imported = 1", (payload["set_id"], payload["annotator"]))
            db.executemany("INSERT OR REPLACE INTO gold_labels VALUES (?,?,?,?,?,?,?)", values)
            db.executemany(f"DELETE FROM gold_final WHERE set_id = ? AND row_key = ? AND {AUTO_FINAL}", [(payload["set_id"], key) for key in sorted(touched)])
        return {"annotator": payload["annotator"], "annotator_name": payload["annotator_name"], "labels": len(values)}

    def annotators(self, set_id):
        with closing(self._connect()) as db:
            return [dict(r) for r in db.execute("""SELECT annotator, annotator_name, MAX(imported) AS imported, COUNT(*) AS labels
                                                   FROM gold_labels WHERE set_id = ? GROUP BY annotator, annotator_name ORDER BY annotator""", (set_id,))]

    # Comparison and adjudication -------------------------------------------------------------
    def comparison(self, set_id, first, second):
        """Agreement of two annotators on the rows both labelled; every row with both labels, its place in the sample,
        its state and final label; how much of the sample each has labelled; the bulk-finalise plan; and what still
        stops the gold file."""
        with closing(self._connect()) as db:
            state = self._state(db, set_id)
        rows, labels, final = state["rows"], state["labels"], state["final"]
        both = [key for key in rows if first in labels.get(key, {}) and second in labels.get(key, {})]
        agreement = extraction_gold.agreement([rows[k] | {"norms": labels[k][first]} for k in both],
                                              [rows[k] | {"norms": labels[k][second]} for k in both]) if both else None
        items = []
        for key, gold_row in rows.items():
            a, b = labels.get(key, {}).get(first), labels.get(key, {}).get(second)
            same = a is not None and b is not None and _norm_set(a) == _norm_set(b)
            decided = final.get(key)
            items.append({"key": key, "unit_id": gold_row["unit_id"], "text": gold_row["text"], "first": a, "second": b, "agree": same,
                          "in_sample": self._in_sample(state, key) is True, "status": self._status(state, key),
                          "final": None if decided is None else decided | provenance(decided["decided_by"])})
        sample = self._public_sample(state["sample"], list(rows.values()))
        in_sample = [key for key in rows if self._in_sample(state, key)]
        progress = {who: sum(1 for key in in_sample if who in labels.get(key, {})) for who in (first, second)}
        return {"first": first, "second": second, "sentences": len(rows), "labelled_by_both": len(both), "agreement": agreement,
                "adjudicated": len(final), "sample": sample, "sample_progress": progress if sample else None,
                "plan": self._plan(state), "blockers": self._blockers(state), "items": items}

    def adjudicate(self, set_id, key, norms, actor):
        """A person's final label for one row (`adjudicated:<actor>`); a row of the agreement sample needs labels of two
        people first."""
        with closing(self._connect()) as db:
            state = self._state(db, set_id)
        if key not in state["rows"]:
            raise ValueError("Không tìm thấy câu này trong bộ gold")
        if self._in_sample(state, key) and len(state["labels"].get(key, {})) < 2:
            raise ValueError("Câu này thuộc mẫu đồng thuận: cần nhãn của cả hai người trước khi chốt")
        clean = self._clean(state["rows"][key], norms, self._units(state["set"]["corpus_version_id"]))
        with self._lock, closing(self._connect()) as db, db:
            db.execute("INSERT OR REPLACE INTO gold_final VALUES (?,?,?,?,?)", (set_id, key, canonical(clean), f"{ADJUDICATED}:{actor}", _now()))
        return {"key": key, "norms": clean}

    def finalise(self, set_id):
        """Record in bulk the rows that need no judgement: equal labels of every labeller (`agreed:<a>+<b>`) and, with
        an agreement sample, rows outside it with exactly one label (`single:<a>`). Rows already final are kept."""
        with self._lock, closing(self._connect()) as db, db:
            state = self._state(db, set_id)
            stamp, done = _now(), {AGREED: 0, SINGLE: 0}
            for key in state["rows"]:
                status = self._status(state, key)
                if status not in done:
                    continue
                people = sorted(state["labels"][key])
                db.execute("INSERT INTO gold_final VALUES (?,?,?,?,?)",
                           (set_id, key, canonical(state["labels"][key][people[0]]), f"{status}:{'+'.join(people)}", stamp))
                done[status] += 1
            state = self._state(db, set_id)
        return {"agreed": done[AGREED], "single": done[SINGLE], "blockers": self._blockers(state)}

    def gold_file(self, set_id):
        """The final gold rows (`extraction-gold-v1`), each with `annotation` (double or single, by whom, the final's
        provenance and, with a sample, whether the row is in it). With an agreement sample every sample row needs two
        people's labels and a final label and every other row a final label; without one every row needs a final
        label. The error names exactly what is missing."""
        with closing(self._connect()) as db:
            state = self._state(db, set_id)
        blockers = self._blockers(state)
        if blockers:
            raise ValueError("Chưa xuất được gold cuối: " + "; ".join(b["message"] for b in blockers))
        out = []
        for key, gold_row in state["rows"].items():
            decided, labelled = state["final"][key], sorted(state["labels"].get(key, {}))
            annotation = {"mode": "double" if len(labelled) >= 2 else "single",
                          "annotators": labelled or provenance(decided["decided_by"])["people"], "decided_by": decided["decided_by"]}
            if state["sample"] is not None:
                annotation["in_sample"] = self._in_sample(state, key)
            out.append(gold_row | {"norms": decided["norms"], "annotation": annotation})
        return out
