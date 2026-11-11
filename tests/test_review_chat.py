"""Offline publication, session isolation, citation gating and source pinning tests."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from legal_ai.common.io import canonical, digest
from legal_ai.ingestion.source_library import SourceLibrary
from legal_ai.kb.import_review import ReviewStore, empty_graph
from legal_ai.providers.pilot import ProviderError
from legal_ai.providers.router import RouterProvider, api_url, read_settings
from legal_ai.rag.review_chat import ChatService, approved_passages, query_terms, validate_generation

TEXT = "Điều 1. DỮ LIỆU TỔNG HỢP KHÔNG PHẢI LUẬT\n1. Người lao động phải thông báo kết quả thử việc cho người lao động. Người sử dụng lao động phải trả khoản bí mật.\n"


class FakeProvider:
    def __init__(self, content=None, error=None):
        self.content = content or json.dumps({"status": "answered", "statements": [{"text": "SYNTHETIC test response", "citation_ids": ["C1"]}]})
        self.error = error
        self.calls = []

    def generate(self, question, citations):
        self.calls.append((question, citations))
        if self.error:
            raise ProviderError(self.error)
        return {"content": self.content, "usage": {"total_tokens": 10}}


class ReviewChatTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = ReviewStore(self.root / "test.sqlite")
        self.chat = ChatService(self.store)

    def tearDown(self):
        self.temp.cleanup()

    def publish(self, text=TEXT, reject_secret=True, name="Kho chat", data_class="public"):
        existing = {k["name"]: k["id"] for k in self.store.knowledge_bases()}
        target = {"mode": "merge", "kb_id": existing[name]} if name in existing else {"mode": "new", "name": name, "data_class": data_class}
        draft = self.store.prepare("SYNTHETIC - NOT REAL LAW", text, synthetic=True, target=target)
        decisions = {n["id"]: ("reject" if reject_secret and "bí mật" in n["payload"]["slots"]["action"].get("text", "") else "approve")
                     for n in draft["graph"]["nodes"] if n["kind"] == "NormClaim"}
        return self.store.publish(draft["id"], "test", "synthetic offline review", decisions=decisions)

    def test_stopwords_do_not_remove_words_that_only_look_alike_without_accents(self):
        # "tôi" is a stopword, "tối" (as in "tối đa") is not; "người lao động" is, "hợp đồng" is not.
        self.assertEqual(query_terms("Thời gian thử việc tối đa bao lâu?"), {"thoi", "gian", "thu", "viec", "toi", "da", "lau"})
        self.assertIn("dong", query_terms("Hợp đồng của người lao động"))
        self.assertNotIn("toi", query_terms("Tôi muốn hỏi về hợp đồng"))
        self.assertNotIn("toi", query_terms("toi muon hoi ve hop dong"), "unaccented input still drops the folded stopword")

    def test_unconfirmed_baseline_and_draft_cannot_start_chat(self):
        seed = self.root / "seed.json"
        seed.write_text(json.dumps(empty_graph()), encoding="utf-8")
        store = ReviewStore(self.root / "seeded.sqlite", seed)
        chat = ChatService(store)
        [kb] = store.knowledge_bases()
        store.prepare("test", TEXT, synthetic=True, target={"mode": "merge", "kb_id": kb["id"]})
        for kb_ids in ([kb["id"]], [], ["missing"], [kb["id"], kb["id"]], "x", [str(i) for i in range(6)]):
            with self.assertRaises(ValueError):
                chat.start(kb_ids)
        self.assertEqual(chat.sessions(), [])

    def test_only_approved_sentence_not_full_unit_retrieved(self):
        revision = self.publish()
        session = self.chat.start([revision["kb_id"]])
        result = self.chat.ask(session["id"], "Ai thông báo kết quả thử việc?")
        self.assertEqual(result["status"], "sources_found")
        self.assertEqual(result["statements"], [])
        self.assertEqual(self.chat.ask(session["id"], "thong bao ket qua thu viec")["status"], "sources_found")
        self.assertNotIn("bí mật", json.dumps(result["citations"], ensure_ascii=False))
        self.assertEqual(self.chat.ask(session["id"], "khoản bí mật")["status"], "insufficient_evidence")
        self.assertEqual(self.chat.ask(session["id"], "thuế suất thu nhập cá nhân")["status"], "insufficient_evidence")

    def test_session_pinned_across_publications_and_restart(self):
        revision = self.publish()
        session = self.chat.start([revision["kb_id"]])
        self.publish("Điều 2. SYNTHETIC\nNgười lao động phải nộp hồ sơ xanh.\n")
        self.assertEqual(self.chat.ask(session["id"], "hồ sơ xanh")["status"], "insufficient_evidence")
        new_session = self.chat.start([revision["kb_id"]])
        self.assertEqual(self.chat.ask(new_session["id"], "hồ sơ xanh")["status"], "sources_found")
        restored = ChatService(ReviewStore(self.root / "test.sqlite"))
        self.assertEqual(restored.session(session["id"])["bindings"][0]["revision_id"], revision["id"])
        self.assertEqual(len(restored.session(session["id"])["turns"]), 1)

    def test_provider_requires_per_turn_consent_and_valid_citations(self):
        session = self.chat.start([self.publish()["kb_id"]])
        provider = FakeProvider()
        chat = ChatService(self.store, provider)
        self.assertEqual(chat.ask(session["id"], "thông báo kết quả", "llm")["status"], "transfer_not_approved")
        self.assertEqual(provider.calls, [])
        result = chat.ask(session["id"], "thông báo kết quả", "llm", True)
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["statements"][0]["citation_ids"], ["C1"])
        provider.content = '{"status":"answered","statements":[{"text":"made up","citation_ids":["C99"]}]}'
        result = chat.ask(session["id"], "thông báo kết quả", "llm", True)
        self.assertEqual(result["status"], "answer_rejected")
        self.assertEqual(result["statements"], [])
        provider.content = '{"status":"insufficient_evidence","statements":[]}'
        result = chat.ask(session["id"], "thông báo kết quả", "llm", True)
        self.assertEqual(result["status"], "model_insufficient", "passages were found; the model judged them not enough")
        self.assertTrue(result["citations"])
        self.assertIn("chưa đủ", result["note"])

    def test_provider_disabled_error_and_no_evidence_statuses(self):
        session = self.chat.start([self.publish()["kb_id"]])
        self.assertEqual(self.chat.ask(session["id"], "thông báo kết quả", "llm", True)["status"], "provider_disabled")
        provider = FakeProvider(error="quota_exhausted")
        chat = ChatService(self.store, provider)
        result = chat.ask(session["id"], "thông báo kết quả", "llm", True)
        self.assertEqual(result["error_code"], "quota_exhausted")
        self.assertEqual(result["statements"], [])
        chat.ask(session["id"], "thuế suất thu nhập", "llm", True)
        self.assertEqual(len(provider.calls), 1)

    def test_tampered_quote_and_graph_rejected(self):
        graph = deepcopy(self.publish()["graph"])
        graph["graph_hash"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "graph_integrity"):
            approved_passages(graph)
        graph = deepcopy(self.store.current(self.store.knowledge_bases()[0]["id"])["graph"])
        node = next(n for n in graph["nodes"] if n["kind"] == "Evidence")
        node["payload"]["quote"] = "tampered"
        content = {k: graph[k] for k in ("graph_version", "nodes", "edges", "references", "extraction_report")}
        graph["graph_hash"] = digest(canonical(content))
        # If this anchor belongs to a rejected claim it is never consulted.
        # Tamper all anchors to ensure an approved one is detected too.
        for n in graph["nodes"]:
            if n["kind"] == "Evidence":
                n["payload"]["quote"] = "tampered"
        graph["graph_hash"] = digest(canonical({k: graph[k] for k in content}))
        with self.assertRaisesRegex(ValueError, "evidence_integrity"):
            approved_passages(graph)

    def test_invalid_model_json_or_empty_citations_rejected(self):
        for content in ('bad json', '[]', '{}', '{"status":"answered","statements":[]}',
                        '{"status":"answered","statements":[{"text":"x","citation_ids":[]}]}'):
            with self.assertRaises((ValueError, TypeError)):
                validate_generation(content, [])

    def test_source_catalog_checksum_path_and_source_url(self):
        source = self.root / "source.txt"
        source.write_bytes(TEXT.encode("utf-8"))
        catalog = self.root / "catalog.json"
        entry = {"id": "test", "title": "SYNTHETIC catalog test", "file": "source.txt", "sha256": digest(source.read_bytes()), "source_url": "https://vbpl.vn/test"}
        def write():
            catalog.write_text(json.dumps({"schema_version": "source-library-v1", "entries": [entry]}), encoding="utf-8")
        write()
        library = SourceLibrary(catalog)
        target = {"mode": "new", "name": "Kho thư viện"}
        draft = library.prepare(self.store, "test", target)
        document = next(n["payload"] for n in draft["graph"]["nodes"] if n["kind"] == "Document")
        self.assertEqual(document["source_url"], entry["source_url"])
        source.write_text("changed", encoding="utf-8")
        with self.assertRaises(ValueError):
            library.prepare(self.store, "test", target)
        entry["file"] = "../escape.txt"
        write()
        with self.assertRaisesRegex(ValueError, "path"):
            library.prepare(self.store, "test", target)

    def test_multi_kb_session_dedupes_shared_quotes_and_labels_sources(self):
        a = self.publish(name="Kho A")["kb_id"]
        b = self.publish(name="Kho B", data_class="private")["kb_id"]
        self.publish("Điều 5. SYNTHETIC\nNgười sử dụng lao động phải trả lương tháng mười ba.\n", name="Kho B")
        session = self.chat.start([a, b])
        self.assertEqual([x["kb_name"] for x in session["bindings"]], ["Kho A", "Kho B"])
        result = self.chat.ask(session["id"], "thông báo kết quả thử việc")
        self.assertEqual(len(result["citations"]), 1)
        self.assertEqual(sorted(s["kb_name"] for s in result["citations"][0]["sources"]), ["Kho A", "Kho B"])
        only_b = self.chat.ask(session["id"], "trả lương tháng mười ba")
        self.assertEqual([s["kb_name"] for s in only_b["citations"][0]["sources"]], ["Kho B"])
        self.assertEqual(self.chat.ask(self.chat.start([a])["id"], "trả lương tháng mười ba")["status"], "insufficient_evidence")
        provider = FakeProvider()
        result = ChatService(self.store, provider).ask(session["id"], "thông báo kết quả", "llm", True)
        self.assertEqual(result["status"], "private_transfer_blocked")
        self.assertEqual(provider.calls, [])

    def test_legacy_single_revision_session_migrates_to_binding(self):
        revision = self.publish()
        legacy = {"schema_version": "review-chat-v1", "id": "s1", "revision": revision["id"],
                  "created_at": "2026-11-01T00:00:00+00:00", "turns": []}
        with self.store.connect() as db:
            db.execute("INSERT INTO chat_sessions VALUES (?, ?)", ("s1", canonical(legacy)))
        session = ChatService(self.store).session("s1")
        self.assertEqual(session["bindings"][0]["revision_id"], revision["id"])
        self.assertEqual(session["bindings"][0]["kb_id"], revision["kb_id"])

    def test_transport_config_is_explicit_no_dotenv_execution(self):
        path = self.root / ".env"
        path.write_text('9ROUTER_KEY="${NOT_EXPANDED}"\n# comment\n', encoding="utf-8")
        self.assertEqual(read_settings(path)["9ROUTER_KEY"], "${NOT_EXPANDED}")
        for url in ("https://example.test", "https://example.test/v1", "https://example.test/v1/chat/completions"):
            self.assertEqual(api_url(url, "models"), "https://example.test/v1/models")
        with self.assertRaises(ValueError):
            api_url("http://example.test", "models")
        with self.assertRaises(ValueError):
            RouterProvider({}, model="ollama/beam")

    def test_transport_budget_stream_flag_and_private_metadata_not_sent(self):
        class Response:
            status = 200
            headers = {"Content-Type": "application/json"}
            def __enter__(self):
                return self
            def __exit__(self, *_):
                pass
            def read(self, _):
                return b'{"choices":[{"message":{"content":"{}"}}],"usage":{}}'
        settings = {"9ROUTER_URL": "https://example.test", "9ROUTER_KEY": "test-key"}
        provider = RouterProvider(settings, model="test-model", approved_route=True, max_calls=1)
        with patch("legal_ai.providers.router.build_opener") as opener:
            opener.return_value.open.return_value = Response()
            provider.generate("test", [{"id": "C1", "evidence": {"quote": "public quote", "unit_id": "u1"},
                                        "scope": [], "human_review": {"reviewer": "private-name"}}])
            request = opener.return_value.open.call_args.args[0]
            body = json.loads(request.data)
            self.assertIs(body["stream"], False)
            self.assertNotIn("private-name", str(body))
            self.assertEqual(body["model"], "test-model")
            with self.assertRaises(ProviderError):
                provider.generate("test", [])
            self.assertEqual(opener.return_value.open.call_count, 1)


if __name__ == "__main__":
    unittest.main()
