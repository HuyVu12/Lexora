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
from legal_ai.indexing.packing import Packer
from legal_ai.indexing.records import structural_records
from legal_ai.kb.amendments import detect, document_id_of, edge_scope, parse_targets, phrases
from legal_ai.kb.validity import RecordFilter, Validity

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
        self.v1 = Validity(documents, self.units, edges, version="unit-status-v1")
        self.unit = "1-2020-nd-cp/chapter-i/"

    def test_status_follows_dates_and_edges(self):
        status = self.validity.status
        self.assertEqual(status(self.unit + "article-1/clause-2", "2020-01-01"), "not_yet_effective")
        self.assertEqual(status(self.unit + "article-1/clause-2", "2021-01-01"), "in_force")
        self.assertEqual(status(self.unit + "article-1/clause-2", "2021-07-01"), "amended")
        self.assertEqual(status(self.unit + "article-1/clause-1", "2021-07-01"), "in_force")
        self.assertEqual(status(self.unit + "article-1", "2021-07-01"), "in_force", "v2: a change below a unit leaves its own text")
        self.assertEqual(self.v1.status(self.unit + "article-1", "2021-07-01"), "amended", "v1: a part of the Article changed")
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
        self.assertEqual((manifest["validity"]["level"], manifest["validity"]["version"]), ("unit", "unit-status-v2"))
        self.assertEqual((rows["new"]["validity"]["as_of_source"], rows["amended"]["validity"]["as_of_source"]), ("question", "default"))

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


AMENDING_V2 = (
    "NGHỊ ĐỊNH GIẢ ĐỊNH HAI\n"
    "Điều 1. Sửa đổi, bổ sung một số điều của Nghị định số 1/2020/NĐ-CP về chủ đề giả định\n"
    "1. Sửa đổi, bổ sung tên khoản 2 Điều 2 như sau:\n"
    "\"2. Tiền lương được trả qua tài khoản ngân hàng:\".\n"
    "2. Thay thế cụm từ \"15 ngày\" bằng cụm từ \"10 ngày\" tại khoản 2 Điều 2.\n"
    "Điều 2. Hiệu lực thi hành\n"
    "1. Nghị định này có hiệu lực thi hành từ ngày 01 tháng 7 năm 2022.\n"
    "2. Điều 3 của Nghị định số 1/2020/NĐ-CP hết hiệu lực thi hành kể từ ngày Nghị định này có hiệu lực.\n"
    "3. Nội dung về thời hạn báo trước quy định tại Nghị định số 1/2020/NĐ-CP hết hiệu lực thi hành kể từ ngày Nghị định này có hiệu lực.\n"
    "4. Kể từ ngày Nghị định này có hiệu lực, các văn bản sau đây hết hiệu lực thi hành:\n"
    "a) Thông tư số 9/2019/TT-BLĐTBXH ngày 01 tháng 01 năm 2019 về chủ đề giả định;\n"
    "b) Nghị định số 1/2020/NĐ-CP về chủ đề giả định.\n"
)


