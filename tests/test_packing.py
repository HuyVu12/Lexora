"""Context packing (`pack-article-v1`), budget curves and verification load, on a synthetic statute (not real law)."""

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
from legal_ai.evaluation.answer_run import pack_with_groups, packer_for, verification_load
from legal_ai.evaluation.preflight import check
from legal_ai.evaluation.retrieval_run import recall_steps, run, score_top, tokens_to_reach, within_budget
from legal_ai.indexing.packing import SIBLING_GROUP_TOKENS, Packer, condition_mode, evidence_payload
from legal_ai.indexing.records import kb_unit_records, structural_records, token_spans


class PackerTests(unittest.TestCase):
    def setUp(self):
        self.documents, self.units, self.texts = bundle(None, {"syn-a": SYNTHETIC, "syn-b": SECOND})
        self.records = structural_records(self.documents, self.units, self.texts)
        self.by_unit = {r["unit_ids"][0]: r for r in self.records}

    def ranked(self, *suffixes):
        return [self.by_unit[f"syn-a/chapter-i/{s}"] for s in suffixes]

    def test_p0_is_the_flat_list_and_dk1_always_packs_flat(self):
        ranked = self.ranked("article-2/clause-2/point-b", "article-1/clause-1")
        packed = Packer("P0").pack(ranked, 10 ** 6)
        self.assertEqual([b["text"] for b in packed["blocks"]], [r["index_text"] for r in ranked])
        self.assertEqual(packed["tokens"], sum(len(token_spans(r["index_text"])) for r in ranked))
        self.assertEqual((condition_mode("DK1", "P2"), condition_mode("DK2", None), condition_mode("DK3", "P1")), ("P0", "P0", "P1"))
        with self.assertRaises(ValueError):
            condition_mode("DK2", "P9")

    def test_p1_groups_by_article_in_first_appearance_order_and_text_order_inside(self):
        ranked = self.ranked("article-2/clause-2/point-b", "article-1/clause-2", "article-2/clause-1", "article-1/clause-1")
        packer = Packer("P1", self.records, self.units, self.documents)
        packed = packer.pack(ranked, 10 ** 6)
        self.assertEqual([b["record"]["unit_ids"][0].split("/", 2)[2] for b in packed["blocks"]],
                         ["article-2/clause-1", "article-2/clause-2/point-b", "article-1/clause-1", "article-1/clause-2"])
        self.assertEqual([b["id"] for b in packed["blocks"]], ["E01", "E02", "E03", "E04"], "block IDs follow the reading order")
        self.assertEqual(len(packed["groups"]), 2)
        header = packed["groups"][0]["header"]
        self.assertTrue(header.startswith("Văn bản giả định syn-a\nChương I > Điều 2\nĐiều 2. Tiền lương giả định"))
        self.assertEqual(packed["blocks"][1]["text"].split("\n")[0], "Khoản 2 > Điểm b", "the body keeps the path below the Article")
        self.assertIn("trừ trường hợp hai bên có thỏa thuận khác", packed["blocks"][1]["text"], "the Clause lead stays with its Point")
        self.assertNotIn("Điều 2. Tiền lương", packed["blocks"][1]["text"], "the Article header is printed once")
        self.assertEqual(packed["tokens"], sum(g["header_tokens"] for g in packed["groups"]) + sum(b["token_count"] for b in packed["blocks"]))
        flat = Packer("P0").pack(ranked, 10 ** 6)
        self.assertLess(packed["tokens"], flat["tokens"], "headers printed once cost less than repeated on every record")
        payload = evidence_payload(packed)
        self.assertEqual([[p["id"] for p in g["passages"]] for g in payload], [["E01", "E02"], ["E03", "E04"]])
        self.assertEqual(evidence_payload(flat)[0], {"id": "E01", "text": ranked[0]["index_text"]})

    def test_budget_is_never_exceeded_and_units_are_not_repeated(self):
        ranked = self.ranked("article-2/clause-2/point-b", "article-1/clause-2", "article-2/clause-1", "article-1/clause-1", "article-3")
        for mode in ("P0", "P1", "P2"):
            packer = Packer(mode, self.records, self.units, self.documents)
            full = packer.pack(ranked, 10 ** 6)["tokens"]
            for budget in range(0, full + 5, 7):
                packed = packer.pack(ranked + ranked, budget)
                self.assertTrue(len(packed["blocks"]) == 1 or packed["tokens"] <= budget, (mode, budget))
                ids = [b["record"]["record_id"] for b in packed["blocks"]]
                self.assertEqual(len(ids), len(set(ids)), mode)
                self.assertIn(ranked[0]["record_id"], ids)
                if packed["next_budget"] is not None:
                    self.assertGreater(packer.pack(ranked, packed["next_budget"])["tokens"], packed["tokens"])

    def test_p2_adds_unranked_siblings_of_the_first_articles_within_the_group_cap(self):
        ranked = self.ranked("article-2/clause-1")
        packed = Packer("P2", self.records, self.units, self.documents).pack(ranked, 10 ** 6)
        units = [b["record"]["unit_ids"][0].split("/", 2)[2] for b in packed["blocks"]]
        self.assertEqual(units, ["article-2/clause-1", "article-2/clause-2/point-a", "article-2/clause-2/point-b"])
        self.assertEqual([b["sibling"] for b in packed["blocks"]], [False, True, True])
        self.assertLessEqual(packed["groups"][0]["header_tokens"] + sum(b["token_count"] for b in packed["blocks"]), SIBLING_GROUP_TOKENS)
        self.assertEqual(len(Packer("P1", self.records, self.units, self.documents).pack(ranked, 10 ** 6)["blocks"]), 1, "P1 adds nothing")

    def test_kb_records_keep_their_claim_lines_in_the_body(self):
        unit = next(u for u in self.units if u["unit_id"].endswith("article-2/clause-1"))
        sentence = {"start": unit["source_start"], "end": unit["source_end"] - 1}
        claim = {"claim_id": "c1", "unit_id": unit["unit_id"], "sentence": sentence, "modality": "obligation", "slots": {"actor": "Bên A"}}
        records = kb_unit_records("DK3", self.documents, self.units, self.texts, [claim], view="compact")
        record = next(r for r in records if r["claim_ids"])
        packed = Packer("P1", records, self.units, self.documents).pack([record], 10 ** 6)
        self.assertTrue(packed["blocks"][0]["text"].endswith("[Quy phạm 1] nghĩa vụ · Chủ thể: Bên A"))

    def test_article_packing_rejects_chunks(self):
        from legal_ai.indexing.records import fixed_chunks
        with self.assertRaisesRegex(ValueError, "one leaf unit"):
            Packer("P1", fixed_chunks(self.documents, self.units, self.texts, 400, 10), self.units, self.documents)


