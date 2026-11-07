"""FastAPI web layer: loopback gates, accounts and roles, the workspace flow and static serving.

Runs only where the `web` extra is installed (`.venv`); the standard-library suite skips it.
"""

import base64
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai import auth
from legal_ai.auth import AccountStore
from legal_ai.common.io import digest
from legal_ai.kb.import_review import ReviewStore

try:
    from fastapi.testclient import TestClient
    from legal_ai.web.app import create_app
except ImportError:  # pragma: no cover - the stdlib-only environment
    TestClient = None

SOURCE = "Điều 1. Ví dụ tổng hợp, không phải luật thật\n1. Người lao động phải thông báo kết quả thử việc cho người sử dụng lao động.\n2. Người lao động có quyền nghỉ việc.\n"
PORT = 8799
BASE = f"http://127.0.0.1:{PORT}"


@unittest.skipIf(TestClient is None, "FastAPI not installed; run in .venv with the web extra")
class WebApiTests(unittest.TestCase):
    def setUp(self):
        fast = mock.patch.dict(auth.SCRYPT, {"n": 2 ** 4})
        fast.start()
        self.addCleanup(fast.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.store = ReviewStore(Path(self.temp.name) / "web.sqlite")
        accounts = AccountStore(self.store.path)
        accounts.create("admin", "Quản trị", "admin", "admin password 1")
        accounts.create("phapche", "Pháp chế", "reviewer", "review password 1")
        accounts.create("nhansu", "Nhân sự", "reader", "reader password 1")
        self.build = Path(self.temp.name) / "build"
        (self.build / "_app" / "immutable").mkdir(parents=True)
        (self.build / "index.html").write_text('<meta name="lexora-token" content="__CSRF_TOKEN__">', encoding="utf-8")
        (self.build / "_app" / "immutable" / "start.js").write_text("export {}", encoding="utf-8")
        self.app = create_app(self.store, PORT, token="t0ken", frontend_dir=self.build)
        self.clients = []

    def tearDown(self):
        for client in self.clients:
            client.close()
        self.temp.cleanup()

    def client(self, username=None, password=None):
        client = TestClient(self.app, base_url=BASE)
        self.clients.append(client)
        if username:
            response = client.post("/api/auth/login", json={"username": username, "password": password}, headers={"X-Lexora-Token": "t0ken"})
            self.assertEqual(response.status_code, 200, response.text)
        return client

    @staticmethod
    def post(client, path, body, headers=None):
        return client.post(path, json=body, headers={"X-Lexora-Token": "t0ken"} if headers is None else headers)

    def prepare(self, client, text=SOURCE, target=None, title="</script><script>alert(1)</script>"):
        target = target or {"mode": "new", "name": "Kho HTTP", "data_class": "public"}
        return self.post(client, "/api/prepare", {"title": title, "text": text, "synthetic": True, "target": target})

    def approve_all(self, client, draft):
        return self.post(client, "/api/draft/review", {"draft_id": draft["id"], "decision": "approve_article",
                                                       "payload": {"article_id": draft["articles"][0]["id"]}})

    def publish(self, client):
        draft = self.prepare(client).json()
        self.approve_all(client, draft)
        return self.post(client, "/api/publish", {"draft_id": draft["id"], "reason": "Đối chiếu nguyên văn"}).json()

    def test_static_build_token_headers_spa_fallback_and_no_escape(self):
        anonymous = self.client()
        page = anonymous.get("/")
        self.assertIn('content="t0ken"', page.text)
        self.assertIn("frame-ancestors 'none'", page.headers["content-security-policy"])
        self.assertEqual(page.headers["cache-control"], "no-store")
        self.assertEqual(page.headers["x-content-type-options"], "nosniff")
        asset = anonymous.get("/_app/immutable/start.js")
        self.assertEqual(asset.headers["content-type"], "text/javascript; charset=utf-8")
        self.assertIn("immutable", asset.headers["cache-control"])
        self.assertIn('content="t0ken"', anonymous.get("/drafts/123").text)
        (Path(self.temp.name) / "secret.txt").write_text("secret", encoding="utf-8")
        self.assertNotIn("secret", anonymous.get("/../secret.txt").text)
        self.assertNotIn("secret", anonymous.get("/%2e%2e/secret.txt").text)
        self.assertEqual(anonymous.get("/api/unknown").status_code, 404)

    def test_missing_build_explains_how_to_build(self):
        client = TestClient(create_app(self.store, PORT, token="t0ken"), base_url=BASE)
        self.clients.append(client)
        self.assertEqual(client.get("/").status_code, 503)

    def test_loopback_gates(self):
        client = self.client("phapche", "review password 1")
        self.assertEqual(client.get("/api/state", headers={"Host": "evil.example"}).status_code, 403)
        self.assertEqual(self.post(client, "/api/prepare", {"title": "x", "text": SOURCE}, headers={}).status_code, 403)
        self.assertEqual(self.post(client, "/api/prepare", {"title": "x", "text": SOURCE},
                                   headers={"X-Lexora-Token": "t0ken", "Origin": "https://example.invalid"}).status_code, 403)
        wrong_type = client.post("/api/prepare", content=b"title=x", headers={"X-Lexora-Token": "t0ken", "Content-Type": "text/plain"})
        self.assertEqual(wrong_type.json(), {"error": "Expected application/json"})
        too_big = client.post("/api/prepare", content=b"{}", headers={"X-Lexora-Token": "t0ken", "Content-Type": "application/json", "Content-Length": "999999999"})
        self.assertEqual(too_big.status_code, 400)

    def test_login_logout_and_session_cookie(self):
        anonymous = self.client()
        self.assertEqual(anonymous.get("/api/state").status_code, 401)
        self.assertEqual(anonymous.get("/api/auth/me").status_code, 401)
        refused = self.post(anonymous, "/api/auth/login", {"username": "phapche", "password": "wrong password"})
        self.assertEqual(refused.status_code, 401)
        ok = self.post(anonymous, "/api/auth/login", {"username": "phapche", "password": "review password 1"})
        cookie = ok.headers["set-cookie"].lower()
        for part in ("httponly", "samesite=strict", "path=/"):
            self.assertIn(part, cookie)
        self.assertEqual(anonymous.get("/api/auth/me").json()["role"], "reviewer")
        self.assertEqual(self.post(anonymous, "/api/auth/logout", {}).status_code, 200)
        self.assertEqual(anonymous.get("/api/auth/me").status_code, 401)

    def test_reader_sees_published_bases_only_and_cannot_review_or_manage(self):
        published = self.publish(self.client("phapche", "review password 1"))
        reviewer = self.clients[-1]
        self.prepare(reviewer, target={"mode": "new", "name": "Kho nháp", "data_class": "private"}, title="Nháp")
        reader = self.client("nhansu", "reader password 1")
        state = reader.get("/api/state").json()
        self.assertEqual(state["drafts"], [])
        self.assertEqual([k["name"] for k in state["knowledge_bases"]], ["Kho HTTP"])
        self.assertEqual(state["account"]["role"], "reader")
        self.assertEqual(reader.get("/api/kb", params={"id": published["kb_id"]}).status_code, 200)
        for path, body in (("/api/prepare", {"title": "x", "text": SOURCE}), ("/api/draft/review", {"draft_id": "d", "decision": "approve"}),
                           ("/api/publish", {"draft_id": "d", "reason": "r"}), ("/api/users", {"username": "x", "display_name": "x", "role": "admin", "password": "long password 1"})):
            self.assertEqual(self.post(reader, path, body).status_code, 403, path)
        self.assertEqual(reader.get("/api/sources").status_code, 403)
        self.assertEqual(reader.get("/api/users").status_code, 403)
        viewer = reader.get("/viewer", params={"revision": published["revision"]})
        self.assertEqual(viewer.status_code, 200)
        self.assertNotIn("</script><script>alert(1)</script>", viewer.text)
        self.assertIn('id="lexora-glossary"', viewer.text)
        structure = reader.get("/structure.html", params={"revision": published["revision"]})
        self.assertEqual(structure.status_code, 200)
        self.assertIn(f'href="/viewer?revision={published["revision"]}"', structure.text)
        self.assertNotIn("<!--LEXORA_TERMS-->", structure.text)
        self.assertEqual(self.client().get("/viewer", params={"revision": published["revision"]}, follow_redirects=False).status_code, 303)

    def test_readers_get_the_published_graph_of_a_base(self):
        published = self.publish(self.client("phapche", "review password 1"))
        reader = self.client("nhansu", "reader password 1")
        graph = reader.get("/api/kb/graph", params={"id": published["kb_id"]}).json()
        self.assertEqual(graph["revision"], published["revision"])
        kinds = {n["kind"] for n in graph["graph"]["nodes"]}
        self.assertTrue({"NormClaim", "LegalUnit", "Evidence"} <= kinds)
        self.assertEqual(self.client().get("/api/kb/graph", params={"id": published["kb_id"]}).status_code, 401)
        self.assertEqual(reader.get("/api/kb/graph", params={"id": "missing"}).status_code, 400)

    def test_chats_are_private_to_their_account(self):
        published = self.publish(self.client("phapche", "review password 1"))
        reader = self.client("nhansu", "reader password 1")
        session = self.post(reader, "/api/chat/start", {"kb_ids": [published["kb_id"]]}).json()
        answer = self.post(reader, "/api/chat/ask", {"session_id": session["id"], "question": "thông báo kết quả thử việc"}).json()
        self.assertEqual(answer["status"], "sources_found")
        self.assertEqual([s["id"] for s in reader.get("/api/state").json()["chat_sessions"]], [session["id"]])
        other = self.client("admin", "admin password 1")
        self.assertEqual(other.get("/api/state").json()["chat_sessions"], [])
        self.assertEqual(other.get("/api/chat/session", params={"id": session["id"]}).status_code, 404)
        self.assertEqual(self.post(other, "/api/chat/ask", {"session_id": session["id"], "question": "x"}).status_code, 404)

    def test_publish_records_the_signed_in_reviewer_and_detects_stale_drafts(self):
        reviewer = self.client("phapche", "review password 1")
        draft = self.prepare(reviewer).json()
        self.assertEqual(self.post(reviewer, "/api/publish", {"draft_id": draft["id"], "reason": "t"}).status_code, 400)
        self.approve_all(reviewer, draft)
        published = self.post(reviewer, "/api/publish", {"draft_id": draft["id"], "reason": "Đối chiếu"}).json()
        revision = reviewer.get("/api/kb", params={"id": published["kb_id"]}).json()["revisions"][0]
        self.assertEqual(revision["reviewer"], "Pháp chế (phapche)")
        self.assertEqual(self.post(reviewer, "/api/publish", {"draft_id": "x", "reviewer": "someone else", "reason": "t"}).status_code, 400)
        viewer = reviewer.get("/viewer", params={"revision": published["revision"]}).text
        self.assertNotIn("</script><script>alert(1)</script>", viewer)
        self.assertIn('id="lexora-glossary"', viewer)
        merge = {"mode": "merge", "kb_id": published["kb_id"]}
        stale = self.prepare(reviewer, SOURCE.replace("Điều 1.", "Điều 2."), merge, "x").json()
        fresh = self.prepare(reviewer, SOURCE.replace("Điều 1.", "Điều 3."), merge, "y").json()
        for d in (stale, fresh):
            self.approve_all(reviewer, d)
        self.assertEqual(self.post(reviewer, "/api/publish", {"draft_id": fresh["id"], "reason": "t"}).status_code, 200)
        conflict = self.post(reviewer, "/api/publish", {"draft_id": stale["id"], "reason": "t"})
        self.assertEqual((conflict.status_code, conflict.json()["code"]), (409, "base_changed"))
        self.assertEqual(self.post(reviewer, "/api/prepare", {"title": "x", "text": SOURCE, "extraction": "llm"}).json()["error"],
                         "Chưa bật model tách quy phạm cho phiên chạy này")

    def test_admin_manages_accounts(self):
        admin = self.client("admin", "admin password 1")
        created = self.post(admin, "/api/users", {"username": "moi", "display_name": "Người mới", "role": "reader", "password": "new user password"})
        self.assertEqual(created.status_code, 200, created.text)
        self.assertIn("moi", [a["username"] for a in admin.get("/api/users").json()["accounts"]])
        self.assertNotIn("password", created.json())
        promoted = self.post(admin, "/api/users/update", {"id": created.json()["id"], "role": "reviewer"})
        self.assertEqual(promoted.json()["role"], "reviewer")
        me = admin.get("/api/auth/me").json()
        self.assertEqual(self.post(admin, "/api/users/update", {"id": me["id"], "active": False}).status_code, 400)
        self.assertEqual(self.post(admin, "/api/users", {"username": "x", "display_name": "x", "role": "reader", "password": "short"}).status_code, 400)
        reviewer = self.client("phapche", "review password 1")
        self.assertEqual(reviewer.get("/api/users").status_code, 403)

    def test_research_corpus_from_files_and_confirmed_vbpl_fetches(self):
        reader = self.client("nhansu", "reader password 1")
        self.assertEqual(reader.get("/api/corpora").status_code, 403)
        self.assertEqual(self.post(reader, "/api/corpora", {"name": "x"}).status_code, 403)
        reviewer = self.client("phapche", "review password 1")
        listing = reviewer.get("/api/corpora").json()
        self.assertEqual((listing["corpora"], listing["vbpl_enabled"], listing["catalog"]), ([], False, None))
        corpus = self.post(reviewer, "/api/corpora", {"name": "Lao động", "description": "thử"}).json()
        upload = {"corpus_id": corpus["id"], "filename": "luat.txt", "content_base64": base64.b64encode(SOURCE.encode("utf-8")).decode()}
        added = self.post(reviewer, "/api/corpus/file", upload)
        self.assertEqual(added.status_code, 200, added.text)
        self.assertEqual((added.json()["document_id"], added.json()["added_by"]), ("luat", "phapche"))
        self.assertEqual(self.post(reviewer, "/api/corpus/file", dict(upload, content_base64="not base64!")).status_code, 400)
        refused = self.post(reviewer, "/api/corpus/vbpl", {"corpus_id": corpus["id"], "reference": "139264", "confirm": True})
        self.assertIn("--allow-vbpl", refused.json()["error"])
        self.assertEqual(reviewer.get("/api/catalog/search", params={"q": "lao động"}).status_code, 400)
        version = self.post(reviewer, "/api/corpus/freeze", {"corpus_id": corpus["id"], "note": "v1"}).json()
        self.assertEqual((version["number"], version["document_count"]), (1, 1))
        detail = reviewer.get("/api/corpus", params={"id": corpus["id"]}).json()
        self.assertEqual((len(detail["documents"]), detail["changed_since_version"]), (1, False))
        units = reviewer.get("/api/corpus/document", params={"id": added.json()["id"]}).json()["units"]
        self.assertEqual(units[0]["unit_id"], "luat/article-1")
        too_big = self.post(reviewer, "/api/corpus/file", dict(upload, content_base64="A" * (30 * 1024 * 1024)))
        self.assertEqual(too_big.status_code, 400)

    def test_vbpl_fetch_needs_the_run_flag_and_a_confirmation(self):
        raw = json.dumps({"success": True, "data": {"id": "139264", "documentContent": {"content": "<p>Điều 1. Phạm vi giả định</p><p>Nội dung giả định.</p>"}}},
                         ensure_ascii=False).encode("utf-8")
        snapshot = Path(self.temp.name) / "document.json"
        snapshot.write_bytes(raw)
        manifest = {"source_sha256": digest(raw), "site_url": "https://vbpl.vn/van-ban/chi-tiet/139264", "accessed_at": "2026-11-07T00:00:00+00:00",
                    "local_path": str(snapshot), "metadata": {"vbpl_id": "139264", "doc_num": "45/2019/GD", "title": "Bộ luật Giả định", "is_translation": False}}
        self.app = create_app(self.store, PORT, token="t0ken", frontend_dir=self.build, vbpl_dir=Path(self.temp.name) / "vbpl")
        reviewer = self.client("phapche", "review password 1")
        corpus = self.post(reviewer, "/api/corpora", {"name": "Có vbpl"}).json()
        self.assertTrue(reviewer.get("/api/corpora").json()["vbpl_enabled"])
        with mock.patch("legal_ai.web.app.fetch_document", return_value=manifest) as fetch:
            unconfirmed = self.post(reviewer, "/api/corpus/vbpl", {"corpus_id": corpus["id"], "reference": "139264"})
            self.assertEqual((unconfirmed.status_code, fetch.call_count), (400, 0), "no network call before the reviewer confirms")
            added = self.post(reviewer, "/api/corpus/vbpl", {"corpus_id": corpus["id"], "reference": "https://vbpl.vn/van-ban/chi-tiet/139264", "confirm": True})
        self.assertEqual(added.status_code, 200, added.text)
        self.assertEqual((added.json()["document_id"], added.json()["source_kind"]), ("45-2019-gd", "vbpl"))
        fetch.assert_called_once()

    def test_import_chosen_articles_from_vbpl_and_files_into_a_base(self):
        law = ("Chương I\nCHUNG\nĐiều 1. Phạm vi\nVăn bản giả định quy định về thử việc.\n"
               "Chương II\nTHỬ VIỆC\nĐiều 2. Thử việc\n1. Người lao động phải thông báo kết quả thử việc cho người sử dụng lao động.\n"
               "Điều 3. Sửa đổi luật giả định\n1. Sửa khoản 1:\n1. Nội dung mới.\n1. Nội dung khác.\n")
        content = "".join(f"<p>{line}</p>" for line in law.splitlines())
        raw = json.dumps({"success": True, "data": {"id": "139264", "documentContent": {"content": content}}}, ensure_ascii=False).encode("utf-8")
        folder = Path(self.temp.name) / "vbpl" / "139264" / digest(raw)
        folder.mkdir(parents=True)
        (folder / "document.json").write_bytes(raw)
        manifest = {"vbpl_id": "139264", "source_sha256": digest(raw), "site_url": "https://vbpl.vn/van-ban/chi-tiet/139264", "accessed_at": "2026-11-07T00:00:00+00:00",
                    "local_path": str(folder / "document.json"), "metadata": {"vbpl_id": "139264", "doc_num": "45/2019/GD", "title": "Bộ luật Giả định", "is_translation": False}}
        (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        reviewer = self.client("phapche", "review password 1")
        refused = self.post(reviewer, "/api/import/vbpl", {"reference": "139264", "confirm": True})
        self.assertIn("--allow-vbpl", refused.json()["error"])
        self.app = create_app(self.store, PORT, token="t0ken", frontend_dir=self.build, vbpl_dir=Path(self.temp.name) / "vbpl")
        reviewer = self.client("phapche", "review password 1")
        with mock.patch("legal_ai.web.app.fetch_document", return_value=manifest) as fetch:
            self.assertEqual((self.post(reviewer, "/api/import/vbpl", {"reference": "139264"}).status_code, fetch.call_count), (400, 0))
            found = self.post(reviewer, "/api/import/vbpl", {"reference": "139264", "confirm": True}).json()
        self.assertEqual([(a["heading"], a["blocked"]) for a in found["articles"]], [("Điều 1. Phạm vi", False), ("Điều 2. Thử việc", False), ("Điều 3. Sửa đổi luật giả định", True)])
        target = {"mode": "new", "name": "Kho vbpl", "data_class": "public"}
        body = {"vbpl_id": "139264", "source_sha256": found["source_sha256"], "article_ids": [found["articles"][1]["id"]], "target": target}
        draft = self.post(reviewer, "/api/prepare-vbpl", body)
        self.assertEqual(draft.status_code, 200, draft.text)
        self.assertEqual((draft.json()["title"], draft.json()["document"]["source_url"]), ("Bộ luật Giả định (Điều 2)", "https://vbpl.vn/van-ban/chi-tiet/139264"))
        self.assertIn("lồng nhau", self.post(reviewer, "/api/prepare-vbpl", body | {"article_ids": [found["articles"][2]["id"]]}).json()["error"])
        self.assertIn("Không tìm thấy bản chụp", self.post(reviewer, "/api/prepare-vbpl", body | {"source_sha256": "0" * 64}).json()["error"])
        import io, zipfile
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            paragraphs = "".join(f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>" for line in SOURCE.splitlines())
            archive.writestr("word/document.xml", f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{paragraphs}</w:body></w:document>')
        upload = {"filename": "luat.docx", "content_base64": base64.b64encode(buffer.getvalue()).decode(), "title": "Tệp DOCX", "synthetic": True,
                  "target": {"mode": "new", "name": "Kho tệp", "data_class": "private"}}
        made = self.post(reviewer, "/api/prepare-file", upload)
        self.assertEqual(made.status_code, 200, made.text)
        self.assertEqual(made.json()["title"], "Tệp DOCX")

    def _frozen_corpus(self, client):
        corpus = self.post(client, "/api/corpora", {"name": "Câu hỏi"}).json()
        self.post(client, "/api/corpus/file", {"corpus_id": corpus["id"], "filename": "luat.txt", "content_base64": base64.b64encode(SOURCE.encode("utf-8")).decode()})
        return self.post(client, "/api/corpus/freeze", {"corpus_id": corpus["id"]}).json()

    def test_question_sets_flow_across_two_machines(self):
        reader = self.client("nhansu", "reader password 1")
        self.assertEqual(reader.get("/api/question-sets").status_code, 403)
        vu = self.client("phapche", "review password 1")
        version = self._frozen_corpus(vu)
        listing = vu.get("/api/question-sets").json()
        self.assertEqual(([v["id"] for v in listing["versions"]], listing["proposal_model"]), ([version["id"]], None))
        qset = self.post(vu, "/api/question-sets", {"name": "Bộ 1", "corpus_version_id": version["id"]}).json()
        question = self.post(vu, "/api/question-set/question", {"set_id": qset["id"], "text": "Người lao động phải thông báo gì?"}).json()
        refused = self.post(vu, "/api/question-set/propose", {"set_id": qset["id"], "question_id": question["id"], "confirm": True})
        self.assertIn("--approve-claude", refused.json()["error"])
        unit = "luat/article-1/clause-1"
        self.assertEqual(vu.get("/api/question-set/candidates", params={"set_id": qset["id"], "q": "thông báo kết quả thử việc"}).json()["candidates"][0]["unit_id"], unit)
        self.assertEqual(vu.get("/api/question-set/outline", params={"set_id": qset["id"]}).json()["articles"][0]["heading"], "Điều 1. Ví dụ tổng hợp, không phải luật thật")
        label = {"set_id": qset["id"], "question_id": question["id"], "fields": {"question_type": "lookup", "expected_status": "answer", "relevant_unit_ids": [unit]}}
        self.assertEqual(self.post(vu, "/api/question-set/label", label).status_code, 400, "mode first")
        self.post(vu, "/api/question-set/mode", {"set_id": qset["id"], "show_proposals": False})
        self.assertEqual(self.post(vu, "/api/question-set/label", label).status_code, 200)
        pack = vu.get("/api/question-set/pack", params={"id": qset["id"]})
        self.assertIn("attachment", pack.headers["content-disposition"])

        # Kha's machine: a separate store and app.
        other = ReviewStore(Path(self.temp.name) / "kha.sqlite")
        AccountStore(other.path).create("kha", "Kha", "reviewer", "review password 2")
        self.app = create_app(other, PORT, token="t0ken", frontend_dir=self.build)
        kha = self.client("kha", "review password 2")
        self.assertEqual(self.post(kha, "/api/question-sets/import-pack", {"pack": pack.json()}).json()["questions"], 1)
        self.post(kha, "/api/question-set/mode", {"set_id": qset["id"], "show_proposals": False})
        self.assertEqual(self.post(kha, "/api/question-set/label", label).status_code, 200)
        labels = kha.get("/api/question-set/labels", params={"id": qset["id"]}).json()

        # Back on Vũ's machine: compare, adjudicate, freeze, download.
        self.app = create_app(self.store, PORT, token="t0ken", frontend_dir=self.build)
        vu = self.client("phapche", "review password 1")
        self.assertEqual(self.post(vu, "/api/question-set/import-labels", {"labels": labels}).json()["labels"], 1)
        report = vu.get("/api/question-set/compare", params={"id": qset["id"], "other": "kha"}).json()
        self.assertEqual((report["labelled_by_both"], report["items"][0]["agree"]), (1, True))
        freeze = {"set_id": qset["id"], "other": "kha", "held_out": 0.5}
        self.assertIn("chưa chốt", self.post(vu, "/api/question-set/freeze", freeze).json()["error"])
        self.post(vu, "/api/question-set/adjudicate", label | {"note": ""})
        self.assertEqual(self.post(vu, "/api/question-set/freeze", freeze).status_code, 200)
        frozen = vu.get("/api/question-set/frozen", params={"id": qset["id"]}).json()
        self.assertEqual(frozen["questions"][0]["relevant_unit_ids"], [unit])

    def test_model_calls_need_the_run_provider_and_a_confirmation(self):
        class Proposer:
            model, effort, max_calls, calls = "stand-in", "low", 3, 0

            def __init__(self):
                self.ledger = []

            def structured(self, system, prompt, schema, purpose="structured"):
                self.calls += 1
                output = {"question_type": "lookup", "expected_status": "answer", "relevant_unit_ids": schema["properties"]["relevant_unit_ids"]["items"]["enum"][:1], "rationale": "r"}
                self.ledger.append({"purpose": purpose, "status": "ok", "output": output})
                return {"output": output}

        proposer = Proposer()
        self.app = create_app(self.store, PORT, token="t0ken", frontend_dir=self.build, proposer=proposer)
        vu = self.client("phapche", "review password 1")
        version = self._frozen_corpus(vu)
        qset = self.post(vu, "/api/question-sets", {"name": "Bộ 2", "corpus_version_id": version["id"]}).json()
        question = self.post(vu, "/api/question-set/question", {"set_id": qset["id"], "text": "Người lao động phải thông báo gì?"}).json()
        body = {"set_id": qset["id"], "question_id": question["id"]}
        self.assertEqual((self.post(vu, "/api/question-set/propose", body).status_code, proposer.calls), (400, 0))
        proposal = self.post(vu, "/api/question-set/propose", body | {"confirm": True}).json()
        self.assertEqual((proposal["fields"]["question_type"], proposer.calls), ("lookup", 1))
        view = vu.get("/api/question-set", params={"id": qset["id"]}).json()
        self.assertEqual((view["calls"], view["proposal_calls_left"], view["proposal_model"]), (1, 2, "stand-in"))


if __name__ == "__main__":
    unittest.main()
