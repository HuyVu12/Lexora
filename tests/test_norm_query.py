"""Norm-field queries (DK3-q/DK4-q) and enumeration drafts from the gold set. Synthetic data, stand-in model."""

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_retrieval_run import SYNTHETIC, bundle
from legal_ai.common.io import read_jsonl
from legal_ai.research.enumeration import check_sheet, drafts
from legal_ai.retrieval import norm_query
from legal_ai.retrieval.norm_query import actor_matches, clean, coverage, filter_ranked, fold, matches, norm_records

ALIASES_FILE = ROOT / "configs" / "experiments" / "actor-aliases.json"


def claim(claim_id, unit, modality, actor, action="thực hiện việc giả định", **slots):
    sentence = {"start": unit["source_start"], "end": unit["source_end"] - 1}
    return {"claim_id": claim_id, "unit_id": unit["unit_id"], "sentence": sentence, "modality": modality,
            "slots": {"actor": actor, "action": action, **slots}}


class Analyzer:
    model, effort = "stand-in", None

    def structured(self, system, prompt, schema, purpose="structured"):
        assert purpose == "query_slots" and schema == norm_query.SCHEMA
        question = json.loads(prompt)["question"]
        if "lỗi" in question:
            return {"output": {"modality": "bad"}}
        return {"output": {"modality": "obligation", "actor": " người sử dụng lao động ", "required_slots": ["deadlines", "deadlines", "x"],
                           "topic_query": "báo trước"}, "model": "stand-in"}


class NormQueryTests(unittest.TestCase):
    def setUp(self):
        self.aliases = norm_query.load_aliases(ALIASES_FILE)
        self.documents, self.units, self.texts = bundle(None, {"syn-a": SYNTHETIC})
        self.by_id = {u["unit_id"]: u for u in self.units}

    def unit(self, suffix):
        return self.by_id[f"syn-a/chapter-i/{suffix}"]

    def test_actor_matching_folds_accents_and_uses_the_alias_table(self):
        self.assertEqual(fold("Người Sử Dụng  Lao Động"), "nguoi su dung lao dong")
        self.assertTrue(actor_matches("người sử dụng lao động", "NSDLĐ", self.aliases))
        self.assertTrue(actor_matches("người lao động", "Người lao động làm việc theo hợp đồng lao động", self.aliases))
        self.assertFalse(actor_matches("người lao động", "người sử dụng lao động", self.aliases), "whole words of another actor do not count")
        self.assertTrue(actor_matches(None, None, self.aliases))
        self.assertFalse(actor_matches("người lao động", None, self.aliases))
        self.assertTrue(actor_matches("ban quản lý giả định", "Ban quản lý giả định của khu", self.aliases), "actors outside the table: containment")

    def test_claim_filter_checks_modality_required_slots_and_actor(self):
        unit = self.unit("article-1/clause-1")
        obligation = claim("c1", unit, "obligation", "Người sử dụng lao động", deadlines="ít nhất 45 ngày")
        analysis = {"modality": "obligation", "actor": "người sử dụng lao động", "required_slots": ["deadlines"], "topic_query": "báo trước"}
        self.assertTrue(matches(obligation, analysis, self.aliases))
        self.assertFalse(matches(obligation | {"modality": "entitlement"}, analysis, self.aliases))
        self.assertFalse(matches(obligation | {"slots": {**obligation["slots"], "deadlines": None}}, analysis, self.aliases))
        self.assertTrue(matches(obligation | {"modality": "permission"}, analysis | {"modality": "any"}, self.aliases))

    def test_analysis_is_cleaned_resumed_and_failures_are_recorded(self):
        with tempfile.TemporaryDirectory() as folder:
            questions = Path(folder) / "q.json"
            questions.write_text(json.dumps({"questions": [{"question_id": "a", "question": "NSDLĐ phải báo trước những gì?"},
                                                           {"question_id": "b", "question": "câu lỗi"}]}, ensure_ascii=False), encoding="utf-8")
            counts = norm_query.analyze(questions, Analyzer(), Path(folder) / "slots")
            self.assertEqual((counts["analyzed"], counts["failed"]), (1, 1))
            rows, manifest = norm_query.load(Path(folder) / "slots", questions)
            self.assertEqual(rows["a"], {"modality": "obligation", "actor": "người sử dụng lao động", "required_slots": ["deadlines"], "topic_query": "báo trước"})
            self.assertEqual(manifest["query_version"], "norm-query-v1")
            again = norm_query.analyze(questions, Analyzer(), Path(folder) / "slots")
            self.assertEqual(again["already_done"], 1)
        with self.assertRaises(ValueError):
            clean({"modality": "obligation", "topic_query": "  "})

    def test_norm_records_hold_claim_lines_and_article_layout(self):
        claims = [claim("c1", self.unit("article-1/clause-1"), "obligation", "Bên A", action="báo trước cho bên B", deadlines="45 ngày"),
                  claim("c2", self.unit("article-2/clause-2/point-a"), "obligation", "Bên A", action="trả một lần mỗi tháng")]
        records = norm_records("DK3", self.documents, self.units, self.texts, claims)
        self.assertEqual([r["unit_ids"][0].split("/", 2)[2] for r in records], ["article-1/clause-1", "article-2/clause-2/point-a"])
        first = records[0]
        self.assertIn("[Quy phạm 1] nghĩa vụ · Chủ thể: Bên A · Thời hạn: 45 ngày · Hành vi: «báo trước cho bên B»", first["generator_text"])
        self.assertEqual(first["pack_layout"]["header"], "Văn bản giả định syn-a\nChương I > Điều 1")
        self.assertTrue(first["pack_layout"]["body"].startswith("Khoản 1\n[Quy phạm 1]"))
        self.assertEqual(first["text"], self.texts["syn-a"][first["source_start"]:first["source_end"]], "the record still spans its unit")
        analysis = {"modality": "obligation", "actor": None, "required_slots": ["deadlines"], "topic_query": "x"}
        self.assertEqual(filter_ranked([(1, 0.9), (0, 0.5)], records, analysis, self.aliases), [(0, 0.5)])
        from legal_ai.indexing.packing import Packer
        packed = Packer("P1", records, self.units, self.documents).pack(records, 10 ** 6)
        self.assertEqual(len(packed["groups"]), 2)
        self.assertTrue(packed["blocks"][0]["text"].startswith("Khoản 1\n[Quy phạm 1]"))

    def test_coverage_counts_gold_units_with_a_claim(self):
        claims = [claim("c1", self.unit("article-1/clause-1"), "obligation", "Bên A")]
        result = coverage([{"relevant_unit_ids": ["syn-a/chapter-i/article-1/clause-1", "syn-a/chapter-i/article-3"]}], claims)
        self.assertEqual((result["covered"], result["coverage"], result["uncovered"]), (1, 0.5, ["syn-a/chapter-i/article-3"]))


