"""Offline tests for rule v2 coverage, AI span extraction, review gaps and hybrid retrieval.

No network: providers are fakes that return fixed JSON or raise ProviderError.
All legal text here is synthetic or a short public-law-shaped sample.
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from legal_ai.extraction.llm_norms import extract, locate, parse_json
from legal_ai.extraction.norms import extract_norms
from legal_ai.ingestion.parser import parse
from legal_ai.kb.import_review import ReviewStore, coverage_gaps
from legal_ai.normalization.text import normalize
from legal_ai.providers.pilot import ProviderError
from legal_ai.providers.router import RouterEmbeddings
from legal_ai.rag.review_chat import ChatService, hybrid_retrieve, retrieve
from legal_ai.validation.evidence import check_evidence, validate_record

SOURCE = ("Điều 3. Sổ quản lý lao động - DỮ LIỆU MINH HỌA\n"
          "Việc lập sổ được quy định như sau:\n"
          "1. Trong thời hạn 30 ngày kể từ ngày bắt đầu hoạt động, người sử dụng lao động phải lập sổ quản lý lao động.\n"
          "2. Sổ quản lý lao động được lập bằng bản giấy hoặc bản điện tử nhưng phải bảo đảm các thông tin cơ bản.\n"
          "3. Người sử dụng lao động có trách nhiệm cập nhật sổ quản lý lao động.\n"
          "4. Sổ quản lý lao động gồm các thông tin về người lao động.\n")


def units_of(text):
    normalized = normalize(text)
    return parse(normalized, "synthetic", normalized["normalized_sha256"])["units"]


def slot_texts(claim):
    return {k: v["text"] for k, v in claim["slots"].items() if v["state"] == "present" and k != "scope"}


class FakeExtractor:
    model = "fake/model"

    def __init__(self, answer=None, error=None):
        self.answer, self.error, self.requests = answer, error, []

    def complete(self, system, user, max_tokens=900):
        self.requests.append(json.loads(user))
        if self.error:
            raise ProviderError(self.error)
        return {"content": self.answer(self.requests[-1]) if callable(self.answer) else self.answer, "usage": {}}


def answer_for_clause_two(request):
    """Answers every sentence; clause 2 gets one verbatim norm, one paraphrased norm."""
    results = []
    for sentence in request["sentences"]:
        norms = []
        if sentence["text"].startswith("Sổ quản lý lao động được lập"):
            norms = [{"actor": None, "action": "bảo đảm", "object": "các thông tin cơ bản", "modality": "obligation", "modality_cue": "phải"},
                     {"actor": "Người sử dụng lao động", "action": "lập sổ bằng giấy", "modality": "permission", "modality_cue": "được"}]
        results.append({"sentence": sentence["id"], "norms": norms})
    return "```json\n" + json.dumps({"results": results}, ensure_ascii=False) + "\n```"


class RuleCoverageTests(unittest.TestCase):
    def test_v2_rules_cover_deadline_prefix_and_responsibility_cue(self):
        claims, evidence, report = extract_norms(units_of(SOURCE))
        structured = [c for c in claims if c["extraction_run_id"] == "norm-rules-v2:explicit-deontic"]
        first = next(c for c in structured if "lập sổ quản lý lao động" in slot_texts(c).get("action", ""))
        self.assertEqual(slot_texts(first), {"actor": "người sử dụng lao động", "action": "lập sổ quản lý lao động",
                                             "deadlines": "Trong thời hạn 30 ngày kể từ ngày bắt đầu hoạt động"})
        third = next(c for c in structured if slot_texts(c)["actor"] == "Người sử dụng lao động")
        self.assertEqual(third["modality"], "obligation")
        units = units_of(SOURCE)
        self.assertEqual(validate_record(third, evidence, units)["reasons"], ["semantic_review_required"])

    def test_cue_sentence_is_a_review_candidate_without_label_or_inferred_modality(self):
        claims, evidence, _ = extract_norms(units_of(SOURCE))
        cue = [c for c in claims if c["extraction_run_id"] == "norm-rules-v2:cue-sentence"]
        self.assertEqual(len(cue), 1)
        self.assertEqual(cue[0]["modality"], "unknown")
        quotes = [e["quote"] for e in evidence if e["evidence_id"] in cue[0]["evidence_ids"]]
        self.assertIn("Sổ quản lý lao động được lập bằng bản giấy hoặc bản điện tử nhưng phải bảo đảm các thông tin cơ bản", quotes)
        self.assertFalse(any(q.startswith("2.") for q in quotes))

    def test_sentence_without_cue_becomes_a_gap(self):
        draft = ReviewStore(Path(tempfile.mkdtemp()) / "s.sqlite").prepare("t", SOURCE, synthetic=True, target={"mode": "new", "name": "K", "data_class": "public"})
        self.assertEqual([g["text"] for g in coverage_gaps(draft["graph"])], ["Sổ quản lý lao động gồm các thông tin về người lao động"])


class AiExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ReviewStore(Path(self.temp.name) / "s.sqlite")

    def tearDown(self):
        self.temp.cleanup()

    def prepare(self, data_class="public", extraction="llm"):
        return self.store.prepare("t", SOURCE, synthetic=True, target={"mode": "new", "name": "K-" + data_class, "data_class": data_class},
                                  extraction=extraction, extraction_model="fake/model" if extraction == "llm" else None)

    def run_job(self, draft, extractor):
        units, targets = self.store.start_extraction(draft["id"])
        claims, evidence, reports, errors = extract(units, targets, extractor)
        self.store.finish_extraction(draft["id"], claims, evidence, reports, errors)
        return self.store.draft_view(draft["id"])

    def test_private_kb_never_uses_ai_extraction(self):
        with self.assertRaises(ValueError):
            self.prepare("private")
        kb_draft = self.prepare("private", extraction="rules")
        self.assertEqual(kb_draft["extraction"], {"mode": "rules", "state": "done"})

    def test_only_unstructured_sentences_are_sent_and_only_verbatim_spans_kept(self):
        extractor = FakeExtractor(answer_for_clause_two)
        view = self.run_job(self.prepare(), extractor)
        sent = [s["text"] for r in extractor.requests for s in r["sentences"]]
        self.assertEqual(len(sent), 2)  # clause 2 (cue sentence) and clause 4 (no cue); clauses 1 and 3 stay rule claims
        self.assertNotIn("Người sử dụng lao động có trách nhiệm cập nhật sổ quản lý lao động", sent)
        ai = [c for c in view["claims"] if c["origin"] == "ai"]
        self.assertEqual(len(ai), 1)  # the paraphrased action "lập sổ bằng giấy" is dropped
        self.assertEqual({k: v["text"] for k, v in ai[0]["slots"].items() if v["state"] == "present" and k != "scope"},
                         {"action": "bảo đảm", "object": "các thông tin cơ bản"})
        self.assertEqual(ai[0]["modality"], "obligation")
        self.assertFalse(any(c["origin"] == "cue" for c in view["claims"]))  # replaced by the AI claim
        self.assertEqual(view["extraction"]["state"], "done")
        units = [u for a in view["articles"] for u in a["units"]]
        for claim in ai:
            for slot in claim["slots"].values():
                for row in slot["evidence"]:
                    self.assertEqual(units_text(units, row), row["quote"])
        report = next(r for r in self.store.draft(view["id"])["extraction"]["sentences"] if r["status"] == "norms")
        self.assertIn("action_not_verbatim", report["issues"])

    def test_unverified_modality_cue_downgrades_to_unknown(self):
        def answer(request):
            return json.dumps({"results": [{"sentence": s["id"], "norms": [{"action": "bảo đảm", "modality": "prohibition", "modality_cue": "phải"}]
                                            if "bảo đảm" in s["text"] else []} for s in request["sentences"]]})
        view = self.run_job(self.prepare(), FakeExtractor(answer))
        ai = next(c for c in view["claims"] if c["origin"] == "ai")
        self.assertEqual(ai["modality"], "unknown")

    def test_provider_failure_keeps_rule_results_and_unblocks_review(self):
        draft = self.prepare()
        with self.assertRaises(ValueError):
            self.store.review(draft["id"], None, "approve_article", {"article_id": "x"})
        view = self.run_job(draft, FakeExtractor(error="provider_unavailable"))
        self.assertEqual(view["extraction"]["state"], "failed")
        self.assertTrue(any(c["origin"] == "cue" for c in view["claims"]))
        self.assertEqual(view["extraction"]["errors"], ["provider_unavailable"])

    def test_structured_providers_get_the_schema_and_their_errors_keep_rule_results(self):
        from legal_ai.extraction.llm_norms import SCHEMA, LLM_SLOTS
        from legal_ai.providers.claude_code import ProviderError as ClaudeError

        class Structured:
            model, max_calls, calls = "claude-opus-5-5", 5, 0

            def __init__(self, error=None):
                self.error, self.seen = error, []

            def structured(self, system, prompt, schema, purpose="structured"):
                self.seen.append((schema, purpose, json.loads(prompt)))
                if self.error:
                    raise ClaudeError(self.error, "detail")
                request = self.seen[-1][2]
                norm = {name: None for name in LLM_SLOTS} | {"action": "bảo đảm", "object": "các thông tin cơ bản", "modality": "obligation", "modality_cue": "phải"}
                return {"output": {"results": [{"sentence": s["id"], "norms": [norm] if "bảo đảm" in s["text"] else []} for s in request["sentences"]]}}

        provider = Structured()
        view = self.run_job(self.prepare(), provider)
        self.assertIs(provider.seen[0][0], SCHEMA)
        self.assertEqual(provider.seen[0][1], "norm-extraction")
        ai = [c for c in view["claims"] if c["origin"] == "ai"]
        self.assertEqual([slot_texts(c) for c in ai], [{"action": "bảo đảm", "object": "các thông tin cơ bản"}])
        failed = self.run_job(self.prepare(), Structured(error="budget_exhausted"))
        self.assertEqual((failed["extraction"]["state"], failed["extraction"]["errors"]), ("failed", ["budget_exhausted"]))
        self.assertTrue(any(c["origin"] == "cue" for c in failed["claims"]), "rule results stay when Claude Code fails")

    def test_garbage_output_is_rejected_not_parsed_loosely(self):
        view = self.run_job(self.prepare(), FakeExtractor("Tôi nghĩ câu này là nghĩa vụ."))
        self.assertEqual(view["extraction"]["errors"], ["invalid_extraction_output"])
        with self.assertRaises(ValueError):
            parse_json('{"results": "x"}')

    def test_restart_interrupts_running_job_and_rerun_requires_no_decisions(self):
        draft = self.prepare()
        self.store.start_extraction(draft["id"])
        ReviewStore(self.store.path).interrupt_extractions()
        view = self.store.draft_view(draft["id"])
        self.assertEqual(view["extraction"]["state"], "interrupted")
        claim = view["claims"][0]["id"]
        self.store.review(draft["id"], claim, "approve")
        with self.assertRaises(ValueError):
            self.store.start_extraction(draft["id"])

    def test_locate_is_exact_or_length_preserving_case_fold(self):
        text = "Người sử dụng lao động phải lập sổ."
        self.assertEqual(locate(text, 0, len(text), "người sử dụng lao động"), (0, 22))
        self.assertIsNone(locate(text, 0, len(text), "người sử dụng  lao động"))
        self.assertIsNone(locate(text, 23, len(text), "Người"))


def units_text(units, row):
    unit = next(u for u in units if u["unit_version_id"] == row["unit_version_id"])
    return unit["text"][row["start"]:row["end"]]


class GapAndManualClaimTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ReviewStore(Path(self.temp.name) / "s.sqlite")
        self.draft = self.store.prepare("t", SOURCE, synthetic=True, target={"mode": "new", "name": "K", "data_class": "public"})

    def tearDown(self):
        self.temp.cleanup()

    def approve_all(self):
        return self.store.review(self.draft["id"], None, "approve_article", {"article_id": self.store.draft_view(self.draft["id"])["articles"][0]["id"]})

    def test_open_gap_blocks_publish_until_dismissed(self):
        view = self.approve_all()
        self.assertEqual(view["progress"]["gaps_open"], 1)
        with self.assertRaisesRegex(ValueError, "chưa có quy phạm"):
            self.store.publish(self.draft["id"], "R", "Synthetic")
        view = self.store.review(self.draft["id"], view["gaps"][0]["id"], "no_norm")
        self.assertEqual(view["progress"]["gaps_open"], 0)
        revision = self.store.publish(self.draft["id"], "R", "Synthetic")
        self.assertEqual(len(revision["review"]["dismissed_gaps"]), 1)

    def test_batch_dismiss_per_article(self):
        view = self.store.review(self.draft["id"], None, "no_norm_article", {"article_id": self.store.draft_view(self.draft["id"])["articles"][0]["id"]})
        self.assertTrue(all(g["decision"] == "no_norm" for g in view["gaps"]))

    def test_manual_claim_from_gap_is_edited_with_exact_quotes_and_published(self):
        gap = self.store.draft_view(self.draft["id"])["gaps"][0]
        view = self.store.review(self.draft["id"], None, "add_claim", {k: gap[k] for k in ("unit_version_id", "start", "end")})
        self.assertEqual(view["gaps"], [])
        manual = next(c for c in view["claims"] if c["origin"] == "manual")
        unit = next(u for a in view["articles"] for u in a["units"] if u["unit_version_id"] == gap["unit_version_id"])
        start = unit["text"].index("Sổ quản lý lao động")
        view = self.store.review(self.draft["id"], manual["id"], "edit", {"field": "slot", "slot": "object", "state": "present",
                                                                           "unit_version_id": unit["unit_version_id"], "start": start, "end": start + len("Sổ quản lý lao động")})
        view = self.approve_all()
        revision = self.store.publish(self.draft["id"], "R", "Synthetic")
        nodes = [n for n in revision["graph"]["nodes"] if n["kind"] == "NormClaim" and n["payload"]["extraction_run_id"] == "manual-v1:reviewer"]
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["payload"]["slots"]["object"]["text"], "Sổ quản lý lao động")
        units = [n["payload"] for n in revision["graph"]["nodes"] if n["kind"] == "LegalUnit"]
        for node in revision["graph"]["nodes"]:
            if node["kind"] == "Evidence":
                self.assertEqual(check_evidence(node["payload"], units), [])

    def test_only_manual_claims_can_be_removed_and_removal_restores_gap(self):
        view = self.store.draft_view(self.draft["id"])
        machine = view["claims"][0]["id"]
        with self.assertRaises(ValueError):
            self.store.review(self.draft["id"], machine, "remove_claim")
        gap = view["gaps"][0]
        view = self.store.review(self.draft["id"], None, "add_claim", {k: gap[k] for k in ("unit_version_id", "start", "end")})
        manual = next(c for c in view["claims"] if c["origin"] == "manual")
        self.store.review(self.draft["id"], manual["id"], "approve")
        view = self.store.review(self.draft["id"], manual["id"], "remove_claim")
        self.assertEqual(len(view["gaps"]), 1)
        self.assertFalse(any(c["origin"] == "manual" for c in view["claims"]))

    def test_manual_claim_must_be_inside_one_leaf_unit(self):
        view = self.store.draft_view(self.draft["id"])
        article = view["articles"][0]["units"][0]
        with self.assertRaises(ValueError):
            self.store.review(self.draft["id"], None, "add_claim", {"unit_version_id": article["unit_version_id"], "start": 0, "end": 5})
        gap = view["gaps"][0]
        with self.assertRaises(ValueError):
            self.store.review(self.draft["id"], None, "add_claim", {"unit_version_id": gap["unit_version_id"], "start": gap["start"] - 1, "end": gap["end"]})


class FakeEmbedder:
    model, dimensions = "fake/embed", 3

    def __init__(self, error=None):
        self.calls, self.error = [], error

    def embed(self, texts):
        if self.error:
            raise ProviderError(self.error)
        self.calls.append(list(texts))
        # "giấy tờ" and "căn cước" share a direction; everything else is orthogonal.
        return [[1.0, 0.0, 0.0] if ("giấy tờ" in t or "căn cước" in t) else [0.0, 1.0, 0.0] for t in texts]


CHAT_SOURCE = ("Điều 1. DỮ LIỆU MINH HỌA\n1. Người sử dụng lao động không được giữ bản chính giấy tờ tùy thân của người lao động.\n"
               "2. Người sử dụng lao động phải lập sổ quản lý lao động.\n")


class HybridRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ReviewStore(Path(self.temp.name) / "s.sqlite")

    def tearDown(self):
        self.temp.cleanup()

    def kb(self, data_class="public"):
        draft = self.store.prepare("t", CHAT_SOURCE, synthetic=True, target={"mode": "new", "name": "K-" + data_class, "data_class": data_class})
        self.store.review(draft["id"], None, "approve_article", {"article_id": self.store.draft_view(draft["id"])["articles"][0]["id"]})
        return self.store.publish(draft["id"], "R", "Synthetic")["kb_id"]

    def test_semantic_search_finds_passage_without_shared_keywords_and_caches_vectors(self):
        embedder = FakeEmbedder()
        chat = ChatService(self.store, embedder=embedder)
        session = chat.start([self.kb()])
        question = "Công ty có được giữ căn cước không?"
        lexical = chat.ask(session["id"], question)
        self.assertEqual(lexical["citations"], [])
        hybrid = chat.ask(session["id"], question, semantic=True)
        self.assertEqual(hybrid["retrieval"]["mode"], "hybrid")
        self.assertIn("giấy tờ tùy thân", hybrid["citations"][0]["evidence"]["quote"])
        self.assertIsNone(hybrid["citations"][0]["lexical_rank"])
        chat.ask(session["id"], question, semantic=True)
        self.assertEqual(len(embedder.calls), 3)  # passages once, then only the question each time

    def test_private_kb_or_embedding_error_falls_back_to_lexical(self):
        chat = ChatService(self.store, embedder=FakeEmbedder())
        private = chat.ask(chat.start([self.kb("private")])["id"], "Công ty có được giữ căn cước không?", semantic=True)
        self.assertEqual(private["retrieval"], {"mode": "lexical", "reason": "private_kb"})
        failing = ChatService(self.store, embedder=FakeEmbedder("provider_unavailable"))
        result = failing.ask(failing.start([self.kb()])["id"], "giữ bản chính giấy tờ", semantic=True)
        self.assertEqual(result["retrieval"]["reason"], "embedding_error")
        self.assertTrue(result["citations"])

    def test_batches_received_before_a_rate_limit_stay_cached(self):
        from legal_ai.rag.dense import DenseIndex

        class Limited(FakeEmbedder):
            MAX_BATCH = 2

            def embed(self, texts):
                if len(self.calls) == 2:
                    raise ProviderError("quota_exhausted")
                return super().embed(texts)

        texts = [f"đoạn {n}" for n in range(5)]
        limited = Limited()
        with self.assertRaises(ProviderError):
            DenseIndex(self.store, limited).vectors(texts)
        self.assertEqual(limited.calls, [texts[:2], texts[2:4]], "one request per batch")
        resumed = FakeEmbedder()
        resumed.MAX_BATCH = 2
        self.assertEqual(len(DenseIndex(self.store, resumed).vectors(texts)), 5)
        self.assertEqual(resumed.calls, [texts[4:]], "only the batch that failed is sent again")

    def test_keyword_match_far_below_best_similarity_is_dropped(self):
        passages = [{"claim_id": n, "evidence": {"quote": q}, "scope": []} for n, q in
                    (("a", "Người sử dụng lao động phải thông báo kết quả thử việc"), ("b", "Thời gian thử việc do hai bên thỏa thuận"))]
        question = "Người sử dụng lao động phải thông báo kết quả thử việc không?"
        self.assertEqual(len(retrieve(passages, question)), 2)  # lexical gate alone keeps both
        kept = hybrid_retrieve(passages, question, [0.90, 0.78])
        self.assertEqual([c["claim_id"] for c in kept], ["a"])
        self.assertEqual(len(hybrid_retrieve(passages, question, [0.90, 0.85])), 2)

    def test_router_embeddings_normalizes_orders_and_checks_dimensions(self):
        class Response:
            status = 200
            headers = {"Content-Type": "application/json"}
            def __init__(self, body):
                self.body = body
            def __enter__(self):
                return self
            def __exit__(self, *_):
                pass
            def read(self, _):
                return self.body
        settings = {"9ROUTER_URL": "https://example.test/v1", "9ROUTER_KEY": "k"}
        embedder = RouterEmbeddings(settings, model="m", approved_route=True, max_calls=2, dimensions=64)
        body = json.dumps({"data": [{"index": 1, "embedding": [0.0, 2.0] + [0.0] * 62}, {"index": 0, "embedding": [3.0] + [0.0] * 63}]}).encode()
        with patch("legal_ai.providers.router.build_opener") as opener:
            opener.return_value.open.return_value = Response(body)
            vectors = embedder.embed(["a", "b"])
            sent = json.loads(opener.return_value.open.call_args.args[0].data)
            self.assertEqual(sent, {"model": "m", "input": ["a", "b"], "dimensions": 64})
            self.assertEqual(vectors[0][0], 1.0)
            self.assertEqual(vectors[1][1], 1.0)
            opener.return_value.open.return_value = Response(json.dumps({"data": [{"index": 0, "embedding": [1.0]}]}).encode())
            with self.assertRaises(ProviderError):
                embedder.embed(["a"])
            with self.assertRaises(ProviderError) as spent:
                embedder.embed(["a"])  # budget of 2 calls is spent
            self.assertEqual(spent.exception.code, "quota_exhausted")
        limited = RouterEmbeddings(settings, model="m", approved_route=True, max_calls=2, dimensions=64)
        with patch("legal_ai.providers.router.build_opener") as opener:
            opener.return_value.open.side_effect = HTTPError("https://example.test/v1/embeddings", 429, "Too Many Requests", {}, None)
            with self.assertRaises(ProviderError) as refused:
                limited.embed(["a"])
            self.assertEqual(refused.exception.code, "rate_limited", "a provider 429 is not Lexora's own budget")
        with self.assertRaises(ValueError):
            RouterEmbeddings({"9ROUTER_URL": "http://34.0.0.1:20128", "9ROUTER_KEY": "k"}, model="m", approved_route=True)


if __name__ == "__main__":
    unittest.main()
