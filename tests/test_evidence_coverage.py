"""evidence-coverage-v1: leaf-complete recall of the packed context, on a synthetic statute (not real law)."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_retrieval_run import SECOND, SYNTHETIC, bundle
from legal_ai.common.io import read_jsonl, write_json
from legal_ai.evaluation import evidence_coverage as ec
from legal_ai.evaluation.retrieval_run import _recall, rescore_evidence, run
from legal_ai.indexing.records import structural_records

ART2 = "syn-a/chapter-i/article-2"
CLAUSE1 = "syn-a/chapter-i/article-1/clause-1"
CLAUSE2 = f"{ART2}/clause-2"  # lead-in "2. ... khác:" with Points a and b
POINT_A, POINT_B = f"{CLAUSE2}/point-a", f"{CLAUSE2}/point-b"


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.documents, self.units, self.texts = bundle(None, {"syn-a": SYNTHETIC, "syn-b": SECOND})
        self.tree = ec.EvidenceTree(self.units)
        self.by_id = {u["unit_id"]: u for u in self.units}
        self.dk2 = {r["unit_ids"][0]: r for r in structural_records(self.documents, self.units, self.texts)}

    def chunk(self, start, end, unit_ids):
        """A DK1-style window: an exact span that carries the ID of every unit it touches."""
        return {"record_id": f"dk1:{start}", "condition": "DK1", "document_id": "syn-a", "source_start": start, "source_end": end,
                "text": self.texts["syn-a"][start:end], "index_text": self.texts["syn-a"][start:end], "unit_ids": unit_ids}

    def test_pieces_are_leaves_plus_the_lead_in_of_every_non_leaf_on_the_way(self):
        clause = self.by_id[CLAUSE2]
        pieces = self.tree.pieces(CLAUSE2)
        self.assertEqual(sorted(pieces), sorted([("syn-a", clause["source_start"], self.by_id[POINT_A]["source_start"]),
                                                 ("syn-a", self.by_id[POINT_A]["source_start"], self.by_id[POINT_A]["source_end"]),
                                                 ("syn-a", self.by_id[POINT_B]["source_start"], self.by_id[POINT_B]["source_end"])]))
        self.assertEqual(len(self.tree.pieces(ART2)), 1 + 1 + 3, "article lead, clause 1, clause 2 lead and its two Points")
        self.assertEqual(self.tree.pieces("syn-a/missing"), [])

    def test_a_dk1_chunk_clipping_a_clause_gets_touch_credit_but_no_leaf_credit(self):
        unit = self.by_id[CLAUSE1]
        clip = self.chunk(unit["source_start"], unit["source_start"] + 20, [CLAUSE1])
        self.assertEqual(_recall([clip], [CLAUSE1]), 1.0, "legacy recall: the chunk carries the unit ID")
        row = ec.question_coverage(self.tree, [CLAUSE1], [clip])
        self.assertEqual((row["leaf_recall_tau1.0"], row["leaf_recall_tau0.8"], row["leaf_recall_tau0.5"], row["complete"]), (0.0, 0.0, 0.0, 0.0))
        self.assertAlmostEqual(row["chars_recall"], 20 / (unit["source_end"] - unit["source_start"]))
        whole = self.chunk(unit["source_start"], unit["source_end"], [CLAUSE1])
        self.assertEqual(ec.question_coverage(self.tree, [CLAUSE1], [whole])["complete"], 1.0)

    def test_a_dk2_leaf_record_with_printed_lead_in_completes_its_clause(self):
        both = [self.dk2[POINT_A], self.dk2[POINT_B]]
        row = ec.question_coverage(self.tree, [CLAUSE2], both)
        self.assertEqual((row["leaf_recall_tau1.0"], row["complete"], row["chars_recall"]), (1.0, 1.0, 1.0),
                         "the Clause lead-in is printed with its Points, so two Points complete the Clause")
        self.assertEqual(ec.question_coverage(self.tree, [CLAUSE2], both[:1])["leaf_recall_tau1.0"], 2 / 3)
        self.assertEqual(ec.question_coverage(self.tree, [CLAUSE2], both[:1])["complete"], 0.0)
        silent = [r | {"index_text": r["text"]} for r in both]  # A record that does not print its ancestors adds only its span.
        row = ec.question_coverage(self.tree, [CLAUSE2], silent)
        self.assertEqual((row["leaf_recall_tau1.0"], row["complete"]), (2 / 3, 0.0))
        layout = [r | {"pack_layout": {"group": [], "header": "", "body": ""}} for r in both]
        self.assertEqual(ec.question_coverage(self.tree, [CLAUSE2], layout)["leaf_recall_tau1.0"], 2 / 3)

    def test_tau_thresholds_and_the_boundary_tolerance(self):
        unit = self.by_id[CLAUSE1]
        length = unit["source_end"] - unit["source_start"]
        start = unit["source_start"]
        at = lambda covered, tau: ec.question_coverage(self.tree, [CLAUSE1], [self.chunk(start, start + covered, [CLAUSE1])])[f"leaf_recall_tau{tau}"]
        half, most = -(-length // 2), -(-length * 8 // 10)
        self.assertEqual((at(half, 0.5), at(half - 1, 0.5)), (1.0, 0.0))
        self.assertEqual((at(most, 0.8), at(most - 1, 0.8)), (1.0, 0.0))
        self.assertEqual((at(length - ec.BOUNDARY, 1.0), at(length - ec.BOUNDARY - 1, 1.0)), (1.0, 0.0), "tau 1.0 tolerates two boundary characters")
        self.assertEqual(at(length - ec.BOUNDARY, 0.8), 1.0)
        self.assertEqual(ec.question_coverage(self.tree, [CLAUSE1], [self.chunk(start, start + length - 1, [CLAUSE1])])["complete"], 1.0)

    def test_complete_needs_every_piece_of_every_gold_unit(self):
        first, second = self.by_id[CLAUSE1], self.by_id["syn-a/chapter-i/article-1/clause-2"]
        gold = [CLAUSE1, "syn-a/chapter-i/article-1/clause-2"]
        one = ec.question_coverage(self.tree, gold, [self.chunk(first["source_start"], first["source_end"], [CLAUSE1])])
        self.assertEqual((one["leaf_recall_tau1.0"], one["complete"]), (0.5, 0.0))
        self.assertAlmostEqual(one["chars_recall"], 0.5)
        both = ec.question_coverage(self.tree, gold, [self.chunk(first["source_start"], second["source_end"], gold)])
        self.assertEqual((both["leaf_recall_tau1.0"], both["complete"]), (1.0, 1.0))
        self.assertIsNone(ec.question_coverage(self.tree, [], [self.dk2[POINT_A]]))

    def test_spans_of_other_documents_do_not_count(self):
        unit = self.by_id[CLAUSE1]
        other = self.chunk(unit["source_start"], unit["source_end"], [CLAUSE1]) | {"document_id": "syn-b"}
        self.assertEqual(ec.question_coverage(self.tree, [CLAUSE1], [other])["complete"], 0.0)


class RunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        bundle(self.root / "bundle", {"syn-a": SYNTHETIC, "syn-b": SECOND})
        self.questions = self.root / "questions.json"
        write_json(self.questions, {"description": "synthetic", "questions": [
            {"question_id": "Q1", "family_id": "F1", "question": "Tiền lương thử nghiệm ít nhất bao nhiêu phần trăm?", "relevant_unit_ids": [f"{ART2}/clause-1"]},
            {"question_id": "Q2", "question": "Trả lương bằng tiền mặt hay chuyển khoản?", "relevant_unit_ids": [CLAUSE2]},
            {"question_id": "Q3", "question": "Câu hỏi ngoài phạm vi", "relevant_unit_ids": []}]})
        self.shared = self.root / "shared.json"
        write_json(self.shared, {"status": "draft", "top_k": 2, "context_packing": "P3", "token_budgets": [20, 60, 400],
                                 "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75, "recall_k": [1, 3]}})
        self.dk1, self.dk2 = self.root / "dk1.json", self.root / "dk2.json"
        write_json(self.dk1, {"condition": "DK1", "representation": "fixed_chunks", "chunk_tokens": 12, "overlap_tokens": 2, "status": "draft"})
        write_json(self.dk2, {"condition": "DK2", "representation": "structural_units", "max_tokens": 384, "status": "draft"})

    def go(self, condition, name):
        return run(self.root / "bundle", self.questions, condition, self.shared, self.root / name)

    def test_every_run_carries_the_metrics_next_to_the_unchanged_legacy_ones(self):
        metrics = self.go(self.dk2, "dk2")
        block = metrics["evidence_coverage"]
        self.assertEqual(block["version"], ec.VERSION)
        for key in ("leaf_recall_tau0.5", "leaf_recall_tau0.8", "leaf_recall_tau1.0", "chars_recall", "complete"):
            self.assertEqual(sorted(block[f"mean_{key}_at_tokens"]), ["20", "400", "60"])
        self.assertEqual(block["scored_questions"], 2)
        rows = {r["question_id"]: r for r in read_jsonl(self.root / "dk2" / "predictions.jsonl")}
        self.assertIsNone(rows["Q3"]["evidence_coverage"]["complete"]["400"])
        self.assertEqual(rows["Q1"]["evidence_coverage"]["leaf_recall_tau1.0"]["400"], 1.0)
        self.assertEqual(json.loads((self.root / "dk2" / "manifest.json").read_text(encoding="utf-8"))["evidence_coverage_version"], ec.VERSION)
        for legacy in ("mean_recall", "mean_complete", "mean_recall_at_tokens", "mean_complete_at_tokens", "tokens_to_reach", "mean_context_tokens"):
            self.assertIn(legacy, metrics)
        self.assertEqual(rows["Q1"]["recall_at_tokens"]["400"], 1.0)

    def test_legacy_recall_counts_the_clipped_clause_that_the_new_metric_does_not(self):
        self.go(self.dk1, "dk1")
        rows = read_jsonl(self.root / "dk1" / "predictions.jsonl")
        legacy = sum(r["recall_at_tokens"]["20"] for r in rows if r["gold_unit_ids"])
        leaf = sum(r["evidence_coverage"]["leaf_recall_tau1.0"]["20"] for r in rows if r["gold_unit_ids"])
        self.assertGreater(legacy, leaf)

    def test_rescore_reproduces_a_new_run_and_gives_an_old_run_the_metric(self):
        metrics = self.go(self.dk2, "dk2")
        result = rescore_evidence(self.root / "dk2")
        self.assertEqual(result["legacy_recall_mismatches"], 0)
        self.assertEqual(result["metrics"], metrics["evidence_coverage"])
        stored = {r["question_id"]: r["evidence_coverage"] for r in read_jsonl(self.root / "dk2" / "predictions.jsonl")}
        for qid, row in result["questions"].items():
            self.assertEqual({k: v for k, v in row.items() if k != "family_id"}, stored[qid])
        self.assertEqual(result["questions"]["Q1"]["family_id"], "F1")
        self.assertTrue((self.root / "dk2" / "metrics-evidence.json").exists())
        # An old run: predictions without the block (as written before evidence-coverage-v1).
        self.go(self.dk1, "old")
        path = self.root / "old" / "predictions.jsonl"
        rows = read_jsonl(path)
        expected = {r["question_id"]: r["evidence_coverage"] for r in rows}
        path.write_text("".join(json.dumps({k: v for k, v in r.items() if k != "evidence_coverage"}, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        manifest = json.loads((self.root / "old" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(rescore_evidence(self.root / "old")["legacy_recall_mismatches"], 0)
        for qid, row in json.loads((self.root / "old" / "metrics-evidence.json").read_text(encoding="utf-8"))["questions"].items():
            self.assertEqual({k: v for k, v in row.items() if k != "family_id"}, expected[qid])
        self.assertEqual(manifest["evidence_coverage_version"], ec.VERSION)


if __name__ == "__main__":
    unittest.main()
