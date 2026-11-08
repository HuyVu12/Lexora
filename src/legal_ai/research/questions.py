"""Question sets for the DK1-DK4 evaluation (`questions-store-v1`), labelled by two annotators independently.

A question set is bound to one frozen corpus version, so every relevant unit ID resolves against fixed text.
Questions are written by a person or drafted by a model and accepted by a person; either way the origin is
kept. Each annotator labels on their own machine: question type, expected behaviour (answer or refuse), the
relevant canonical units and a note. When an annotator chose to see model proposals, each field records
whether the proposal was kept or changed, so agreement can be reported honestly (seeing the same proposal
raises agreement). A question pack moves the corpus version and the questions to the other machine; label
files move back. Adjudication compares the two annotators (Cohen's kappa for the categories, Dice for unit
sets), records one final label per question, and freezing assigns dev/held-out splits by paraphrase family,
stratified by question type, with a recorded seed. Labels are human research annotations, not legal advice.
"""

from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import sqlite3
import threading

from legal_ai.common.io import canonical, digest

STORE_VERSION = "questions-store-v1"
PACK_FORMAT = "lexora-question-pack-v1"
LABELS_FORMAT = "lexora-labels-v1"
QUESTIONS_FORMAT = "lexora-questions-v1"
QUESTION_TYPES = ("lookup", "synthesis", "temporal", "out_of_scope")
STATUSES = ("answer", "refuse")
FIELDS = ("question_type", "expected_status", "relevant_unit_ids")
SCHEMA = """
CREATE TABLE IF NOT EXISTS question_sets (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, corpus_version_id TEXT NOT NULL, guideline TEXT NOT NULL,
  created_by TEXT NOT NULL, created_at TEXT NOT NULL, imported INTEGER NOT NULL, frozen TEXT);
CREATE TABLE IF NOT EXISTS questions (
  id TEXT PRIMARY KEY, set_id TEXT NOT NULL REFERENCES question_sets(id), position INTEGER NOT NULL, text TEXT NOT NULL,
  family_id TEXT NOT NULL, origin TEXT NOT NULL, origin_detail TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL, removed_at TEXT);
CREATE TABLE IF NOT EXISTS question_proposals (
  id TEXT PRIMARY KEY, set_id TEXT NOT NULL, question_id TEXT NOT NULL, fields TEXT NOT NULL, rationale TEXT NOT NULL,
  candidates TEXT NOT NULL, call TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS question_labels (
  set_id TEXT NOT NULL, question_id TEXT NOT NULL, annotator TEXT NOT NULL, annotator_name TEXT NOT NULL, imported INTEGER NOT NULL,
  fields TEXT NOT NULL, note TEXT NOT NULL, provenance TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY (set_id, question_id, annotator));
CREATE TABLE IF NOT EXISTS question_annotators (
  set_id TEXT NOT NULL, annotator TEXT NOT NULL, show_proposals INTEGER NOT NULL, PRIMARY KEY (set_id, annotator));
CREATE TABLE IF NOT EXISTS question_calls (
  id TEXT PRIMARY KEY, set_id TEXT NOT NULL, purpose TEXT NOT NULL, record TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS question_drafts (
  id TEXT PRIMARY KEY, set_id TEXT NOT NULL, call_id TEXT NOT NULL, unit_ids TEXT NOT NULL, drafts TEXT NOT NULL, accepted TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS question_adjudications (
  set_id TEXT NOT NULL, question_id TEXT NOT NULL, fields TEXT NOT NULL, note TEXT NOT NULL, decided_by TEXT NOT NULL,
  decided_at TEXT NOT NULL, PRIMARY KEY (set_id, question_id));
"""


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def kappa(first, second):
    """Cohen's kappa of two equal-length label lists; None without items, 1.0 when both agree on one label only."""
    if len(first) != len(second):
        raise ValueError("kappa needs paired labels")
    n = len(first)
    if not n:
        return None
    observed = sum(a == b for a, b in zip(first, second)) / n
    left, right = Counter(first), Counter(second)
    expected = sum(left[label] * right[label] for label in set(left) | set(right)) / (n * n)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def dice(first, second):
    first, second = set(first), set(second)
    return 1.0 if not first and not second else 2 * len(first & second) / (len(first) + len(second))


