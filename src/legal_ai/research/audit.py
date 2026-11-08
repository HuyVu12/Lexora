"""Rejection audit labelled in the app (`audit-store-v1`): the blinded sheet of `rejection_audit`, one label per
annotator account, adjudication and scoring.

A set is imported once from a sheet (`kb-audit-sheet`) and its key. Annotators see only the sheet columns (context,
unit text, sentence, norm); the key (model, validator decision, automatic category) stays in the store and is used only
to score, which admin and dev accounts can open. Labels are the five of `rejection_audit.LABELS`. Two annotators label
independently; the comparison gives Cohen's kappa; adjudication records one final label per item. A sheet in the CSV
layout of `kb-audit-score` can be downloaded for each annotator or for the final labels.
"""

from contextlib import closing
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import secrets
import sqlite3
import threading

from legal_ai.evaluation.rejection_audit import AUDIT_VERSION, COLUMNS, LABELS, agreement_labels, score_labels

STORE_VERSION = "audit-store-v1"
SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_sets (id TEXT PRIMARY KEY, name TEXT NOT NULL, items TEXT NOT NULL, key TEXT NOT NULL,
    created_by TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_labels (set_id TEXT NOT NULL, item_id TEXT NOT NULL, annotator TEXT NOT NULL, annotator_name TEXT NOT NULL,
    label TEXT NOT NULL, note TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY (set_id, item_id, annotator));
CREATE TABLE IF NOT EXISTS audit_final (set_id TEXT NOT NULL, item_id TEXT NOT NULL, label TEXT NOT NULL, note TEXT NOT NULL,
    decided_by TEXT NOT NULL, decided_at TEXT NOT NULL, PRIMARY KEY (set_id, item_id));
"""
SHEET_FIELDS = ("context", "unit_text", "sentence", "norm")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AuditStore:
    def __init__(self, path):
        self.path = str(path)
        self._lock = threading.Lock()
        with closing(self._connect()) as db, db:
            db.executescript(SCHEMA)

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def _set(self, db, set_id):
        row = db.execute("SELECT * FROM audit_sets WHERE id = ?", (set_id,)).fetchone()
        if row is None:
            raise ValueError("Không tìm thấy bảng kiểm tra")
        return row

    def create(self, name, sheet_rows, key, actor):
        """A new set from the rows of a sheet and the `items` of its key; every row must be in the key."""
        name = (name or "").strip()
        if not 1 <= len(name) <= 120:
            raise ValueError("Tên bảng kiểm tra cần 1-120 ký tự")
        items = [{"item_id": r["item_id"]} | {f: (r.get(f) or "") for f in SHEET_FIELDS} for r in sheet_rows]
        ids = [i["item_id"] for i in items]
        if not items or len(set(ids)) != len(ids) or any(i not in key for i in ids):
            raise ValueError("Bảng và khóa không khớp: mỗi dòng cần một mã riêng có trong khóa")
        set_id = "a" + secrets.token_hex(6)
        with self._lock, closing(self._connect()) as db, db:
            db.execute("INSERT INTO audit_sets VALUES (?,?,?,?,?,?)", (set_id, name, json.dumps(items, ensure_ascii=False),
                                                                       json.dumps({i: key[i] for i in ids}, ensure_ascii=False), actor, _now()))
        return self.summary(set_id)

    def import_files(self, name, sheet_path, key_path, actor):
        with Path(sheet_path).open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        key = json.loads(Path(key_path).read_text(encoding="utf-8"))
        if key.get("audit_version") != AUDIT_VERSION:
            raise ValueError("Tệp khóa không phải của rejection-audit-v1")
        return self.create(name, rows, key["items"], actor)

    def _summary(self, db, row):
        total = len(json.loads(row["items"]))
        counts = {r["annotator"]: {"name": r["annotator_name"], "n": r["n"]} for r in db.execute(
            "SELECT annotator, MAX(annotator_name) AS annotator_name, COUNT(*) AS n FROM audit_labels WHERE set_id = ? GROUP BY annotator", (row["id"],))}
        final = db.execute("SELECT COUNT(*) FROM audit_final WHERE set_id = ?", (row["id"],)).fetchone()[0]
        return {"id": row["id"], "name": row["name"], "items": total, "labelled": counts, "adjudicated": final,
                "created_by": row["created_by"], "created_at": row["created_at"]}

    def sets(self):
        with closing(self._connect()) as db:
            return [self._summary(db, r) for r in db.execute("SELECT * FROM audit_sets ORDER BY created_at DESC, id")]

    def summary(self, set_id):
        with closing(self._connect()) as db:
            return self._summary(db, self._set(db, set_id))

    def workspace(self, set_id, annotator):
        """The blinded items and this annotator's labels; the key is never part of it."""
        with closing(self._connect()) as db:
            row = self._set(db, set_id)
            mine = {r["item_id"]: {"label": r["label"], "note": r["note"], "updated_at": r["updated_at"]}
                    for r in db.execute("SELECT * FROM audit_labels WHERE set_id = ? AND annotator = ?", (set_id, annotator))}
            summary = self._summary(db, row)
        return summary | {"labels": list(LABELS), "rows": [item | {"mine": mine.get(item["item_id"])} for item in json.loads(row["items"])]}

    def save_label(self, set_id, item_id, annotator, annotator_name, label, note=""):
        if label not in LABELS:
            raise ValueError(f"Nhãn phải là một trong {', '.join(LABELS)}")
        note = (note or "").strip()
        if len(note) > 2000:
            raise ValueError("Ghi chú tối đa 2000 ký tự")
        with self._lock, closing(self._connect()) as db, db:
            if item_id not in {i["item_id"] for i in json.loads(self._set(db, set_id)["items"])}:
                raise ValueError("Không tìm thấy dòng này trong bảng")
            db.execute("INSERT OR REPLACE INTO audit_labels VALUES (?,?,?,?,?,?,?)", (set_id, item_id, annotator, annotator_name, label, note, _now()))
        return {"item_id": item_id, "label": label, "note": note}

    def _labels(self, db, set_id, annotator):
        return {r["item_id"]: r for r in db.execute("SELECT * FROM audit_labels WHERE set_id = ? AND annotator = ?", (set_id, annotator))}

    def comparison(self, set_id, first, second):
        """Both annotators' labels per item, kappa and the final labels; the key stays hidden."""
        with closing(self._connect()) as db:
            row = self._set(db, set_id)
            a, b = self._labels(db, set_id, first), self._labels(db, set_id, second)
            final = {r["item_id"]: dict(r) for r in db.execute("SELECT * FROM audit_final WHERE set_id = ?", (set_id,))}
        items = []
        for item in json.loads(row["items"]):
            x, y = a.get(item["item_id"]), b.get(item["item_id"])
            items.append(item | {"first": dict(x) if x else None, "second": dict(y) if y else None, "final": final.get(item["item_id"]),
                                 "agree": bool(x and y and x["label"] == y["label"])})
        names = {who: (rows[next(iter(rows))]["annotator_name"] if rows else who) for who, rows in ((first, a), (second, b))}
        agreement = agreement_labels({k: v["label"] for k, v in a.items()}, {k: v["label"] for k, v in b.items()})
        return {"set": self._summary_from(row, len(a), len(b), len(final)), "first": {"username": first, "name": names[first]},
                "second": {"username": second, "name": names[second]}, "agreement": agreement, "items": items}

    @staticmethod
    def _summary_from(row, a, b, final):
        return {"id": row["id"], "name": row["name"], "items": len(json.loads(row["items"])), "first_labelled": a, "second_labelled": b, "adjudicated": final}

    def adjudicate(self, set_id, item_id, label, note, actor):
        if label not in LABELS:
            raise ValueError(f"Nhãn phải là một trong {', '.join(LABELS)}")
        with self._lock, closing(self._connect()) as db, db:
            if item_id not in {i["item_id"] for i in json.loads(self._set(db, set_id)["items"])}:
                raise ValueError("Không tìm thấy dòng này trong bảng")
            db.execute("INSERT OR REPLACE INTO audit_final VALUES (?,?,?,?,?,?)", (set_id, item_id, label, (note or "").strip()[:2000], actor, _now()))
        return {"item_id": item_id, "label": label}

    def accept_agreed(self, set_id, first, second, actor):
        """Final label for every item where both annotators gave the same label and nothing is final yet."""
        with self._lock, closing(self._connect()) as db, db:
            self._set(db, set_id)
            a, b = self._labels(db, set_id, first), self._labels(db, set_id, second)
            done = {r[0] for r in db.execute("SELECT item_id FROM audit_final WHERE set_id = ?", (set_id,))}
            agreed = [i for i in a if i in b and a[i]["label"] == b[i]["label"] and i not in done]
            for item_id in agreed:
                db.execute("INSERT INTO audit_final VALUES (?,?,?,?,?,?)", (set_id, item_id, a[item_id]["label"], "", actor, _now()))
        return {"accepted": len(agreed)}

    def score(self, set_id, source="final"):
        """`score_labels` on the final labels (default) or on one annotator's labels; opens the key."""
        with closing(self._connect()) as db:
            row = self._set(db, set_id)
            if source == "final":
                labels = {r["item_id"]: r["label"] for r in db.execute("SELECT item_id, label FROM audit_final WHERE set_id = ?", (set_id,))}
            else:
                labels = {k: v["label"] for k, v in self._labels(db, set_id, source).items()}
        key = json.loads(row["key"])
        report = score_labels({i: labels.get(i) for i in key}, key)
        return report | {"source": source, "labelled": sum(1 for v in labels.values() if v)}

    def sheet_csv(self, set_id, source):
        """The labels as a sheet in the `kb-audit-score` CSV layout (one annotator, or `final`)."""
        with closing(self._connect()) as db:
            row = self._set(db, set_id)
            if source == "final":
                labels = {r["item_id"]: r for r in db.execute("SELECT * FROM audit_final WHERE set_id = ?", (set_id,))}
            else:
                labels = self._labels(db, set_id, source)
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=COLUMNS)
        writer.writeheader()
        for item in json.loads(row["items"]):
            got = labels.get(item["item_id"])
            writer.writerow({k: item.get(k, "") for k in ("item_id",) + SHEET_FIELDS} | {"label": got["label"] if got else "", "note": got["note"] if got else ""})
        return "﻿" + out.getvalue()
