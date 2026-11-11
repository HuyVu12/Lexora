"""Amendment edges by rule, unit status at a date and validity filtering in the retrieval run. Synthetic texts only."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_retrieval_run import SYNTHETIC, bundle
from legal_ai.common.io import digest, read_jsonl, write_json, write_jsonl
from legal_ai.evaluation.answer_run import cites_stale
from legal_ai.evaluation.retrieval_run import run
from legal_ai.kb.amendments import detect, document_id_of, parse_targets
from legal_ai.kb.validity import Validity

AMENDING = (
    "NGHỊ ĐỊNH GIẢ ĐỊNH\n"
    "Điều 1. Sửa đổi, bổ sung một số điều của Nghị định số 1/2020/NĐ-CP về chủ đề giả định\n"
    "1. Sửa đổi, bổ sung một số khoản của Điều 1 như sau:\n"
    "a) Sửa đổi, bổ sung khoản 2 Điều 1 như sau:\n"
    "\"2. Ít nhất 35 ngày đối với hợp đồng xác định thời hạn.\".\n"
    "b) Bổ sung khoản 3 Điều 1 như sau:\n"
    "\"3. Bổ sung khoản mới\n"
    "a) Sửa đổi, bổ sung khoản 9 Điều 9 như sau: dòng này nằm trong trích dẫn.\".\n"
    "2. Thay thế cụm từ \"khoản 4 Điều 7\" bằng cụm từ \"khoản 5 Điều 7\" tại khoản 1 Điều 2.\n"
    "3. Bãi bỏ điểm a, c khoản 2 Điều 2 và Điều 3.\n"
    "4. Sửa đổi Mẫu số 01 Phụ lục I.\n"
    "Điều 2. Bãi bỏ một số quy định của Thông tư số 9/2019/TT-BLĐTBXH\n"
    "1. Bãi bỏ khoản 1 Điều 4.\n"
    "Điều 3. Hiệu lực thi hành\n"
    "Thay thế người lao động nghỉ thai sản là một quy định nội dung, không phải lệnh sửa đổi.\n"
)


class AmendmentTests(unittest.TestCase):
    def setUp(self):
        documents, self.units, _ = bundle(None, {"1-2020-nd-cp": SYNTHETIC})
        self.edges = detect({"document_id": "2-2021-nd-cp"}, AMENDING, self.units, "2021-07-01")

    def test_targets_and_document_numbers(self):
        self.assertEqual(document_id_of("152/2020/NĐ-CP"), "152-2020-nd-cp")
        self.assertEqual(parse_targets("Bãi bỏ điểm c, d, đ khoản 5 và điểm g khoản 6 Điều 30;"),
                         [("30", "5", "c"), ("30", "5", "d"), ("30", "5", "đ"), ("30", "6", "g")])
        self.assertEqual(parse_targets("Thay thế cụm từ \"khoản 4, 6 và 8 Điều 154\" bằng cụm từ \"x\" tại khoản 2 Điều 8;"), [("8", "2", None)])
        self.assertEqual(parse_targets("Sửa đổi, bổ sung Điều 4 như sau:"), [("4", None, None)])
        self.assertEqual(parse_targets("tại khoản 10 Điều 9 và khoản 4 Điều 23"), [("9", "10", None), ("23", "4", None)])

    def test_edges_are_anchored_resolved_and_never_guessed(self):
        rows = [(e["kind"], e["status"], e["target"] and tuple(e["target"].values()), e["target_unit_id"]) for e in self.edges]
        unit = "1-2020-nd-cp/chapter-i/"
        self.assertIn(("modify", "resolved", ("1", "2", None), unit + "article-1/clause-2"), rows)
        self.assertIn(("add", "resolved_parent", ("1", "3", None), None), rows)
        self.assertIn(("replace_phrase", "resolved", ("2", "1", None), unit + "article-2/clause-1"), rows)
        self.assertIn(("repeal", "resolved", ("3", None, None), unit + "article-3"), rows)
        self.assertIn(("repeal", "resolved", ("2", "2", "a"), unit + "article-2/clause-2/point-a"), rows)
        self.assertIn(("repeal", "unresolved", ("2", "2", "c"), None), rows, "a missing point stays unresolved")
        self.assertIn(("modify", "unresolved", None, None), rows, "an annex form is not a unit")
        external = [e for e in self.edges if e["status"] == "external"]
        self.assertEqual([(e["target_document_id"], e["target"]["article"]) for e in external], [("9-2019-tt-bldtbxh", "4")])
        self.assertFalse(any(e["target"] and e["target"]["article"] == "9" for e in self.edges), "quoted new wording is never an instruction")
        self.assertFalse(any("thai sản" in e["instruction"]["text"] for e in self.edges), "a provision is not an instruction")
        for edge in self.edges:
            quote = edge["instruction"]
            self.assertEqual(AMENDING[quote["start"]:quote["end"]], quote["text"])
            self.assertEqual(edge["effective_from"], "2021-07-01")
        modify = next(e for e in self.edges if e["kind"] == "modify" and e["status"] == "resolved")
        self.assertTrue(AMENDING[modify["new_text"]["start"]:modify["new_text"]["end"]].startswith("\"2. Ít nhất 35 ngày"))
        self.assertEqual(len({e["edge_id"] for e in self.edges}), len(self.edges))


class StatusTests(unittest.TestCase):
    def setUp(self):
        documents, self.units, _ = bundle(None, {"1-2020-nd-cp": SYNTHETIC})
        documents[0] |= {"effective_from": "2020-07-01", "effective_to": "2030-01-01"}
        edges = detect({"document_id": "2-2021-nd-cp"}, AMENDING, self.units, "2021-07-01")
        self.validity = Validity(documents, self.units, edges)
        self.unit = "1-2020-nd-cp/chapter-i/"

    def test_status_follows_dates_and_edges(self):
        status = self.validity.status
        self.assertEqual(status(self.unit + "article-1/clause-2", "2020-01-01"), "not_yet_effective")
        self.assertEqual(status(self.unit + "article-1/clause-2", "2021-01-01"), "in_force")
        self.assertEqual(status(self.unit + "article-1/clause-2", "2021-07-01"), "amended")
        self.assertEqual(status(self.unit + "article-1/clause-1", "2021-07-01"), "in_force")
        self.assertEqual(status(self.unit + "article-1", "2021-07-01"), "amended", "a part of the Article changed")
        self.assertEqual(status(self.unit + "article-3", "2022-01-01"), "repealed")
        self.assertEqual(status(self.unit + "article-2/clause-1", "2022-01-01"), "amended", "a reworded phrase amends the clause")
        self.assertEqual(status(self.unit + "article-1/clause-1", "2030-01-01"), "expired")
        note = self.validity.note(self.unit + "article-1/clause-2", "2022-01-01")
        self.assertIn("đã được sửa đổi", note)
        self.assertIn("2-2021-nd-cp", note)
        self.assertIsNone(self.validity.note(self.unit + "article-1/clause-1", "2022-01-01"))

    def test_stale_citations(self):
        answer = {"statements": [{"unit_ids": [self.unit + "article-1/clause-2"]}]}
        self.assertTrue(cites_stale(answer, [self.unit + "article-1/clause-2"]))
        self.assertTrue(cites_stale(answer, [self.unit + "article-1"]), "citing a part of a stale Article")
        self.assertFalse(cites_stale(answer, [self.unit + "article-1/clause-1"]))


class RetrievalValidityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        documents, units, _ = bundle(self.root / "bundle", {"1-2020-nd-cp": SYNTHETIC})
        documents[0] |= {"effective_from": "2020-07-01", "effective_to": None}
        write_jsonl(self.root / "bundle" / "documents.jsonl", documents)
        edges = detect({"document_id": "2-2021-nd-cp"}, AMENDING, units, "2021-07-01")
        write_jsonl(self.root / "edges" / "edges.jsonl", edges)
        write_json(self.root / "edges" / "manifest.json", {"units_sha256": digest((self.root / "bundle" / "units.jsonl").read_bytes())})
        unit = "1-2020-nd-cp/chapter-i/"
        self.questions = self.root / "q.json"
        write_json(self.questions, {"questions": [
            {"question_id": "old", "question": "Nghỉ hằng năm bao nhiêu ngày?", "as_of": "2021-01-01", "relevant_unit_ids": [unit + "article-3"]},
            {"question_id": "new", "question": "Nghỉ hằng năm bao nhiêu ngày?", "as_of": "2022-01-01", "relevant_unit_ids": [unit + "article-1"],
             "stale_unit_ids": [unit + "article-3"]},
            {"question_id": "amended", "question": "Báo trước bao nhiêu ngày với hợp đồng xác định thời hạn?", "relevant_unit_ids": [unit + "article-1/clause-2"]}]})
        self.shared = self.root / "shared.json"
        write_json(self.shared, {"top_k": 3, "validity_as_of": "2022-01-01", "token_budgets": [1000],
                                 "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75, "recall_k": [1, 3]}})

    def condition(self, name, body):
        path = self.root / f"{name}.json"
        write_json(path, body)
        return path

    def test_unit_level_drops_repealed_units_at_the_question_date_and_notes_amended_ones(self):
        dk2 = self.condition("dk2", {"condition": "DK2", "representation": "structural_units", "max_tokens": 384,
                                     "validity": {"level": "unit", "amendments": (self.root / "edges").as_posix()}})
        metrics = run(self.root / "bundle", self.questions, dk2, self.shared, self.root / "run")
        rows = {r["question_id"]: r for r in read_jsonl(self.root / "run" / "predictions.jsonl")}
        article3 = lambda row: [r for r in row["ranked"] if r["unit_ids"][0].endswith("article-3")]
        self.assertTrue(article3(rows["old"]), "before the repeal the Article is retrieved")
        self.assertFalse(article3(rows["new"]), "after the repeal it is dropped")
        self.assertEqual(rows["new"]["validity"]["as_of"], "2022-01-01")
        self.assertEqual(rows["amended"]["validity"]["as_of"], "2022-01-01", "questions without a date use the shared date")
        noted = [r for r in rows["amended"]["ranked"] if r["unit_ids"][0].endswith("article-1/clause-2")]
        self.assertIn("đã được sửa đổi", noted[0]["status_note"])
        self.assertEqual((metrics["questions_with_stale_units"], metrics["stale_context_rate_at_tokens"]["1000"]), (1, 0.0))
        manifest = json.loads((self.root / "run" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual((manifest["validity"]["level"], manifest["validity"]["version"]), ("unit", "unit-status-v1"))

    def test_without_validity_the_repealed_unit_stays_and_is_counted_as_stale(self):
        dk2 = self.condition("plain", {"condition": "DK2", "representation": "structural_units", "max_tokens": 384})
        metrics = run(self.root / "bundle", self.questions, dk2, self.shared, self.root / "plain-run")
        self.assertEqual(metrics["stale_context_rate_at_tokens"]["1000"], 1.0)

    def test_document_level_is_the_only_level_for_chunks_and_checks_its_inputs(self):
        bad = self.condition("bad", {"condition": "DK1", "representation": "fixed_chunks", "chunk_tokens": 30, "overlap_tokens": 5,
                                     "validity": {"level": "unit"}})
        with self.assertRaisesRegex(ValueError, "DK1-hl"):
            run(self.root / "bundle", self.questions, bad, self.shared, self.root / "bad")
        hl = self.condition("hl", {"condition": "DK1", "representation": "fixed_chunks", "chunk_tokens": 30, "overlap_tokens": 5,
                                   "validity": {"level": "document"}})
        write_json(self.questions, {"questions": [{"question_id": "q", "question": "Nghỉ hằng năm", "as_of": "2019-01-01", "relevant_unit_ids": []}]})
        run(self.root / "bundle", self.questions, hl, self.shared, self.root / "hl")
        row = read_jsonl(self.root / "hl" / "predictions.jsonl")[0]
        self.assertEqual((row["ranked"], row["validity"]["dropped"] > 0), ([], True), "nothing applies before the document took effect")


class AmendingUnitTests(unittest.TestCase):
    """Scope v3: the amending document is in the corpus, so its instruction units carry the wording in force."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        from legal_ai.kb.amendments import link_amending_units
        documents, units, texts = bundle(self.root / "bundle", {"1-2020-nd-cp": SYNTHETIC, "2-2021-nd-cp": AMENDING})
        dates = {"1-2020-nd-cp": "2020-07-01", "2-2021-nd-cp": "2021-07-01"}
        for document in documents:
            document |= {"effective_from": dates[document["document_id"]], "effective_to": None}
        write_jsonl(self.root / "bundle" / "documents.jsonl", documents)
        edges = link_amending_units(detect({"document_id": "2-2021-nd-cp"}, texts["2-2021-nd-cp"], units, "2021-07-01"), units, texts["2-2021-nd-cp"])
        self.edges, self.units = edges, units
        write_jsonl(self.root / "edges" / "edges.jsonl", edges)
        write_json(self.root / "edges" / "manifest.json", {"units_sha256": digest((self.root / "bundle" / "units.jsonl").read_bytes())})
        self.old = "1-2020-nd-cp/chapter-i/article-1/clause-2"

    def test_amending_articles_are_excerpted_only_on_request(self):
        from legal_ai.ingestion.excerpt import excerpt, outline
        article = next(a for a in outline(AMENDING) if a["id"].endswith("article-1"))
        self.assertEqual((article["blocked"], article["reason"]), (True, "quoted_text"))
        with self.assertRaises(ValueError):
            excerpt(AMENDING, [article["id"]], limit=None)
        self.assertIn("Ít nhất 35 ngày", excerpt(AMENDING, [article["id"]], limit=None, include_amending=True))

    def test_edges_link_the_amending_unit_exactly(self):
        modify = next(e for e in self.edges if e["target_unit_id"] == self.old)
        unit = next(u for u in self.units if u["unit_id"] == modify["amending_unit_id"])
        self.assertIn("Ít nhất 35 ngày", unit["text"])
        self.assertTrue(unit["unit_id"].startswith("2-2021-nd-cp/"))

    def run_at(self, as_of, name):
        questions = self.root / f"{name}.json"
        write_json(questions, {"questions": [{"question_id": "q", "question": "Báo trước bao nhiêu ngày đối với hợp đồng xác định thời hạn?",
                                              "as_of": as_of, "relevant_unit_ids": [self.old], "stale_unit_ids": [self.old]}]})
        shared = self.root / "shared.json"
        write_json(shared, {"top_k": 3, "validity_as_of": "2022-01-01", "token_budgets": [2000],
                            "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75, "recall_k": [1, 3]}})
        condition = self.root / "dk2.json"
        write_json(condition, {"condition": "DK2", "representation": "structural_units", "max_tokens": 384,
                               "validity": {"level": "unit", "amendments": (self.root / "edges").as_posix()}})
        metrics = run(self.root / "bundle", questions, condition, shared, self.root / name)
        return read_jsonl(self.root / name / "predictions.jsonl")[0], metrics

    def test_after_the_amendment_the_new_wording_replaces_the_old_unit(self):
        row, metrics = self.run_at("2022-01-01", "after")
        units = [r["unit_ids"][0] for r in row["ranked"]]
        self.assertNotIn(self.old, units, "the outdated wording is not retrieved")
        new = next(r for r in row["ranked"] if r["unit_ids"][0].startswith("2-2021-nd-cp/") and "status_note" in r)
        self.assertIn("Lời văn sửa đổi", new["status_note"])
        self.assertIn("khoản 2 Điều 1", new["status_note"])
        self.assertEqual(metrics["stale_context_rate_at_tokens"]["2000"], 0.0)

    def test_before_the_amendment_the_old_unit_stays_and_the_new_one_is_not_yet_in_force(self):
        row, _ = self.run_at("2021-01-01", "before")
        units = [r["unit_ids"][0] for r in row["ranked"]]
        self.assertIn(self.old, units)
        self.assertFalse(any(u.startswith("2-2021-nd-cp/") for u in units))


if __name__ == "__main__":
    unittest.main()
