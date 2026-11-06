"""Offline import/review invariants and actual loopback HTTP round trips."""

from copy import deepcopy
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from legal_ai.common.io import canonical, digest
from legal_ai.demo import make_server
from legal_ai.kb.import_review import ReviewStore
from legal_ai.validation.evidence import check_evidence

SOURCE = "Điều 1. Ví dụ tổng hợp, không phải luật thật\n1. Người lao động phải thông báo kết quả thử việc cho người sử dụng lao động.\n2. Người lao động có quyền nghỉ việc.\n"


class ImportReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "demo.sqlite"
        self.store = ReviewStore(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def prepare(self, text=SOURCE):
        return self.store.prepare("SYNTHETIC — NOT REAL LAW", text, synthetic=True)

    def decisions(self, draft, choice="approve"):
        return {n["id"]: choice for n in draft["graph"]["nodes"] if n["kind"] == "NormClaim"}

    def publish(self, draft, decisions=None, links=None):
        return self.store.publish(draft["id"], self.decisions(draft) if decisions is None else decisions,
                                  links or {}, "Reviewer", "Synthetic offline test")

    def test_prepare_preserves_quotes_and_does_not_mutate_current(self):
        before = self.store.current()
        draft = self.prepare()
        self.assertEqual(self.store.current(), before)
        self.assertEqual(draft["raw_text"], SOURCE)
        self.assertTrue(self.decisions(draft))
        units = [n["payload"] for n in draft["graph"]["nodes"] if n["kind"] == "LegalUnit"]
        for node in draft["graph"]["nodes"]:
            if node["kind"] == "Evidence":
                self.assertEqual(check_evidence(node["payload"], units), [])

    def test_requires_complete_review_and_nonempty_approval(self):
        draft = self.prepare()
        for decisions in ({}, self.decisions(draft, "reject"), self.decisions(draft, "accepted")):
            with self.assertRaises(ValueError):
                self.publish(draft, decisions)
        self.assertEqual(len(self.store.state()["revisions"]), 1)

    def test_rejected_claim_and_slots_excluded_old_revision_immutable_restore(self):
        before = self.store.current()
        draft = self.prepare()
        decisions = self.decisions(draft)
        rejected = next(iter(decisions))
        decisions[rejected] = "reject"
        revision = self.publish(draft, decisions)
        self.assertEqual(revision["parent"], before["id"])
        self.assertEqual(self.store.revision(before["id"]), before)
        self.assertFalse(any(n["id"] == rejected or n["id"].startswith(rejected + "/") for n in revision["graph"]["nodes"]))
        reopened = ReviewStore(self.path)
        self.assertEqual(reopened.current(), revision)
        self.assertEqual(reopened.draft(draft["id"])["status"], "merged")
        with self.assertRaises(ValueError):
            self.publish(draft, decisions)
        with self.assertRaises(ValueError):
            self.prepare()

    def test_stale_draft_cannot_overwrite_new_revision(self):
        first, second = self.prepare(), self.prepare(SOURCE.replace("Điều 1.", "Điều 2."))
        self.publish(first)
        with self.assertRaisesRegex(ValueError, "revision"):
            self.publish(second)
        self.assertEqual(len(self.store.state()["revisions"]), 2)

    def test_entity_links_require_review_and_keep_both_mentions(self):
        self.publish(self.prepare())
        draft = self.prepare(SOURCE.replace("Điều 1.", "Điều 2."))
        source = next(n for n in draft["graph"]["nodes"] if n["kind"] == "Entity" and draft["suggestions"][n["id"]])
        target = draft["suggestions"][source["id"]][0]
        original = deepcopy(self.store.current())
        self.assertFalse(any(e["kind"] == "REVIEWED_ENTITY_LINK" for e in draft["graph"]["edges"]))
        revision = self.publish(draft, links={source["id"]: target})
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

    def test_invalid_entity_target_and_rejected_source_cannot_publish(self):
        draft = self.prepare()
        source = next(n for n in draft["graph"]["nodes"] if n["kind"] == "Entity")
        with self.assertRaises(ValueError):
            self.publish(draft, links={source["id"]: "missing"})
        self.assertEqual(len(self.store.state()["revisions"]), 1)

    def test_input_failures_are_actionable(self):
        for title, text in (("", SOURCE), ("x", ""), ("x", "x" * 1_000_001), ("x", "Không có heading"),
                            ("x", "Điều 1. Một\nNội dung\nĐiều 1. Trùng\nKhác"), ("x", "1. Khoản thiếu điều")):
            with self.assertRaises(ValueError):
                self.store.prepare(title, text)

    def test_seed_copied_once_and_never_modified(self):
        revision = self.publish(self.prepare())
        seed = Path(self.temp.name) / "seed.json"
        seed.write_text(json.dumps(revision["graph"]), encoding="utf-8")
        before = seed.read_bytes()
        store = ReviewStore(Path(self.temp.name) / "seeded.sqlite", seed)
        self.assertEqual(store.current()["graph"], revision["graph"])
        self.assertEqual(seed.read_bytes(), before)
        self.assertEqual(ReviewStore(store.path, "missing-ignored-seed.json").current(), store.current())

    def test_http_gate_upload_publish_and_safe_viewer_embedding(self):
        server = make_server(self.store, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        try:
            connection.request("GET", "/")
            response = connection.getresponse()
            page = response.read().decode()
            self.assertEqual(response.status, 200)
            token = page.split("const token='")[1].split("'")[0]
            body = json.dumps({"title": "</script><script>alert(1)</script>", "text": SOURCE, "synthetic": True})
            connection.request("POST", "/api/prepare", body, {"Content-Type": "application/json"})
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, 403)
            headers = {"Content-Type": "application/json", "X-Lexora-Token": token}
            connection.request("POST", "/api/chat/start", json.dumps({"revision": self.store.current()["id"]}), headers)
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, 400)
            connection.request("POST", "/api/prepare", body, headers)
            response = connection.getresponse()
            draft = json.loads(response.read())
            self.assertEqual(response.status, 200)
            body = json.dumps({"draft_id": draft["id"], "decisions": self.decisions(draft), "links": {}, "reviewer": "test", "reason": "test"})
            connection.request("POST", "/api/publish", body, headers)
            response = connection.getresponse()
            published = json.loads(response.read())
            self.assertEqual(response.status, 200)
            connection.request("POST", "/api/chat/start", json.dumps({"revision": published["revision"]}), headers)
            response = connection.getresponse()
            session = json.loads(response.read())
            self.assertEqual(response.status, 200)
            connection.request("POST", "/api/chat/ask", json.dumps({"session_id": session["id"], "question": "thông báo kết quả thử việc"}), headers)
            response = connection.getresponse()
            answer = json.loads(response.read())
            self.assertEqual(response.status, 200)
            self.assertEqual(answer["status"], "sources_found")
            self.assertEqual(answer["revision"], published["revision"])
            connection.request("GET", "/viewer?revision=" + published["revision"])
            response = connection.getresponse()
            viewer = response.read().decode()
            self.assertEqual(response.status, 200)
            self.assertNotIn("</script><script>alert(1)</script>", viewer)
            connection.request("POST", "/api/prepare", json.dumps({"title": "x", "text": SOURCE}), {**headers, "Origin": "https://example.invalid"})
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, 403)
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
