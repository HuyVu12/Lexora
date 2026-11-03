"""Graph identity, reference binding and evidence integrity; no network."""

from copy import deepcopy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from legal_ai.common.io import digest, canonical
from legal_ai.ingestion.parser import parse
from legal_ai.kb.graph import make_graph, build_graph
from legal_ai.kb.references import detect_references
from legal_ai.kb.viewer import render_viewer
from legal_ai.normalization.text import normalize
from legal_ai.schemas.contract import VERSION
from legal_ai.validation.evidence import check_evidence


def fixture(raw, document_id="fixture"):
    normalized = normalize(raw)
    version = normalized["normalized_sha256"]
    document = {"schema_version": VERSION, "document_id": document_id, "document_version_id": version, "snapshot_id": digest(raw), "title": "SYNTHETIC — NOT REAL LAW", "source_url": "fixture://graph", "accessed_at": "2026-11-02T00:00:00Z", "source_sha256": digest(raw), "effective_from": None, "effective_to": None, "legal_status": "unknown", "synthetic": True}
    return document, parse(normalized, document_id, version)["units"]


class GraphTests(unittest.TestCase):
    def test_heading_is_not_a_reference(self):
        _, units = fixture("Điều 1. Ví dụ\nNội dung.\n")
        self.assertEqual(detect_references(units[0], units), [])

    def test_internal_reference_is_resolved_with_exact_source(self):
        _, units = fixture("Điều 1. Một\nTheo khoản 1 Điều 2 của Bộ luật này.\nĐiều 2. Hai\n1. Nội dung.\n")
        references = detect_references(units[0], units)
        self.assertEqual(len(references), 1)
        self.assertEqual(references[0]["status"], "resolved")
        self.assertEqual(references[0]["target_unit_version_ids"], [units[2]["unit_version_id"]])
        self.assertEqual(check_evidence(references[0]["evidence"], units), [])

    def test_missing_target_remains_mention_not_fake_unit_or_edge(self):
        document, units = fixture("Điều 1. Một\nTheo Điều 99 của Bộ luật này.\n")
        graph = make_graph([document], units, [], [])
        self.assertEqual(graph["references"][0]["status"], "pending")
        self.assertFalse(any(edge["kind"] == "REFERENCES" for edge in graph["edges"]))
        self.assertEqual(graph["summary"]["nodes"]["LegalUnit"], 1)

    def test_cross_document_requires_explicit_alias(self):
        d1, u1 = fixture("Điều 1. Một\nTheo khoản 1 Điều 2 của Bộ luật Lao động.\n", "source")
        d2, u2 = fixture("Điều 2. Hai\n1. Nội dung.\n", "labour")
        self.assertEqual(detect_references(u1[0], u1 + u2)[0]["status"], "external")
        graph = make_graph([d1, d2], u1 + u2, [], [], aliases={"Bộ luật Lao động": "labour"})
        self.assertEqual(graph["summary"]["edges"]["REFERENCES"], 1)
        self.assertEqual(graph["references"][0]["target_document_id"], "labour")

    def test_explicit_point_list_resolves_all_and_preserves_d(self):
        _, units = fixture("Điều 1. Một\nTheo các điểm a, đ và h khoản 1 Điều 2 của Bộ luật này.\nĐiều 2. Hai\n1. Nội dung:\na) A\nđ) D\nh) H\n")
        ref = detect_references(units[0], units)[0]
        self.assertEqual(ref["point_labels"], ["a", "đ", "h"])
        self.assertEqual(ref["status"], "resolved")
        self.assertEqual(len(ref["target_unit_version_ids"]), 3)
        self.assertIn("các điểm", ref["evidence"]["quote"])
        missing = detect_references(units[0], units[:-1])[0]
        self.assertEqual(missing["status"], "pending")
        self.assertEqual(missing["target_unit_version_ids"], [])

    def test_multiple_clause_list_is_not_silently_bound_to_article(self):
        _, units = fixture("Điều 1. Một\nTheo các khoản 1, 2 và 3 Điều 2.\nĐiều 2. Hai\n1. Nội dung.\n")
        ref = detect_references(units[0], units)[0]
        self.assertEqual(ref["status"], "needs_review")
        self.assertEqual(ref["target_unit_version_ids"], [])

    def test_repeated_mentions_have_distinct_offsets_and_ids(self):
        _, units = fixture("Điều 1. Một\nTheo Điều 2; theo Điều 2.\nĐiều 2. Hai\nNội dung.\n")
        refs = detect_references(units[0], units)
        self.assertEqual(len(refs), 2)
        self.assertNotEqual(refs[0]["reference_id"], refs[1]["reference_id"])
        for ref in refs:
            self.assertEqual(check_evidence(ref["evidence"], units), [])

    def test_ambiguous_same_article_label_is_not_linked(self):
        _, units = fixture("Chương I\nĐiều 1. Một\nTheo Điều 2.\nĐiều 2. Hai\nA\nChương II\nĐiều 2. Hai khác\nB\n")
        source = next(unit for unit in units if unit["label"] == "1" and unit["unit_type"] == "article")
        self.assertEqual(detect_references(source, units)[0]["status"], "ambiguous")

    def test_candidate_claims_are_always_review_and_not_inferred_actors(self):
        document, units = fixture("Điều 1. Một\nChủ thể A phải làm B trừ trường hợp C.\n")
        graph = make_graph([document], units, [], [], include_candidates=True)
        claim = next(node for node in graph["nodes"] if node["kind"] == "NormClaim")
        self.assertEqual(claim["payload"]["validation"]["decision"], "needs_review")
        self.assertEqual(claim["payload"]["slots"]["actor"]["state"], "unknown")
        self.assertIn("trừ trường hợp C", claim["payload"]["slots"]["action"]["text"])

    def test_all_edges_have_real_endpoints_and_valid_evidence(self):
        document, units = fixture("Điều 1. Một\nTheo Điều 2.\nĐiều 2. Hai\nA phải làm B.\n")
        graph = make_graph([document], units, [], [], include_candidates=True)
        node_ids = {node["id"] for node in graph["nodes"]}
        evidence = {node["payload"]["evidence_id"]: node["payload"] for node in graph["nodes"] if node["kind"] == "Evidence"}
        for edge in graph["edges"]:
            self.assertTrue({edge["source"], edge["target"]} <= node_ids)
            self.assertTrue(edge["evidence_ids"])
            for eid in edge["evidence_ids"]:
                self.assertEqual(check_evidence(evidence[eid], units), [])

    def test_graph_hash_stable_under_record_order(self):
        document, units = fixture("Điều 1. Một\nTheo Điều 2.\nĐiều 2. Hai\nA phải làm B.\n")
        first = make_graph([document], units, [], [], include_candidates=True)
        second = make_graph([document], list(reversed(units)), [], [], include_candidates=True)
        self.assertEqual(first, second)

    def test_corrupt_unit_cannot_build_graph(self):
        document, units = fixture("Điều 1. Một\nNội dung.\n")
        units[0]["text"] += "tamper"
        with self.assertRaises(ValueError):
            make_graph([document], units, [], [])

    def test_embedded_viewer_escapes_script_markup(self):
        document, units = fixture("Điều 1. Một\n</script><script>BAD()</script>\n")
        graph = make_graph([document], units, [], [])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "index.html"
            render_viewer(graph, path)
            html = path.read_text(encoding="utf-8")
            self.assertNotIn('</script><script>BAD()', html)
            self.assertNotIn('__GRAPH_JSON__', html)
            self.assertIn('connect-src \'none\'', html)

    def test_sqlite_constraints_and_new_output_only(self):
        from legal_ai.common.io import write_jsonl
        document, units = fixture("Điều 1. Một\nTheo Điều 2.\nĐiều 2. Hai\nA phải làm B.\n")
        with tempfile.TemporaryDirectory() as temp:
            bundle, output = Path(temp) / "bundle", Path(temp) / "graph"
            for name, rows in (("documents", [document]), ("units", units), ("evidence", []), ("claims", [])):
                write_jsonl(bundle / f"{name}.jsonl", rows)
            manifest = build_graph(bundle, output)
            with closing(sqlite3.connect(output / "graph.sqlite")) as connection:
                self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
                count = connection.execute("SELECT count(*) FROM edges WHERE kind = ?", ("REFERENCES",)).fetchone()[0]
                self.assertEqual(count, 1)
            with self.assertRaises(ValueError):
                build_graph(bundle, output)
