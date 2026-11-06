"""FastAPI web layer: loopback gates, accounts and roles, the workspace flow and static serving.

Runs only where the `web` extra is installed (`.venv`); the standard-library suite skips it.
"""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai import auth
from legal_ai.auth import AccountStore
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
        self.assertEqual(reader.get("/viewer", params={"revision": published["revision"]}).status_code, 200)
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


if __name__ == "__main__":
    unittest.main()
