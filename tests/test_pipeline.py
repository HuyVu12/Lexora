"""Offline invariants, including corrupted evidence and failure paths."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import random
import sys
import tempfile
import threading
import unittest
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.common.io import digest, read_jsonl
from legal_ai.ingestion.parser import parse
from legal_ai.ingestion.vbpl_html import legal_html, extract_paragraphs
from legal_ai.normalization.text import normalize, source_span
from legal_ai.providers.pilot import CachedProvider, ProviderError
from legal_ai.retrieval.bm25 import search, tokens
from legal_ai.schemas.contract import validate_document, validate_unit, validate_claim, unit_version
from legal_ai.validation.bundle import validate_bundle
from legal_ai.validation.evidence import align_quote, check_evidence, validate_record

spec = importlib.util.spec_from_file_location("fixture_builder", ROOT / "scripts/build_fixture.py")
fixture_builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_builder)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.doc, self.units, self.evidence, self.claim = fixture_builder.build(self.temp.name)

    def test_fixture_roundtrip_and_unknown_not_accepted(self):
        folder = Path(self.temp.name)
        results = validate_bundle(*[read_jsonl(folder / f"{name}.jsonl") for name in ("documents", "units", "evidence", "claims")])
        self.assertEqual(results[0]["decision"], "needs_review")
        self.assertTrue(self.doc["synthetic"])

    def test_normalization_maps_combining_and_non_bmp(self):
        raw = "a\u0306\u0301\r\n😀e\u0301"
        result = normalize(raw)
        self.assertEqual(result["text"], "ắ\n😀é")
        self.assertEqual(source_span(result, 0, 1), (0, 3))
        self.assertEqual(source_span(result, 1, 2), (3, 5))
        self.assertEqual(source_span(result, 2, 3), (5, 6))
        self.assertEqual(source_span(result, 3, 4), (6, 8))

    def test_normalization_fuzz_against_unicode_reference(self):
        rng = random.Random(42)
        for _ in range(200):
            raw = "".join(rng.choice("aê\u0301\u0323\u0306\r\n😀\u1100\u1161\u11a8") for _ in range(40))
            expected = unicodedata.normalize("NFC", raw.replace("\r\n", "\n").replace("\r", "\n"))
            result = normalize(raw)
            self.assertEqual(result["text"], expected)
            self.assertEqual(len(result["text"]), len(result["raw_spans"]))

    def test_parser_retains_all_text_and_parent_context(self):
        raw = (ROOT / "tests/fixtures/synthetic-law.txt").read_text(encoding="utf-8")
        normalized = normalize(raw)
        result = parse(normalized, "fixture", "version")
        self.assertEqual(result["unassigned_text"] + "".join(u["text"] for u in result["units"]), normalized["text"])
        clause = next(u for u in result["units"] if u["unit_id"].endswith("article-1/clause-2"))
        self.assertIn("Theo Điều 2", clause["text"])
        self.assertEqual(sum(u["unit_type"] == "article" for u in result["units"]), 2)
        for unit in result["units"]:
            validate_unit(unit)

    def test_duplicate_gap_and_orphan_are_audited_not_lost(self):
        raw = "1. Orphan\nĐiều 1. First\n1. A\n3. Gap\n3. Duplicate\n"
        result = parse(normalize(raw), "fixture", "v1")
        self.assertEqual({a["code"] for a in result["audit"]}, {"orphan_heading", "sequence_gap", "duplicate_heading"})
        self.assertEqual(len({u["unit_id"] for u in result["units"]}), len(result["units"]))
        self.assertEqual(result["unassigned_text"] + "".join(u["text"] for u in result["units"]), raw)

    def test_exact_quote_rejects_ambiguous_and_missing(self):
        unit = next(u for u in self.units if "7 ngày" in u["text"])
        self.assertEqual(check_evidence(align_quote(unit, "7 ngày"), self.units), [])
        for quote in (" ", "7 ngày làm việc", ""):
            with self.assertRaises(ValueError):
                align_quote(unit, quote)

    def test_unicode_codepoint_offsets_not_utf16(self):
        unit = next(u for u in self.units if "😀" in u["text"])
        evidence = align_quote(unit, "😀")
        self.assertEqual(evidence["end"] - evidence["start"], 1)

    def test_corrupt_quote_hash_or_version_is_rejected(self):
        for field, value in (("quote", "X" * len(self.evidence[0]["quote"])), ("normalized_sha256", "0" * 64), ("unit_version_id", "missing"), ("start", True)):
            rows = deepcopy(self.evidence)
            rows[0][field] = value
            self.assertEqual(validate_record(self.claim, rows, self.units)["decision"], "rejected")

    def test_stale_unit_hash_is_detected(self):
        rows = deepcopy(self.units)
        rows[0]["text"] += "changed"
        with self.assertRaises(ValueError):
            validate_bundle([self.doc], rows, self.evidence, [self.claim])

    def test_missing_evidence_and_wrong_slot_text_rejected(self):
        self.assertEqual(validate_record(self.claim, [], self.units)["decision"], "rejected")
        claim = deepcopy(self.claim)
        claim["slots"]["deadlines"]["text"] = "7 ngày làm việc"
        self.assertIn("slot_text_not_in_evidence", validate_record(claim, self.evidence, self.units)["reasons"])

    def test_empty_claims_still_validate_evidence(self):
        evidence = deepcopy(self.evidence)
        evidence[0]["quote"] = "X" * len(evidence[0]["quote"])
        with self.assertRaises(ValueError):
            validate_bundle([self.doc], self.units, evidence, [])

    def test_dangling_parent_duplicate_id_rejected(self):
        for rows in (self.units[1:], self.units + [self.units[0]]):
            with self.assertRaises(ValueError):
                validate_bundle([self.doc], rows, self.evidence, [self.claim])

    def test_cross_document_parent_rejected(self):
        rows = deepcopy(self.units)
        rows[0]["document_id"] = "another"
        with self.assertRaises(ValueError):
            validate_bundle([self.doc], rows, self.evidence, [])

    def test_schema_rejects_unknown_field_and_invalid_dates(self):
        document = deepcopy(self.doc)
        document["effective_from"] = "2026-02-30"
        with self.assertRaises(ValueError):
            validate_document(document)
        claim = deepcopy(self.claim)
        claim["ignored_typo"] = True
        with self.assertRaises(ValueError):
            validate_claim(claim)

    def test_unknown_and_not_present_are_distinct(self):
        claim = deepcopy(self.claim)
        claim["slots"]["conditions"] = {"state": "unknown", "text": "inferred", "evidence_ids": []}
        with self.assertRaises(ValueError):
            validate_claim(claim)

    def test_retrieval_keeps_parent_condition_and_evidence(self):
        result = search(self.units, "7 ngày", 1)[0]
        self.assertTrue(result["unit_id"].endswith("point-a"))
        self.assertTrue(any("trường hợp A" in row["quote"] for row in result["parent_evidence"]))
        for row in [result["evidence"], *result["parent_evidence"]]:
            self.assertEqual(check_evidence(row, self.units), [])
        self.assertIn("không", tokens("Không quá 7 ngày 85%"))
        self.assertEqual(search(self.units, "zzzzzz"), [])

    def test_retrieval_tie_break_is_stable(self):
        self.assertEqual(search(self.units, "Điều"), search(list(reversed(self.units)), "Điều"))

    def test_vbpl_flight_byte_lengths_and_navigation_isolation(self):
        body = '<p class="prov-article">Điều 1. 😀</p><p>1. Không xóa dấu.</p>'
        flight = f"f:T{len(body.encode('utf-8')):x}," + body
        page = '<nav>FAKE</nav><script>self.__next_f.push(' + json.dumps([1, flight]) + ')</script>'
        extracted = extract_paragraphs(legal_html(page))
        self.assertEqual(extracted["text"], "Điều 1. 😀\n1. Không xóa dấu.\n")
        with self.assertRaises(ValueError):
            legal_html('<html>Điều 1. Navigation only</html>')


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def provider(self, transport, **kwargs):
        return CachedProvider(transport, self.temp.name, model="synthetic", revision="test-v1", prompt_hash=digest("prompt"), schema_version="1.0.0-pilot", **kwargs)

    def test_cache_reuses_identical_requests_and_invalidates_revision(self):
        calls = []
        def transport(*args):
            calls.append(args)
            return {"synthetic": True}
        provider = self.provider(transport)
        self.assertEqual(provider.request("generate", "x"), provider.request("generate", "x"))
        self.assertEqual(len(calls), 1)
        provider.config["revision"] = "test-v2"
        provider.request("generate", "x")
        self.assertEqual(len(calls), 2)

    def test_timeout_busy_and_no_late_cache_write(self):
        release, started = threading.Event(), threading.Event()
        def transport(*args):
            started.set()
            release.wait(1)
            return "synthetic"
        provider = self.provider(transport, timeout=0.01)
        try:
            with self.assertRaises(ProviderError) as error:
                provider.request("generate", "x")
            self.assertEqual(error.exception.code, "timeout")
            self.assertTrue(started.is_set())
            with self.assertRaises(ProviderError) as error:
                provider.request("generate", "x")
            self.assertEqual(error.exception.code, "provider_busy")
        finally:
            release.set()
            provider.pending.result(timeout=1)
        self.assertEqual(list(Path(self.temp.name).glob("*.json")), [])

    def test_transport_error_has_structured_reason(self):
        def transport(*args):
            raise OSError("synthetic outage")
        with self.assertRaises(ProviderError) as error:
            self.provider(transport).request("embed", "x")
        self.assertEqual(error.exception.code, "transport_error")

    def test_corrupt_cache_fails_closed(self):
        provider = self.provider(lambda *args: "first")
        provider.request("generate", "x")
        path = next(Path(self.temp.name).glob("*.json"))
        value = json.loads(path.read_text(encoding="utf-8"))
        value["response"] = "tampered"
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(ProviderError) as error:
            provider.request("generate", "x")
        self.assertEqual(error.exception.code, "cache_corrupt")


if __name__ == "__main__":
    unittest.main()