class QueryRunTests(unittest.TestCase):
    def test_query_conditions_rank_by_topic_and_keep_only_passing_units(self):
        from legal_ai.common.io import write_json, write_jsonl
        from legal_ai.evaluation.preflight import check
        from legal_ai.evaluation.retrieval_run import run
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            documents, units, texts = bundle(root / "bundle", {"syn-a": SYNTHETIC})
            by_id = {u["unit_id"]: u for u in units}
            base = "syn-a/chapter-i/"
            claims = [claim("c1", by_id[base + "article-1/clause-1"], "obligation", "Bên A", deadlines="45 ngày"),
                      claim("c2", by_id[base + "article-1/clause-2"], "obligation", "Bên A", deadlines="30 ngày"),
                      claim("c3", by_id[base + "article-3"], "entitlement", "Người làm việc", deadlines="12 tháng")]
            kb = root / "kb"
            write_jsonl(kb / "dk3.jsonl", claims)
            write_jsonl(kb / "dk4.jsonl", claims[:1])
            from legal_ai.common.io import digest
            write_json(kb / "manifest.json", {"units_sha256": digest((root / "bundle" / "units.jsonl").read_bytes())})
            questions = root / "q.json"
            write_json(questions, {"questions": [{"question_id": "e1", "question": "Bên A có những nghĩa vụ báo trước nào?",
                                                  "relevant_unit_ids": [base + "article-1/clause-1", base + "article-1/clause-2"]}]})
            slots = root / "slots"
            write_json(slots / "manifest.json", {"questions_sha256": digest(questions.read_bytes())})
            write_jsonl(slots / "query_slots.jsonl", [{"question_id": "e1", "error": None, "analysis": {
                "modality": "obligation", "actor": "Bên A", "required_slots": ["deadlines"], "topic_query": "báo trước"}}])
            shared = root / "shared.json"
            write_json(shared, {"top_k": 3, "query_slots": slots.as_posix(), "context_packing": "P1", "token_budgets": [500],
                                "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75, "recall_k": [1, 3]}})
            runs = {}
            for name, body in (("DK2", {"representation": "structural_units", "max_tokens": 384}),
                               ("DK3", {"representation": "llm_kb_raw", "kb_run": kb.as_posix(), "record": "norm_lines", "query": {"aliases": ALIASES_FILE.as_posix()}}),
                               ("DK4", {"representation": "llm_kb_validated", "kb_run": kb.as_posix(), "record": "norm_lines", "query": {"aliases": ALIASES_FILE.as_posix()}})):
                path = root / f"{name}.json"
                write_json(path, {"condition": name} | body)
                runs[name] = run(root / "bundle", questions, path, shared, root / name)
            dk3 = read_jsonl(root / "DK3" / "predictions.jsonl")[0]
            self.assertEqual(sorted(r["unit_ids"][0] for r in dk3["ranked"]), [base + "article-1/clause-1", base + "article-1/clause-2"],
                             "the entitlement of another actor is filtered out")
            self.assertEqual((runs["DK3"]["mean_recall_at_tokens"]["500"], runs["DK4"]["mean_recall_at_tokens"]["500"]), (1.0, 0.5))
            manifest = json.loads((root / "DK3" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["query_slots"]["version"], "norm-query-v1")
            self.assertEqual(check([root / "DK2", root / "DK3", root / "DK4"])["status"], "warn", "DK1 is missing, nothing fails")
            bad = root / "bad.json"
            write_json(bad, {"condition": "DK3", "representation": "llm_kb_raw", "kb_run": kb.as_posix(), "record": "unit_with_claims", "query": {"aliases": "x"}})
            with self.assertRaisesRegex(ValueError, "norm_lines"):
                run(root / "bundle", questions, bad, shared, root / "bad")


class EnumerationTests(unittest.TestCase):
    def test_drafts_group_gold_norms_by_scope_and_criterion(self):
        aliases = norm_query.load_aliases(ALIASES_FILE)
        documents, units, _ = bundle(None, {"syn-a": SYNTHETIC})
        base = "syn-a/chapter-i/article-2/"
        gold = [
            {"unit_id": base + "clause-1", "norms": [{"modality": "obligation", "slots": {"actor": "Người sử dụng lao động", "quantities": "85%"}}]},
            {"unit_id": base + "clause-2/point-a", "norms": [{"modality": "obligation", "slots": {"actor": "NSDLĐ", "deadlines": "15 ngày", "quantities": "một lần"}}]},
            {"unit_id": base + "clause-2/point-b", "norms": [{"modality": "entitlement", "slots": {"actor": "người lao động"}}]},
        ]
        rows = drafts(gold, units, documents, aliases)
        kinds = {(r["enumeration_kind"], r["criteria"]["modality"], r["criteria"]["actor"]): r["relevant_unit_ids"] for r in rows}
        self.assertEqual(kinds[("by_actor", "obligation", "người sử dụng lao động")], [base + "clause-1", base + "clause-2/point-a"])
        self.assertEqual(kinds[("quantities", "any", None)], [base + "clause-1", base + "clause-2/point-a"])
        self.assertNotIn(("by_actor", "entitlement", "người lao động"), kinds, "a single unit is not an enumeration")
        self.assertNotIn(("deadlines", "any", None), kinds)
        self.assertTrue(rows[0]["question"].startswith("Theo Điều 2. Tiền lương giả định của Văn bản giả định syn-a"))
        self.assertEqual({r["annotation_status"] for r in rows}, {"draft"})
        with tempfile.TemporaryDirectory() as folder:
            check_sheet(Path(folder) / "sheet.csv", rows, gold, units)
            with open(Path(folder) / "sheet.csv", encoding="utf-8-sig") as handle:
                sheet = list(csv.DictReader(handle))
            self.assertEqual(len(sheet), sum(len(r["relevant_unit_ids"]) for r in rows))
            self.assertEqual({row["keep"] for row in sheet}, {""})


if __name__ == "__main__":
    unittest.main()