class RulesV2Tests(unittest.TestCase):
    """amendment-rules-v2 and unit-status-v2: heading-only changes, phrases per unit, expiry statements, status per unit."""

    def setUp(self):
        from legal_ai.kb.amendments import link_amending_units
        documents, self.units, texts = bundle(None, {"1-2020-nd-cp": SYNTHETIC, "3-2022-nd-cp": AMENDING_V2})
        dates = {"1-2020-nd-cp": "2020-07-01", "3-2022-nd-cp": "2022-07-01"}
        for document in documents:
            document |= {"effective_from": dates[document["document_id"]], "effective_to": None}
        self.documents, self.texts = documents, texts
        self.edges = link_amending_units(detect({"document_id": "3-2022-nd-cp"}, texts["3-2022-nd-cp"], self.units, "2022-07-01"),
                                         self.units, texts["3-2022-nd-cp"])
        self.validity = Validity(documents, self.units, self.edges)
        self.v1 = Validity(documents, self.units, self.edges, version="unit-status-v1")
        self.unit = "1-2020-nd-cp/chapter-i/"

    def test_edges_carry_scope_phrases_and_expiry_statements(self):
        rows = {(e["kind"], e["status"], e["target_unit_id"] or e["target_document_id"]): e for e in self.edges}
        heading = rows[("modify", "resolved", self.unit + "article-2/clause-2")]
        self.assertEqual(heading["scope"], "own_text")
        phrase = rows[("replace_phrase", "resolved", self.unit + "article-2/clause-2")]
        self.assertEqual((phrase["scope"], phrase["phrases"]), ("phrase", [["15 ngày", "10 ngày"]]))
        self.assertEqual(rows[("expire", "resolved", self.unit + "article-3")]["scope"], "unit")
        subject = rows[("expire_subject", "unresolved", "1-2020-nd-cp")]
        self.assertEqual(subject["reason"], "subject_scope_needs_legal_judgment", "a subject-matter scope is never mapped to units")
        self.assertIn(("expire_document", "external", "9-2019-tt-bldtbxh"), rows, "an announced list gives one edge per item")
        self.assertIn(("expire_document", "document", "1-2020-nd-cp"), rows)
        self.assertEqual(phrases('Thay thế cụm từ "A" tại khoản 1 bằng cụm từ "B"; cụm từ "C" thành cụm từ "D" tại khoản 2'), [["A", "B"], ["C", "D"]])
        v1_shaped = {k: v for k, v in heading.items() if k != "scope"}
        self.assertEqual(edge_scope(v1_shaped), "own_text", "v1 edges get their scope from the instruction")

    def test_status_is_per_unit_in_v2(self):
        at = "2022-07-01"
        status = self.validity.status
        self.assertEqual(status(self.unit + "article-2/clause-2", at), "amended", "its lead sentence was rewritten")
        self.assertEqual(status(self.unit + "article-2/clause-2/point-b", at), "in_force", "a rewritten lead leaves the points as they were")
        self.assertEqual(status(self.unit + "article-2/clause-2/point-a", at), "amended", "its own text holds the replaced phrase")
        self.assertEqual(status(self.unit + "article-2", at), "in_force", "a change below a unit does not change the unit")
        self.assertEqual(status(self.unit + "article-3", at), "expired", "an expire edge naming the Article")
        self.assertEqual(status(self.unit + "article-1/clause-1", at), "in_force", "expiry by subject matter is never applied")
        self.assertEqual(status(self.unit + "article-3", "2022-06-30"), "in_force")
        self.assertEqual((self.v1.status(self.unit + "article-2/clause-2/point-b", at), self.v1.status(self.unit + "article-2", at)),
                         ("amended", "amended"), "v1 semantics stay available")
        self.assertEqual(self.v1.status(self.unit + "article-3", at), "in_force", "v1 knew no expire edges")
        self.assertEqual(self.validity.amended_ancestors(self.unit + "article-2/clause-2/point-b", at), [self.unit + "article-2/clause-2"])

    def test_record_filter_annotates_units_under_an_amended_lead_and_drops_expired_ones(self):
        records = structural_records(self.documents, self.units, self.texts)
        rfilter = RecordFilter(self.validity, "unit", records)
        by_unit = {r["unit_ids"][0]: r for r in records}
        shown = rfilter.admit_record(by_unit[self.unit + "article-2/clause-2/point-b"], "2022-07-01")
        self.assertEqual(shown[0]["record_id"], by_unit[self.unit + "article-2/clause-2/point-b"]["record_id"])
        self.assertIn("phần dẫn của khoản 2 Điều 2", shown[0]["status_note"])
        self.assertTrue(any(r["document_id"] == "3-2022-nd-cp" for r in shown[1:]), "the new lead follows")
        self.assertEqual(rfilter.admit_record(by_unit[self.unit + "article-3"], "2022-07-01"), [])
        self.assertEqual(rfilter.admit_record(by_unit[self.unit + "article-1/clause-1"], "2022-07-01"), [by_unit[self.unit + "article-1/clause-1"]])


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
        self.edges, self.units, self.documents, self.texts = edges, units, documents, texts
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


    def test_p2_siblings_never_bring_back_a_unit_the_filter_removed(self):
        from legal_ai.evaluation.answer_run import pack_with_groups
        from legal_ai.evaluation.retrieval_run import within_budget
        records = structural_records(self.documents, self.units, self.texts)
        by_unit = {r["unit_ids"][0]: r for r in records}
        packer = Packer("P2", records, self.units, self.documents)
        rfilter = RecordFilter(Validity(self.documents, self.units, self.edges), "unit", records)
        admit = lambda record: rfilter.admit_record(record, "2022-01-01")
        unit = "1-2020-nd-cp/chapter-i/"
        units_of = lambda packed: [b["record"]["unit_ids"][0] for b in packed["blocks"]]
        wages = [by_unit[unit + "article-2/clause-2/point-b"]]
        self.assertIn(unit + "article-2/clause-2/point-a", units_of(packer.pack(wages, 10 ** 6)), "without validity the sibling is added")
        self.assertNotIn(unit + "article-2/clause-2/point-a", units_of(packer.pack(wages, 10 ** 6, admit=admit)), "a repealed sibling is dropped")
        notice = [by_unit[unit + "article-1/clause-1"]]
        packed = packer.pack(notice, 10 ** 6, admit=admit)
        self.assertNotIn(self.old, units_of(packed), "a sibling replaced by its new wording is not shown")
        new = [b for b in packed["blocks"] if b["record"]["document_id"] == "2-2021-nd-cp"]
        self.assertTrue(new and "Lời văn sửa đổi" in new[0]["text"], "its amending unit takes its place, with a note")
        bound = packer.bind(admit)
        items = [{"record_id": r["record_id"]} for r in notice]
        blocks, _ = pack_with_groups(items, {r["record_id"]: r for r in records}, None, 10 ** 6, bound)
        self.assertEqual([b["unit_ids"][0] for b in blocks], [r["unit_ids"][0] for r in within_budget(notice, 10 ** 6, bound)],
                         "the answer run packs exactly what the retrieval run scored")
        noted, _ = pack_with_groups([{"record_id": notice[0]["record_id"], "status_note": "[ghi chú thử]"}], {r["record_id"]: r for r in records},
                                    None, 10 ** 6, Packer("P0"))
        self.assertIn("[ghi chú thử]", noted[0]["text"], "a ranked item's status note reaches the generator")

    def test_retrieval_run_with_p2_scores_no_stale_sibling_and_reports_wrong_versions(self):
        questions = self.root / "q2.json"
        unit = "1-2020-nd-cp/chapter-i/"
        new_wording = next(e["amending_unit_id"] for e in self.edges if e["target_unit_id"] == self.old)
        write_json(questions, {"questions": [
            {"question_id": "wage", "question": "Tiền lương trả theo tuần khi làm việc theo giờ?", "as_of": "2022-01-01",
             "relevant_unit_ids": [unit + "article-2/clause-2/point-b"], "stale_unit_ids": [unit + "article-2/clause-2/point-a"]},
            {"question_id": "past", "question": "Báo trước bao nhiêu ngày đối với hợp đồng xác định thời hạn?", "as_of": "2021-01-01",
             "relevant_unit_ids": [self.old], "not_yet_effective_unit_ids": [new_wording]}]})
        shared = self.root / "shared-p2.json"
        write_json(shared, {"top_k": 3, "validity_as_of": "2022-01-01", "token_budgets": [2000], "context_packing": "P2",
                            "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75, "recall_k": [1, 3]}})
        with_validity = self.root / "dk2-hl.json"
        write_json(with_validity, {"condition": "DK2", "representation": "structural_units", "max_tokens": 384,
                                   "validity": {"level": "unit", "amendments": (self.root / "edges").as_posix()}})
        plain = self.root / "dk2.json"
        write_json(plain, {"condition": "DK2", "representation": "structural_units", "max_tokens": 384})
        filtered = run(self.root / "bundle", questions, with_validity, shared, self.root / "p2-hl")
        unfiltered = run(self.root / "bundle", questions, plain, shared, self.root / "p2")
        self.assertEqual(filtered["stale_context_rate_at_tokens"]["2000"], 0.0, "P2 siblings obey the validity filter")
        self.assertEqual(unfiltered["stale_context_rate_at_tokens"]["2000"], 1.0)
        self.assertEqual((filtered["questions_with_wrong_version_units"], unfiltered["questions_with_wrong_version_units"]), (2, 2))
        self.assertEqual(filtered["wrong_version_context_rate_at_tokens"]["2000"], 0.0, "a unit not yet in force is not shown")

    def test_preflight_fails_when_validity_conditions_used_different_default_dates(self):
        from legal_ai.evaluation.preflight import check
        questions = self.root / "q3.json"
        write_json(questions, {"questions": [{"question_id": "q", "question": "Nghỉ hằng năm", "relevant_unit_ids": ["1-2020-nd-cp/chapter-i/article-3"]}]})
        runs = {}
        for name, day, body in (("dk1-hl", "2022-01-01", {"condition": "DK1", "variant": "DK1-hl", "representation": "fixed_chunks", "chunk_tokens": 30,
                                                          "overlap_tokens": 5, "validity": {"level": "document"}}),
                                ("dk2-a", "2022-01-01", {"condition": "DK2", "representation": "structural_units", "max_tokens": 384,
                                                         "validity": {"level": "unit", "amendments": (self.root / "edges").as_posix()}}),
                                ("dk2-b", "2023-01-01", {"condition": "DK2", "representation": "structural_units", "max_tokens": 384,
                                                         "validity": {"level": "unit", "amendments": (self.root / "edges").as_posix()}})):
            shared, condition = self.root / f"shared-{name}.json", self.root / f"{name}.json"
            write_json(shared, {"top_k": 3, "validity_as_of": day, "token_budgets": [1000],
                                "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75, "recall_k": [1, 3]}})
            write_json(condition, body)
            run(self.root / "bundle", questions, condition, shared, self.root / f"run-{name}")
            runs[name] = self.root / f"run-{name}"
        status = lambda dirs: next(c["status"] for c in check(dirs)["checks"] if c["check"] == "validity conditions use one default date")
        self.assertEqual(status([runs["dk1-hl"], runs["dk2-a"]]), "pass")
        self.assertEqual(status([runs["dk1-hl"], runs["dk2-b"]]), "fail")


if __name__ == "__main__":
    unittest.main()