class QuestionStore:
    def __init__(self, path, corpora):
        self.path, self.corpora = Path(path), corpora
        self._lock = threading.Lock()
        with closing(self._connect()) as db, db:
            db.executescript(SCHEMA)

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def _units(self, version_id):
        _, units, _ = self.corpora.bundle(version_id)
        return {u["unit_id"]: u for u in units}

    def _set_row(self, db, set_id):
        row = db.execute("SELECT * FROM question_sets WHERE id = ?", (set_id,)).fetchone()
        if row is None:
            raise ValueError("Không tìm thấy bộ câu hỏi")
        return row

    @staticmethod
    def _open(row):
        if row["frozen"]:
            raise ValueError("Bộ câu hỏi đã khóa; không sửa được nữa")

    # Sets and questions ----------------------------------------------------------------
    def create(self, name, corpus_version_id, guideline, actor):
        name, guideline = (name or "").strip(), (guideline or "").strip()
        if not 1 <= len(name) <= 120 or len(guideline) > 20000:
            raise ValueError("Tên bộ câu hỏi cần 1-120 ký tự; hướng dẫn gán nhãn tối đa 20000 ký tự")
        self.corpora.version(corpus_version_id)
        set_id = "q" + secrets.token_hex(6)
        with self._lock, closing(self._connect()) as db, db:
            db.execute("INSERT INTO question_sets VALUES (?,?,?,?,?,?,?,?)", (set_id, name, corpus_version_id, guideline, actor, _now(), 0, None))
        return self.summary(set_id)

    def sets(self):
        with closing(self._connect()) as db:
            rows = db.execute("""SELECT s.*, (SELECT COUNT(*) FROM questions q WHERE q.set_id = s.id AND q.removed_at IS NULL) AS questions
                                 FROM question_sets s ORDER BY s.created_at DESC, s.id""").fetchall()
        return [self._set_summary(r) for r in rows]

    def _set_summary(self, row):
        version = self.corpora.version(row["corpus_version_id"])
        return {"id": row["id"], "name": row["name"], "corpus_version_id": row["corpus_version_id"], "corpus_id": version["corpus_id"],
                "corpus_version": version["number"], "guideline": row["guideline"], "created_by": row["created_by"], "created_at": row["created_at"],
                "imported": bool(row["imported"]), "frozen": json.loads(row["frozen"]) if row["frozen"] else None,
                "questions": row["questions"] if "questions" in row.keys() else None}

    def summary(self, set_id):
        with closing(self._connect()) as db:
            row = db.execute("""SELECT s.*, (SELECT COUNT(*) FROM questions q WHERE q.set_id = s.id AND q.removed_at IS NULL) AS questions
                                FROM question_sets s WHERE s.id = ?""", (set_id,)).fetchone()
        if row is None:
            raise ValueError("Không tìm thấy bộ câu hỏi")
        return self._set_summary(row)

    def add_question(self, set_id, text, actor, family_id=None, origin="human", origin_detail=None):
        text = (text or "").strip()
        if not 3 <= len(text) <= 1000:
            raise ValueError("Câu hỏi cần 3-1000 ký tự")
        if origin not in {"human", "model"}:
            raise ValueError("origin must be human or model")
        question_id = "qq" + secrets.token_hex(6)
        with self._lock, closing(self._connect()) as db, db:
            self._open(self._set_row(db, set_id))
            if family_id and db.execute("SELECT 1 FROM questions WHERE set_id = ? AND family_id = ? AND removed_at IS NULL",
                                        (set_id, family_id)).fetchone() is None:
                raise ValueError("Không có nhóm diễn đạt này trong bộ câu hỏi")
            if db.execute("SELECT 1 FROM questions WHERE set_id = ? AND text = ? AND removed_at IS NULL", (set_id, text)).fetchone():
                raise ValueError("Câu hỏi này đã có trong bộ")
            position = db.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM questions WHERE set_id = ?", (set_id,)).fetchone()[0]
            db.execute("INSERT INTO questions VALUES (?,?,?,?,?,?,?,?,?,?)", (question_id, set_id, position, text, family_id or "f" + question_id[2:],
                                                                              origin, canonical(origin_detail or {}), actor, _now(), None))
        return self.question(question_id)

    def remove_question(self, set_id, question_id):
        with self._lock, closing(self._connect()) as db, db:
            self._open(self._set_row(db, set_id))
            if not db.execute("UPDATE questions SET removed_at = ? WHERE id = ? AND set_id = ? AND removed_at IS NULL", (_now(), question_id, set_id)).rowcount:
                raise ValueError("Không tìm thấy câu hỏi")

    def question(self, question_id):
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
        if row is None:
            raise ValueError("Không tìm thấy câu hỏi")
        return self._question(row)

    @staticmethod
    def _question(row):
        return {"id": row["id"], "position": row["position"], "text": row["text"], "family_id": row["family_id"], "origin": row["origin"],
                "origin_detail": json.loads(row["origin_detail"]), "created_by": row["created_by"], "created_at": row["created_at"]}

    def _questions(self, db, set_id):
        return [self._question(r) for r in db.execute("SELECT * FROM questions WHERE set_id = ? AND removed_at IS NULL ORDER BY position", (set_id,))]

    # Annotators, proposals and labels --------------------------------------------------
    def set_mode(self, set_id, annotator, show_proposals):
        """Choose once, before labelling, whether model proposals are shown to this annotator."""
        with self._lock, closing(self._connect()) as db, db:
            self._open(self._set_row(db, set_id))
            current = db.execute("SELECT show_proposals FROM question_annotators WHERE set_id = ? AND annotator = ?", (set_id, annotator)).fetchone()
            labelled = db.execute("SELECT 1 FROM question_labels WHERE set_id = ? AND annotator = ?", (set_id, annotator)).fetchone()
            if current is not None and labelled and bool(current[0]) != bool(show_proposals):
                raise ValueError("Đã gán nhãn rồi thì không đổi chế độ hiện đề xuất được")
            db.execute("INSERT OR REPLACE INTO question_annotators VALUES (?,?,?)", (set_id, annotator, int(bool(show_proposals))))

    def mode(self, set_id, annotator):
        with closing(self._connect()) as db:
            row = db.execute("SELECT show_proposals FROM question_annotators WHERE set_id = ? AND annotator = ?", (set_id, annotator)).fetchone()
        return None if row is None else bool(row[0])

    def add_proposal(self, set_id, question_id, fields, rationale, candidates, call):
        """Store a model proposal; unit IDs outside the corpus version are dropped, never stored."""
        with closing(self._connect()) as db:
            row = self._set_row(db, set_id)
        known = self._units(row["corpus_version_id"])
        clean = self._clean_fields(fields, known, strict=False)
        proposal_id = "p" + secrets.token_hex(6)
        with self._lock, closing(self._connect()) as db, db:
            if db.execute("SELECT 1 FROM questions WHERE id = ? AND set_id = ?", (question_id, set_id)).fetchone() is None:
                raise ValueError("Không tìm thấy câu hỏi")
            db.execute("INSERT INTO question_proposals VALUES (?,?,?,?,?,?,?,?)", (proposal_id, set_id, question_id, canonical(clean), (rationale or "")[:2000],
                                                                                   canonical(candidates), canonical(call), _now()))
        return {"id": proposal_id, "fields": clean, "rationale": rationale}

    def import_drafts(self, set_id, items, actor, author):
        """Add model-drafted questions with their proposed labels, all strictly checked before anything is written.

        Each item: text, question_type, expected_status, relevant_unit_ids, rationale and `paraphrase_of` (index of an
        earlier item, which puts both in one paraphrase family). Questions get origin `model` with the author; the labels
        are stored as proposals, never as labels, so the two annotators still label every question themselves."""
        with closing(self._connect()) as db:
            row = self._set_row(db, set_id)
            self._open(row)
        known = self._units(row["corpus_version_id"])
        if not isinstance(items, list) or not items:
            raise ValueError("Tệp nháp cần một danh sách câu hỏi")
        with closing(self._connect()) as db:
            texts = {q["text"] for q in self._questions(db, set_id)}
        for n, item in enumerate(items):
            text = item.get("text")
            if not isinstance(text, str) or not text.strip() or text in texts:
                raise ValueError(f"Câu {n}: câu hỏi rỗng hoặc trùng với câu đã có")
            texts.add(text)
            self._clean_fields(item, known, strict=True)  # Unknown unit IDs or missing labels stop the whole import.
            if item.get("expected_status") == "refuse" and item.get("relevant_unit_ids"):
                raise ValueError(f"Câu {n}: câu cần từ chối không có đơn vị liên quan")
            source = item.get("paraphrase_of")
            if source is not None and not (isinstance(source, int) and 0 <= source < n):
                raise ValueError(f"Câu {n}: paraphrase_of phải trỏ tới một câu đứng trước")
        added = []
        for n, item in enumerate(items):
            source = item.get("paraphrase_of")
            question = self.add_question(set_id, item["text"], actor, family_id=added[source]["family_id"] if source is not None else None,
                                         origin="model", origin_detail={"author": author, "draft_index": n, "batch": item.get("batch")})
            self.add_proposal(set_id, question["id"], item, item.get("rationale", ""), [], {"model": author, "purpose": "question-draft-labels"})
            added.append(question)
        return {"added": len(added), "families": len({q["family_id"] for q in added})}

    def _latest_proposal(self, db, set_id, question_id):
        row = db.execute("SELECT * FROM question_proposals WHERE set_id = ? AND question_id = ? ORDER BY created_at DESC, rowid DESC LIMIT 1",
                         (set_id, question_id)).fetchone()
        return None if row is None else {"id": row["id"], "fields": json.loads(row["fields"]), "rationale": row["rationale"],
                                         "candidates": json.loads(row["candidates"]), "created_at": row["created_at"]}

    @staticmethod
    def _clean_fields(fields, known, strict=True):
        fields = fields or {}
        kind, status = fields.get("question_type"), fields.get("expected_status")
        units = fields.get("relevant_unit_ids") or []
        if strict and (kind not in QUESTION_TYPES or status not in STATUSES):
            raise ValueError("Chọn loại câu hỏi và hành vi mong đợi")
        if not isinstance(units, list) or not all(isinstance(u, str) for u in units):
            raise ValueError("relevant_unit_ids must be a list of unit IDs")
        missing = [u for u in units if u not in known]
        if strict and missing:
            raise ValueError(f"Đơn vị không có trong phiên bản corpus: {missing[0]}")
        units = list(dict.fromkeys(u for u in units if u in known))
        if strict and status == "answer" and not units:
            raise ValueError("Câu trả lời được cần ít nhất một đơn vị liên quan")
        return {"question_type": kind if kind in QUESTION_TYPES else None, "expected_status": status if status in STATUSES else None,
                "relevant_unit_ids": units}

    def save_label(self, set_id, question_id, annotator, annotator_name, fields, note=""):
        with closing(self._connect()) as db:
            row = self._set_row(db, set_id)
            self._open(row)
            if db.execute("SELECT 1 FROM questions WHERE id = ? AND set_id = ? AND removed_at IS NULL", (question_id, set_id)).fetchone() is None:
                raise ValueError("Không tìm thấy câu hỏi")
            proposal = self._latest_proposal(db, set_id, question_id)
        shown = self.mode(set_id, annotator)
        if shown is None:
            raise ValueError("Hãy chọn có hiện đề xuất của model hay không trước khi gán nhãn")
        clean = self._clean_fields(fields, self._units(row["corpus_version_id"]))
        decisions = {}
        for field in FIELDS:
            if not shown or proposal is None:
                decisions[field] = "own"
            else:
                same = sorted(proposal["fields"][field]) == sorted(clean[field]) if field == "relevant_unit_ids" else proposal["fields"][field] == clean[field]
                decisions[field] = "kept" if same else "changed"
        provenance = {"proposals_shown": shown, "proposal_id": proposal["id"] if shown and proposal else None, "decisions": decisions}
        with self._lock, closing(self._connect()) as db, db:
            db.execute("INSERT OR REPLACE INTO question_labels VALUES (?,?,?,?,?,?,?,?,?)", (set_id, question_id, annotator, annotator_name, 0,
                                                                                          canonical(clean), (note or "")[:2000], canonical(provenance), _now()))
        return {"fields": clean, "note": note, "provenance": provenance}

    def workspace(self, set_id, annotator):
        """Everything the annotation screen needs for one annotator: questions with their own label and,
        only in proposal mode, the latest proposal."""
        with closing(self._connect()) as db:
            row = self._set_row(db, set_id)
            questions = self._questions(db, set_id)
            labels = {r["question_id"]: r for r in db.execute("SELECT * FROM question_labels WHERE set_id = ? AND annotator = ?", (set_id, annotator))}
            shown = self.mode(set_id, annotator)
            items = []
            for q in questions:
                label = labels.get(q["id"])
                items.append(q | {"label": None if label is None else {"fields": json.loads(label["fields"]), "note": label["note"],
                                                                        "provenance": json.loads(label["provenance"]), "updated_at": label["updated_at"]},
                                  "proposal": self._latest_proposal(db, set_id, q["id"]) if shown else None})
        return self._set_summary(dict(row) | {"questions": len(questions)}) | {"show_proposals": shown, "items": items,
                                                                              "labelled": sum(1 for i in items if i["label"])}

    # Model calls and drafts -----------------------------------------------------------
    def log_call(self, set_id, record):
        """Keep one model call (successful or not) of this set; returns its ID."""
        call_id = "m" + secrets.token_hex(6)
        with self._lock, closing(self._connect()) as db, db:
            self._set_row(db, set_id)
            db.execute("INSERT INTO question_calls VALUES (?,?,?,?,?)", (call_id, set_id, record.get("purpose", ""), canonical(record), _now()))
        return call_id

    def calls(self, set_id):
        with closing(self._connect()) as db:
            return [{"id": r["id"], "purpose": r["purpose"], "created_at": r["created_at"]} | json.loads(r["record"])
                    for r in db.execute("SELECT * FROM question_calls WHERE set_id = ? ORDER BY created_at, rowid", (set_id,))]

    def save_drafts(self, set_id, call_id, unit_ids, drafts):
        draft_id = "dr" + secrets.token_hex(6)
        with self._lock, closing(self._connect()) as db, db:
            self._open(self._set_row(db, set_id))
            db.execute("INSERT INTO question_drafts VALUES (?,?,?,?,?,?,?)", (draft_id, set_id, call_id, canonical(unit_ids), canonical(drafts), "[]", _now()))
        return self.draft(draft_id)

    def draft(self, draft_id):
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM question_drafts WHERE id = ?", (draft_id,)).fetchone()
        if row is None:
            raise ValueError("Không tìm thấy bản nháp câu hỏi")
        return {"id": row["id"], "set_id": row["set_id"], "call_id": row["call_id"], "unit_ids": json.loads(row["unit_ids"]),
                "drafts": json.loads(row["drafts"]), "accepted": json.loads(row["accepted"]), "created_at": row["created_at"]}

    def accept_draft(self, set_id, draft_id, index, texts, actor):
        """Add draft `index` as model-origin questions (the first text, then paraphrases in the same family), each with
        the draft's labels as its proposal. `texts` are the reviewer's final wording; edits are recorded."""
        draft = self.draft(draft_id)
        if draft["set_id"] != set_id:
            raise ValueError("Bản nháp thuộc bộ câu hỏi khác")
        if not 0 <= index < len(draft["drafts"]) or index in draft["accepted"]:
            raise ValueError("Câu nháp không tồn tại hoặc đã được thêm")
        item = draft["drafts"][index]
        offered = [item["text"]] + item.get("paraphrases", [])
        texts = [t.strip() for t in texts if t and t.strip()]
        if not texts:
            raise ValueError("Cần ít nhất một câu hỏi")
        added, family = [], None
        for n, text in enumerate(texts):
            detail = {"call_id": draft["call_id"], "draft_id": draft_id, "draft_index": index, "edited": text not in offered}
            question = self.add_question(set_id, text, actor, family_id=family, origin="model", origin_detail=detail)
            family = question["family_id"]
            self.add_proposal(set_id, question["id"], {"question_type": item["question_type"], "expected_status": "answer",
                                                       "relevant_unit_ids": item["relevant_unit_ids"]}, item.get("rationale", ""),
                              draft["unit_ids"], {"call_id": draft["call_id"], "source": "draft"})
            added.append(question)
        with self._lock, closing(self._connect()) as db, db:
            db.execute("UPDATE question_drafts SET accepted = ? WHERE id = ?", (canonical(sorted(draft["accepted"] + [index])), draft_id))
        return added

    # Moving work between machines ------------------------------------------------------
    def export_pack(self, set_id):
        """The corpus version and the questions, for the second annotator's machine. No labels or proposals."""
        with closing(self._connect()) as db:
            row = self._set_row(db, set_id)
            questions = self._questions(db, set_id)
        body = {"format": PACK_FORMAT, "set": {"id": row["id"], "name": row["name"], "guideline": row["guideline"], "created_by": row["created_by"],
                                               "created_at": row["created_at"], "corpus_version_id": row["corpus_version_id"]},
                "questions": [{k: q[k] for k in ("id", "position", "text", "family_id", "origin", "created_by", "created_at")} for q in questions],
                "corpus": self.corpora.version_payload(row["corpus_version_id"]), "exported_at": _now()}
        return body | {"questions_sha256": digest(canonical(body["questions"]))}

    def import_pack(self, pack, actor):
        if pack.get("format") != PACK_FORMAT:
            raise ValueError("Tệp không phải gói câu hỏi Lexora")
        if digest(canonical(pack["questions"])) != pack.get("questions_sha256"):
            raise ValueError("Danh sách câu hỏi trong gói không khớp mã băm")
        info = pack["set"]
        version = self.corpora.import_version(pack["corpus"], actor)
        if version["id"] != info["corpus_version_id"]:
            raise ValueError("Gói câu hỏi trỏ tới phiên bản corpus khác")
        with self._lock, closing(self._connect()) as db, db:
            existing = db.execute("SELECT * FROM question_sets WHERE id = ?", (info["id"],)).fetchone()
            if existing is None:
                db.execute("INSERT INTO question_sets VALUES (?,?,?,?,?,?,?,?)", (info["id"], info["name"], info["corpus_version_id"], info["guideline"],
                                                                                 info["created_by"], info["created_at"], 1, None))
            elif existing["corpus_version_id"] != info["corpus_version_id"]:
                raise ValueError("Bộ câu hỏi trùng mã nhưng khác phiên bản corpus")
            else:
                self._open(existing)
            here = {r["id"] for r in db.execute("SELECT id FROM questions WHERE set_id = ?", (info["id"],))}
            for q in pack["questions"]:
                if q["id"] not in here:
                    db.execute("INSERT INTO questions VALUES (?,?,?,?,?,?,?,?,?,?)", (q["id"], info["id"], q["position"], q["text"], q["family_id"],
                                                                                      q["origin"], canonical({"imported": True}), q["created_by"], q["created_at"], None))
        return self.summary(info["id"])

    def export_labels(self, set_id, annotator):
        with closing(self._connect()) as db:
            row = self._set_row(db, set_id)
            labels = db.execute("SELECT * FROM question_labels WHERE set_id = ? AND annotator = ? AND imported = 0", (set_id, annotator)).fetchall()
            questions = {q["id"]: q for q in self._questions(db, set_id)}
        if not labels:
            raise ValueError("Bạn chưa gán nhãn câu nào trong bộ này")
        items = [{"question_id": l["question_id"], "question_sha256": digest(questions[l["question_id"]]["text"]), "fields": json.loads(l["fields"]),
                  "note": l["note"], "provenance": json.loads(l["provenance"]), "updated_at": l["updated_at"]}
                 for l in labels if l["question_id"] in questions]
        body = {"format": LABELS_FORMAT, "set_id": set_id, "corpus_version_id": row["corpus_version_id"], "annotator": annotator,
                "annotator_name": labels[0]["annotator_name"], "show_proposals": self.mode(set_id, annotator), "labels": items, "exported_at": _now()}
        return body | {"labels_sha256": digest(canonical(items))}

    def import_labels(self, payload, importer):
        if payload.get("format") != LABELS_FORMAT:
            raise ValueError("Tệp không phải tệp nhãn Lexora")
        if digest(canonical(payload["labels"])) != payload.get("labels_sha256"):
            raise ValueError("Tệp nhãn không khớp mã băm")
        set_id, annotator = payload["set_id"], payload["annotator"]
        if annotator == importer:
            raise ValueError("Đây là nhãn của chính bạn; hãy nhập tệp của người gán nhãn còn lại")
        with closing(self._connect()) as db:
            row = self._set_row(db, set_id)
            self._open(row)
            questions = {q["id"]: q for q in self._questions(db, set_id)}
        if payload["corpus_version_id"] != row["corpus_version_id"]:
            raise ValueError("Tệp nhãn thuộc phiên bản corpus khác")
        known = self._units(row["corpus_version_id"])
        rows = []
        for item in payload["labels"]:
            question = questions.get(item["question_id"])
            if question is None or digest(question["text"]) != item["question_sha256"]:
                raise ValueError("Tệp nhãn có câu hỏi không khớp bộ câu hỏi này")
            clean = self._clean_fields(item["fields"], known)
            rows.append((set_id, item["question_id"], annotator, payload["annotator_name"], 1, canonical(clean), item.get("note", ""),
                         canonical(item["provenance"]), item["updated_at"]))
        with self._lock, closing(self._connect()) as db, db:
            db.execute("DELETE FROM question_labels WHERE set_id = ? AND annotator = ? AND imported = 1", (set_id, annotator))
            db.executemany("INSERT OR REPLACE INTO question_labels VALUES (?,?,?,?,?,?,?,?,?)", rows)
        return {"annotator": annotator, "annotator_name": payload["annotator_name"], "labels": len(rows)}

    # Adjudication and freezing ---------------------------------------------------------
    def comparison(self, set_id, first, second):
        """Agreement between two annotators over questions both labelled, and every question side by side."""
        with closing(self._connect()) as db:
            self._set_row(db, set_id)
            questions = self._questions(db, set_id)
            labels = defaultdict(dict)
            names, modes = {}, {}
            for r in db.execute("SELECT * FROM question_labels WHERE set_id = ? AND annotator IN (?, ?)", (set_id, first, second)):
                labels[r["question_id"]][r["annotator"]] = json.loads(r["fields"]) | {"note": r["note"], "provenance": json.loads(r["provenance"])}
                names[r["annotator"]] = r["annotator_name"]
                modes[r["annotator"]] = json.loads(r["provenance"]).get("proposals_shown")
            final = {r["question_id"]: json.loads(r["fields"]) | {"note": r["note"], "decided_by": r["decided_by"]}
                     for r in db.execute("SELECT * FROM question_adjudications WHERE set_id = ?", (set_id,))}
        both = [q for q in questions if first in labels[q["id"]] and second in labels[q["id"]]]
        pair = lambda field: ([labels[q["id"]][first][field] for q in both], [labels[q["id"]][second][field] for q in both])
        dices = [dice(labels[q["id"]][first]["relevant_unit_ids"], labels[q["id"]][second]["relevant_unit_ids"]) for q in both]
        items = []
        for q in questions:
            a, b = labels[q["id"]].get(first), labels[q["id"]].get(second)
            agree = bool(a and b) and all(sorted(a[f]) == sorted(b[f]) if f == "relevant_unit_ids" else a[f] == b[f] for f in FIELDS)
            items.append(q | {"first": a, "second": b, "agree": agree, "final": final.get(q["id"])})
        return {"first": {"annotator": first, "name": names.get(first), "proposals_shown": modes.get(first)},
                "second": {"annotator": second, "name": names.get(second), "proposals_shown": modes.get(second)},
                "questions": len(questions), "labelled_by_both": len(both),
                "kappa_question_type": kappa(*pair("question_type")), "kappa_expected_status": kappa(*pair("expected_status")),
                "mean_unit_dice": sum(dices) / len(dices) if dices else None,
                "exact_unit_match": sum(d == 1.0 for d in dices) / len(dices) if dices else None,
                "full_agreement": sum(i["agree"] for i in items) / len(both) if both else None,
                "adjudicated": len(final), "items": items}

    def annotators(self, set_id):
        with closing(self._connect()) as db:
            return [dict(r) for r in db.execute("""SELECT annotator, annotator_name, MAX(imported) AS imported, COUNT(*) AS labels
                                                   FROM question_labels WHERE set_id = ? GROUP BY annotator, annotator_name ORDER BY annotator""", (set_id,))]

    def adjudicate(self, set_id, question_id, fields, note, actor):
        with closing(self._connect()) as db:
            row = self._set_row(db, set_id)
            self._open(row)
            if db.execute("SELECT 1 FROM questions WHERE id = ? AND set_id = ? AND removed_at IS NULL", (question_id, set_id)).fetchone() is None:
                raise ValueError("Không tìm thấy câu hỏi")
        clean = self._clean_fields(fields, self._units(row["corpus_version_id"]))
        with self._lock, closing(self._connect()) as db, db:
            db.execute("INSERT OR REPLACE INTO question_adjudications VALUES (?,?,?,?,?,?)", (set_id, question_id, canonical(clean), (note or "")[:2000], actor, _now()))
        return clean

    def freeze(self, set_id, first, second, actor, held_out=0.3, seed="lexora-split-v1"):
        """Lock the set: every question needs a final label; families go to dev or held-out, stratified by type."""
        if not 0 < held_out < 1:
            raise ValueError("held_out must be between 0 and 1")
        report = self.comparison(set_id, first, second)
        missing = [i["position"] for i in report["items"] if not i["final"]]
        if missing:
            raise ValueError(f"Còn {len(missing)} câu chưa chốt nhãn cuối (ví dụ câu {missing[0]})")
        families = defaultdict(list)
        for item in report["items"]:
            families[item["family_id"]].append(item)
        strata = defaultdict(list)
        for family, items in families.items():
            kind = Counter(i["final"]["question_type"] for i in items).most_common(1)[0][0]
            strata[kind].append(family)
        split = {}
        for kind, members in sorted(strata.items()):
            ordered = sorted(members, key=lambda f: digest(f"{seed}:{f}"))
            count = round(len(ordered) * held_out)
            for n, family in enumerate(ordered):
                split[family] = "held_out" if n < count else "dev"
        with closing(self._connect()) as db:
            row = self._set_row(db, set_id)
        version = self.corpora.version(row["corpus_version_id"])
        questions = [{"question_id": i["id"], "family_id": i["family_id"], "split": split[i["family_id"]], "question": i["text"],
                      "question_type": i["final"]["question_type"], "expected_status": i["final"]["expected_status"],
                      "relevant_unit_ids": i["final"]["relevant_unit_ids"], "origin": i["origin"], "annotation_status": "adjudicated"}
                     for i in report["items"]]
        agreement = {k: report[k] for k in ("labelled_by_both", "kappa_question_type", "kappa_expected_status", "mean_unit_dice", "exact_unit_match", "full_agreement")}
        frozen = {"format": QUESTIONS_FORMAT, "frozen_at": _now(), "frozen_by": actor, "seed": seed, "held_out_fraction": held_out,
                  "corpus_version_id": version["id"], "bundle_sha256": version["bundle_sha256"], "annotators": [report["first"], report["second"]],
                  "agreement": agreement, "counts": dict(Counter(q["split"] for q in questions)), "questions_sha256": digest(canonical(questions))}
        with self._lock, closing(self._connect()) as db, db:
            self._open(self._set_row(db, set_id))
            db.execute("UPDATE question_sets SET frozen = ? WHERE id = ?", (canonical(frozen | {"questions": questions}), set_id))
        return frozen

    def frozen_file(self, set_id):
        """The frozen question file, readable by `run-retrieval --questions`."""
        summary = self.summary(set_id)
        if not summary["frozen"]:
            raise ValueError("Bộ câu hỏi chưa khóa")
        frozen = summary["frozen"]
        return frozen | {"description": f"{summary['name']} (frozen {frozen['frozen_at']}); human annotations, not legal advice"}
