"""Offline multi-KB import/review invariants (HTTP behaviour lives in test_web_api.py)."""

from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from legal_ai.common.io import canonical, digest
from legal_ai.kb.import_review import Conflict, ReviewStore, empty_graph
from legal_ai.validation.evidence import check_evidence

SOURCE = "Điều 1. Ví dụ tổng hợp, không phải luật thật\n1. Người lao động phải thông báo kết quả thử việc cho người sử dụng lao động.\n2. Người lao động có quyền nghỉ việc.\n"
OTHER = SOURCE.replace("Điều 1.", "Điều 2.")


class ImportReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "demo.sqlite"
        self.store = ReviewStore(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def prepare(self, text=SOURCE, target=None):
        return self.store.prepare("SYNTHETIC - NOT REAL LAW", text, synthetic=True,
                                  target=target or {"mode": "new", "name": "Kho thử", "data_class": "public"})

    def decisions(self, draft, choice="approve"):
        return {n["id"]: choice for n in draft["graph"]["nodes"] if n["kind"] == "NormClaim"}

    def publish(self, draft, decisions=None, links=None):
        return self.store.publish(draft["id"], "Reviewer", "Synthetic offline test",
                                  decisions=self.decisions(draft) if decisions is None else decisions, links=links)

    def kb(self, name="Kho thử"):
        return next(k for k in self.store.knowledge_bases() if k["name"] == name)

    def test_new_store_has_no_kb_and_prepare_never_creates_one(self):
        self.assertEqual(self.store.knowledge_bases(), [])
        draft = self.prepare()
        self.assertEqual(self.store.knowledge_bases(), [])
        self.assertEqual(draft["raw_text"], SOURCE)
        self.assertTrue(self.decisions(draft))
        units = [n["payload"] for n in draft["graph"]["nodes"] if n["kind"] == "LegalUnit"]
        for node in draft["graph"]["nodes"]:
            if node["kind"] == "Evidence":
                self.assertEqual(check_evidence(node["payload"], units), [])
        self.store.discard(draft["id"])
        self.assertEqual(self.store.knowledge_bases(), [])
        with self.assertRaises(ValueError):
            self.publish(draft)

    def test_requires_complete_review_and_nonempty_approval(self):
        draft = self.prepare()
        for decisions in ({}, self.decisions(draft, "reject"), self.decisions(draft, "accepted")):
            with self.assertRaises(ValueError):
                self.publish(draft, decisions)
        self.assertEqual(self.store.knowledge_bases(), [])

    def test_publish_new_kb_then_merge_rejected_claim_excluded_old_revision_immutable(self):
        first = self.publish(self.prepare())
        kb = self.kb()
        self.assertEqual(first["kb_id"], kb["id"])
        self.assertIsNone(first["parent"])
        draft = self.prepare(OTHER, {"mode": "merge", "kb_id": kb["id"]})
        decisions = self.decisions(draft)
        rejected = next(iter(decisions))
        decisions[rejected] = "reject"
        revision = self.publish(draft, decisions)
        self.assertEqual(revision["parent"], first["id"])
        self.assertEqual(self.store.revision(first["id"]), first)
        self.assertFalse(any(n["id"] == rejected or n["id"].startswith(rejected + "/") for n in revision["graph"]["nodes"]))
        reopened = ReviewStore(self.path)
        self.assertEqual(reopened.current(kb["id"]), revision)
        self.assertEqual(reopened.draft(draft["id"])["status"], "merged")
        with self.assertRaises(ValueError):
            self.publish(draft, decisions)
        with self.assertRaisesRegex(ValueError, "đã có"):
            self.prepare(OTHER, {"mode": "merge", "kb_id": kb["id"]})

    def test_structure_problems_are_rejected_before_a_draft(self):
        with self.assertRaisesRegex(ValueError, "heading trùng"):
            self.prepare("Điều 1. Một\n1. Khoản.\n1. Khoản lặp.\n")
        with self.assertRaisesRegex(ValueError, "sửa đổi văn bản khác"):
            self.prepare("Điều 1. Sửa đổi\n1. Sửa đổi khoản 2 Điều 3 như sau:\n“2. Nội dung mới.”\n")

    def test_kb_names_unique_and_revisions_scoped_to_their_kb(self):
        a = self.publish(self.prepare())
        with self.assertRaisesRegex(ValueError, "cùng tên"):
            self.prepare(OTHER, {"mode": "new", "name": "  kho THỬ "})
        b = self.publish(self.prepare(OTHER, {"mode": "new", "name": "Kho khác", "data_class": "private"}))
        self.assertNotEqual(a["kb_id"], b["kb_id"])
        with self.assertRaisesRegex(ValueError, "không thuộc"):
            self.store.revision(a["id"], b["kb_id"])
        for target in (None, {"mode": "merge", "kb_id": "missing"}, {"mode": "new", "name": ""},
                       {"mode": "new", "name": "x", "data_class": "secret"}):
            with self.assertRaises(ValueError):
                self.prepare(SOURCE.replace("Điều 1.", "Điều 3."), target)

    def test_two_new_kb_drafts_with_same_name_cannot_both_publish(self):
        first, second = self.prepare(), self.prepare(OTHER)
        self.publish(first)
        with self.assertRaisesRegex(ValueError, "cùng tên"):
            self.publish(second)

    def test_stale_merge_draft_gets_conflict(self):
        kb = self.publish(self.prepare())["kb_id"]
        first = self.prepare(OTHER, {"mode": "merge", "kb_id": kb})
        second = self.prepare(SOURCE.replace("Điều 1.", "Điều 3."), {"mode": "merge", "kb_id": kb})
        self.publish(first)
        with self.assertRaises(Conflict):
            self.publish(second)
        self.assertEqual(len(self.store.knowledge_base(kb)["revisions"]), 2)

    def test_saved_decisions_resume_and_batch_approve_article(self):
        draft = self.prepare()
        claims = list(self.decisions(draft))
        view = self.store.review(draft["id"], claims[0], "reject")
        self.assertEqual(view["progress"]["rejected"], 1)
        reopened = ReviewStore(self.path).draft_view(draft["id"])
        self.assertEqual(reopened["progress"]["rejected"], 1)
        view = self.store.review(draft["id"], None, "approve_article", {"article_id": view["articles"][0]["id"]})
        self.assertEqual(view["progress"]["undecided"], 0)
        modes = {c["id"]: (c["decision"], c["decision_mode"]) for c in view["claims"]}
        self.assertEqual(modes[claims[0]], ("reject", "single"))
        self.assertTrue(all(m == ("approve", "batch") for k, m in modes.items() if k != claims[0]))
        revision = self.store.publish(draft["id"], "Reviewer", "batch")
        approved = [n for n in revision["graph"]["nodes"] if n["kind"] == "NormClaim"]
        self.assertTrue(approved and all(n["payload"]["human_review"]["decision_mode"] == "batch" for n in approved))
        with self.assertRaises(ValueError):
            self.store.review(draft["id"], claims[0], "approve")

    def test_curated_slot_edit_keeps_machine_claim_and_exact_source_quote(self):
        draft = self.prepare()
        view = self.store.draft_view(draft["id"])
        claim = view["claims"][0]
        unit = next(u for a in view["articles"] for u in a["units"] if u["unit_version_id"] == claim["source_unit_version_ids"][0])
        quote = "kết quả thử việc"
        start = unit["text"].index(quote)
        edit = {"field": "slot", "slot": "object", "state": "present", "unit_version_id": unit["unit_version_id"], "start": start, "end": start + len(quote)}
        for bad in ({**edit, "end": len(unit["text"]) + 5}, {**edit, "unit_version_id": "other"}, {**edit, "start": start - 1},
                    {**edit, "slot": "secret"}, {"field": "modality", "modality": "obligation"}):
            with self.assertRaises(ValueError):
                self.store.review(draft["id"], claim["id"], "edit", bad)
        view = self.store.review(draft["id"], claim["id"], "edit", edit)
        edited = next(c for c in view["claims"] if c["id"] == claim["id"])
        self.assertTrue(edited["edited"])
        self.assertEqual(edited["slots"]["object"]["text"], quote)
        self.assertEqual(edited["decision"], "approve")
        self.store.review(draft["id"], claim["id"], "edit", {"field": "note", "text": "Ghi chú người duyệt"})
        for other in self.decisions(draft):
            if other != claim["id"]:
                self.store.review(draft["id"], other, "approve")
        revision = self.store.publish(draft["id"], "Reviewer", "edit")
        self.assertIn(claim["id"], {n["id"] for n in draft["graph"]["nodes"]})
        self.assertNotIn(claim["id"], {n["id"] for n in revision["graph"]["nodes"]})
        node = next(n for n in revision["graph"]["nodes"] if n["kind"] == "NormClaim" and n["payload"].get("curation"))
        self.assertEqual(node["payload"]["curation"]["derived_from"], claim["id"])
        self.assertEqual(node["payload"]["curation"]["reviewer_note"], "Ghi chú người duyệt")
        self.assertTrue(node["payload"]["human_review"]["edited"])
        self.assertEqual(node["payload"]["slots"]["object"]["text"], quote)
        units = [n["payload"] for n in revision["graph"]["nodes"] if n["kind"] == "LegalUnit"]
        for n in revision["graph"]["nodes"]:
            if n["kind"] == "Evidence":
                self.assertEqual(check_evidence(n["payload"], units), [])
        self.assertIn(node["id"] + "/slot/object", {n["id"] for n in revision["graph"]["nodes"]})

    def test_restore_drops_curated_edit(self):
        draft = self.prepare()
        claim = self.store.draft_view(draft["id"])["claims"][0]
        self.store.review(draft["id"], claim["id"], "edit", {"field": "slot", "slot": "object", "state": "unknown"})
        view = self.store.review(draft["id"], claim["id"], "edit", {"field": "restore"})
        self.assertFalse(next(c for c in view["claims"] if c["id"] == claim["id"])["edited"])

    def test_entity_links_require_review_and_keep_both_mentions(self):
        kb = self.publish(self.prepare())["kb_id"]
        draft = self.prepare(OTHER, {"mode": "merge", "kb_id": kb})
        source = next(n for n in draft["graph"]["nodes"] if n["kind"] == "Entity" and draft["suggestions"][n["id"]])
        target = draft["suggestions"][source["id"]][0]
        original = deepcopy(self.store.current(kb))
        self.assertFalse(any(e["kind"] == "REVIEWED_ENTITY_LINK" for e in draft["graph"]["edges"]))
        with self.assertRaises(ValueError):
            self.store.review(draft["id"], source["id"], "link", {"target": "missing"})
        view = self.store.review(draft["id"], source["id"], "link", {"target": target})
        self.assertEqual(next(e for e in view["entities"] if e["id"] == source["id"])["target"], target)
        revision = self.publish(draft)
        ids = {n["id"] for n in revision["graph"]["nodes"]}
        self.assertIn(source["id"], ids)
        self.assertIn(target, ids)
        edge = next(e for e in revision["graph"]["edges"] if e["kind"] == "REVIEWED_ENTITY_LINK")
        self.assertEqual(edge["target"], target)
        self.assertEqual(self.store.revision(original["id"]), original)
        evidence = {n["payload"]["evidence_id"] for n in revision["graph"]["nodes"] if n["kind"] == "Evidence"}
        for e in revision["graph"]["edges"]:
            self.assertIn(e["source"], ids)
            self.assertIn(e["target"], ids)
            self.assertTrue(set(e["evidence_ids"]) <= evidence)
        content = {k: revision["graph"][k] for k in ("graph_version", "nodes", "edges", "references", "extraction_report")}
        self.assertEqual(digest(canonical(content)), revision["graph"]["graph_hash"])

    def test_invalid_entity_target_cannot_publish(self):
        draft = self.prepare()
        source = next(n for n in draft["graph"]["nodes"] if n["kind"] == "Entity")
        with self.assertRaises(ValueError):
            self.publish(draft, links={source["id"]: "missing"})
        self.assertEqual(self.store.knowledge_bases(), [])

    def test_diff_reports_duplicates_and_counts(self):
        kb = self.publish(self.prepare())["kb_id"]
        draft = self.prepare(OTHER, {"mode": "merge", "kb_id": kb})
        for claim in self.decisions(draft):
            self.store.review(draft["id"], claim, "approve")
        diff = self.store.draft_view(draft["id"])["diff"]
        self.assertEqual((diff["documents_before"], diff["documents_after"]), (1, 2))
        self.assertEqual(diff["claims_after"], diff["claims_before"] + diff["approved"])
        self.assertEqual(diff["duplicates"], diff["approved"])
        self.assertTrue(diff["warnings"])

    def test_input_failures_are_actionable(self):
        target = {"mode": "new", "name": "x"}
        for title, text in (("", SOURCE), ("x", ""), ("x", "x" * 1_000_001), ("x", "Không có heading"),
                            ("x", "Điều 1. Một\nNội dung\nĐiều 1. Trùng\nKhác"), ("x", "1. Khoản thiếu điều")):
            with self.assertRaises(ValueError):
                self.store.prepare(title, text, target=target)

    def test_seed_copied_once_into_default_kb_and_never_modified(self):
        revision = self.publish(self.prepare())
        seed = Path(self.temp.name) / "seed.json"
        seed.write_text(json.dumps(revision["graph"]), encoding="utf-8")
        before = seed.read_bytes()
        store = ReviewStore(Path(self.temp.name) / "seeded.sqlite", seed)
        [kb] = store.knowledge_bases()
        self.assertEqual(store.current(kb["id"])["graph"], revision["graph"])
        self.assertEqual(seed.read_bytes(), before)
        again = ReviewStore(store.path, "missing-ignored-seed.json")
        self.assertEqual(again.current(kb["id"]), store.current(kb["id"]))

    def test_legacy_single_chain_store_migrates_to_default_kb(self):
        path = Path(self.temp.name) / "legacy.sqlite"
        legacy = {"schema_version": "import-review-v1", "id": "r1", "parent": None, "created_at": "2026-11-01T00:00:00+00:00",
                  "reviewer": None, "reason": "Initial", "graph": empty_graph(), "review": None}
        draft = {"id": "d1", "title": "old", "status": "draft", "created_at": "2026-11-01T00:00:00+00:00", "base_revision": "r1",
                 "graph": empty_graph()}
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE revisions (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            db.execute("CREATE TABLE drafts (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            db.execute("INSERT INTO revisions VALUES (?, ?)", ("r1", canonical(legacy)))
            db.execute("INSERT INTO drafts VALUES (?, ?)", ("d1", canonical(draft)))
        store = ReviewStore(path)
        [kb] = store.knowledge_bases()
        self.assertEqual(kb["current_revision"], "r1")
        self.assertEqual(store.revision("r1", kb["id"])["graph"], legacy["graph"])
        self.assertEqual(store.draft("d1")["target"], {"mode": "merge", "kb_id": kb["id"]})
        with closing(sqlite3.connect(path)) as db, db:
            self.assertEqual(json.loads(db.execute("SELECT body FROM revisions").fetchone()[0]), legacy)
        self.assertEqual(len(ReviewStore(path).knowledge_bases()), 1)


if __name__ == "__main__":
    unittest.main()