class BudgetCurveTests(unittest.TestCase):
    def setUp(self):
        self.documents, self.units, self.texts = bundle(None, {"syn-a": SYNTHETIC})
        self.records = structural_records(self.documents, self.units, self.texts)

    def test_recall_steps_agree_with_recall_at_every_budget(self):
        gold = ["syn-a/chapter-i/article-2", "syn-a/chapter-i/article-3"]
        for mode in ("P0", "P1", "P2"):
            packer = Packer(mode, self.records, self.units, self.documents)
            steps = recall_steps(self.records, gold, packer)
            self.assertEqual([t for t, _ in steps], sorted({t for t, _ in steps}), "breakpoints grow strictly")
            for budget in range(0, steps[-1][0] + 20, 3):
                expected = score_top(self.records, gold, [1], [budget], packer=packer)["recall_at_tokens"][str(budget)]
                at = [r for t, r in steps if t <= budget]
                self.assertEqual(at[-1] if at else steps[0][1], expected, (mode, budget))

    def test_tokens_to_reach_is_the_smallest_budget_of_the_mean_curve(self):
        steps = [[(10, 0.0), (30, 1.0)], [(20, 0.5), (40, 1.0)]]
        self.assertEqual(tokens_to_reach(steps, 0.25), 10, "the first record is always kept, even under its cost")
        self.assertEqual(tokens_to_reach(steps, 0.75), 30)
        self.assertEqual(tokens_to_reach(steps, 1.0), 40)
        self.assertIsNone(tokens_to_reach([[(10, 0.2)]], 0.5))

    def test_expanded_head_is_kept_and_the_tail_follows_unexpanded(self):
        from legal_ai.evaluation.retrieval_run import extend_tail
        head = [(3, 0.9), (7, 0.0), (1, 0.8)]
        ranked = [(3, 0.9), (1, 0.8), (5, 0.7), (7, 0.6), (2, 0.5)]
        self.assertEqual(extend_tail(head, ranked, 10), head + [(5, 0.7), (2, 0.5)])
        self.assertEqual(extend_tail(head, ranked, 4), head + [(5, 0.7)])

    def test_within_budget_p0_matches_the_old_rule(self):
        kept = within_budget(self.records, 60)
        used = 0
        for row in kept:
            used += len(token_spans(row["index_text"]))
        self.assertTrue(used <= 60 or len(kept) == 1)
        self.assertEqual(kept, self.records[:len(kept)])


class RunIntegrationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        bundle(self.root / "bundle", {"syn-a": SYNTHETIC})
        self.questions = self.root / "q.json"
        write_json(self.questions, {"questions": [
            {"question_id": "Q1", "question": "Tiền lương trả bằng tiền mặt hay chuyển khoản?", "relevant_unit_ids": ["syn-a/chapter-i/article-2"]}]})
        self.dk1, self.dk2 = self.root / "dk1.json", self.root / "dk2.json"
        write_json(self.dk1, {"condition": "DK1", "representation": "fixed_chunks", "chunk_tokens": 30, "overlap_tokens": 5})
        write_json(self.dk2, {"condition": "DK2", "representation": "structural_units", "max_tokens": 384})

    def shared(self, mode):
        path = self.root / f"shared-{mode}.json"
        write_json(path, {"top_k": 2, "context_packing": mode, "token_budgets": [40, 80],
                          "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75, "recall_k": [1, 3]}})
        return path

    def test_runs_record_packing_budgets_and_tokens_to_reach(self):
        metrics = run(self.root / "bundle", self.questions, self.dk2, self.shared("P1"), self.root / "dk2-p1")
        manifest = json.loads((self.root / "dk2-p1" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["context_packing"], {"version": "pack-article-v1", "mode": "P1"})
        self.assertEqual((manifest["token_budgets"], metrics["context_packing"]), ([40, 80], "P1"))
        self.assertEqual(set(metrics["tokens_to_reach"]), {"0.4", "0.8"})
        self.assertIn("mean_complete_at_tokens", metrics)
        dk1 = run(self.root / "bundle", self.questions, self.dk1, self.shared("P1"), self.root / "dk1-p1")
        self.assertEqual(dk1["context_packing"], "P0", "DK1 is always flat")
        report = check([self.root / "dk1-p1", self.root / "dk2-p1"])
        self.assertEqual(next(c for c in report["checks"] if c["check"] == "DK2-DK4 use the same context packing")["status"], "pass")

    def test_preflight_fails_when_structural_conditions_pack_differently(self):
        run(self.root / "bundle", self.questions, self.dk2, self.shared("P1"), self.root / "a")
        dk3 = self.root / "dk3.json"
        write_json(dk3, {"condition": "DK2", "representation": "structural_units", "max_tokens": 384})
        run(self.root / "bundle", self.questions, dk3, self.shared("P2"), self.root / "b")
        report = check([self.root / "a", self.root / "b"])
        self.assertEqual(next(c for c in report["checks"] if c["check"] == "DK2-DK4 use the same context packing")["status"], "fail")
        self.assertEqual(next(c for c in report["checks"] if c["check"] == "same retrieval settings")["status"], "fail")

    def test_answer_packing_matches_retrieval_packing(self):
        run(self.root / "bundle", self.questions, self.dk2, self.shared("P2"), self.root / "dk2")
        retrieval = json.loads((self.root / "dk2" / "manifest.json").read_text(encoding="utf-8"))
        records = {r["record_id"]: r for r in read_jsonl(self.root / "dk2" / "records.jsonl")}
        prediction = read_jsonl(self.root / "dk2" / "predictions.jsonl")[0]
        packer = packer_for(retrieval, list(records.values()))
        blocks, packed = pack_with_groups(prediction["ranked"], records, 50, 80, packer)
        self.assertEqual([b["record_id"] for b in blocks],
                         [r["record_id"] for r in within_budget([records[x["record_id"]] for x in prediction["ranked"]], 80, packer)])
        self.assertEqual(packed["tokens"], sum(g["header_tokens"] for g in packed["groups"]) + sum(b["token_count"] for b in blocks))


class VerificationLoadTests(unittest.TestCase):
    def test_cited_tokens_and_single_leaf_citations(self):
        units = {"a": {"unit_id": "a", "parent_id": None}, "a/1": {"unit_id": "a/1", "parent_id": "a"}, "a/2": {"unit_id": "a/2", "parent_id": "a"}}
        records = {"r1": {"unit_ids": ["a/1"]}, "r2": {"unit_ids": ["a", "a/1", "a/2"]}}
        answers = [
            {"status": "answered", "context": [{"id": "E01", "record_id": "r1", "unit_ids": ["a/1"], "token_count": 10, "group": 0},
                                               {"id": "E02", "record_id": "r2", "unit_ids": ["a", "a/1", "a/2"], "token_count": 30, "group": 0}],
             "context_groups": [{"header_tokens": 5}],
             "statements": [{"evidence_ids": ["E01"]}, {"evidence_ids": ["E01", "E02"]}]},
            {"status": "insufficient_evidence", "context": [], "statements": []},
        ]
        load = verification_load(answers, records, units)
        self.assertEqual(load["cited_tokens_per_statement"], ((10 + 5) + (40 + 5)) / 2)
        self.assertEqual((load["single_leaf_citation_rate"], load["citations"]), (2 / 3, 3))


if __name__ == "__main__":
    unittest.main()
