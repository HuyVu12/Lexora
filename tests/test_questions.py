"""Question sets across two machines: pack, independent labels, agreement, adjudication and frozen splits.
Synthetic statute text, not real law; no model is called."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.common.io import write_json
from legal_ai.evaluation.retrieval_run import run
from legal_ai.research.corpus import CorpusStore
from legal_ai.research.questions import QuestionStore, dice, kappa

LAW = ("Điều 1. Thời hạn báo trước\n1. Bên A phải báo trước 30 ngày.\n2. Bên B phải báo trước 45 ngày.\n"
       "Điều 2. Tiền lương giả định\nTiền lương thử nghiệm ít nhất bằng 85% mức lương chính thức.\n")
U1, U2, A2 = "luat/article-1/clause-1", "luat/article-1/clause-2", "luat/article-2"


def machine(folder, name):
    path = Path(folder) / f"{name}.sqlite"
    corpora = CorpusStore(path)
    return corpora, QuestionStore(path, corpora)


class QuestionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.corpora, self.store = machine(self.temp.name, "vu")
        corpus = self.corpora.create("Lao động", "", "vu")
        self.corpora.add_file(corpus["id"], "luat.txt", LAW.encode("utf-8"), "vu")
        self.version = self.corpora.freeze(corpus["id"], "", "vu")
        self.set = self.store.create("Bộ thử", self.version["id"], "Gán theo hướng dẫn", "vu")
        self.q1 = self.store.add_question(self.set["id"], "Bên A phải báo trước bao nhiêu ngày?", "vu")
        self.q2 = self.store.add_question(self.set["id"], "Lương thử nghiệm tối thiểu bao nhiêu?", "vu", origin="model", origin_detail={"call": "c1"})
        self.q3 = self.store.add_question(self.set["id"], "Mức lương thử nghiệm thấp nhất là mấy phần trăm?", "vu", family_id=self.q2["family_id"])
        self.q4 = self.store.add_question(self.set["id"], "Thủ tục ly hôn thế nào?", "vu")

    def label(self, store, who, question, kind, status, units):
        return store.save_label(self.set["id"], question["id"], who, who.title(), {"question_type": kind, "expected_status": status, "relevant_unit_ids": units})

    def test_metrics(self):
        self.assertEqual(kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]), 1.0)
        self.assertAlmostEqual(kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]), 0.0)
        self.assertEqual(kappa(["a"], ["a"]), 1.0)
        self.assertIsNone(kappa([], []))
        self.assertEqual((dice([], []), dice(["x"], ["x", "y"])), (1.0, 2 / 3))

    def test_drafts_are_model_questions_with_proposals_checked_before_anything_is_written(self):
        drafts = [{"text": "Bên B báo trước mấy ngày?", "question_type": "lookup", "expected_status": "answer", "relevant_unit_ids": [U2], "rationale": "Khoản 2"},
                  {"text": "Thời hạn báo trước của bên B là bao lâu?", "question_type": "lookup", "expected_status": "answer", "relevant_unit_ids": [U2], "paraphrase_of": 0},
                  {"text": "Mức đóng bảo hiểm xã hội là bao nhiêu?", "question_type": "out_of_scope", "expected_status": "refuse", "relevant_unit_ids": []}]
        before = len(self.store.workspace(self.set["id"], "vu")["items"])
        for bad, message in (([drafts[0] | {"relevant_unit_ids": ["luat/article-9"]}], "không có trong phiên bản"),
                             ([drafts[2] | {"relevant_unit_ids": [U1]}], "từ chối"),
                             ([drafts[1]], "paraphrase_of"),
                             ([drafts[0], drafts[0]], "trùng")):
            with self.assertRaisesRegex(ValueError, message):
                self.store.import_drafts(self.set["id"], bad, "vu", "claude-opus-5-5")
        self.assertEqual(len(self.store.workspace(self.set["id"], "vu")["items"]), before, "a rejected file writes nothing")

        self.assertEqual(self.store.import_drafts(self.set["id"], drafts, "vu", "claude-opus-5-5"), {"added": 3, "families": 2})
        self.store.set_mode(self.set["id"], "vu", True)
        items = {i["text"]: i for i in self.store.workspace(self.set["id"], "vu")["items"]}
        first, paraphrase = items[drafts[0]["text"]], items[drafts[1]["text"]]
        self.assertEqual((first["origin"], first["origin_detail"]["author"], first["family_id"]), ("model", "claude-opus-5-5", paraphrase["family_id"]))
        self.assertEqual(first["proposal"]["fields"]["relevant_unit_ids"], [U2])
        self.assertIsNone(first.get("label"), "proposals are never labels")

    def test_labels_need_a_mode_valid_units_and_record_proposal_decisions(self):
        with self.assertRaisesRegex(ValueError, "hiện đề xuất"):
            self.label(self.store, "vu", self.q1, "lookup", "answer", [U1])
        self.store.add_proposal(self.set["id"], self.q1["id"], {"question_type": "lookup", "expected_status": "answer", "relevant_unit_ids": [U1, "luat/article-9"]},
                                "Khoản 1 nêu thời hạn", [U1, U2], {"model": "claude-opus-5-5"})
        self.store.set_mode(self.set["id"], "vu", True)
        proposal = self.store.workspace(self.set["id"], "vu")["items"][0]["proposal"]
        self.assertEqual(proposal["fields"]["relevant_unit_ids"], [U1], "unknown unit IDs from the model are dropped")
        saved = self.label(self.store, "vu", self.q1, "lookup", "answer", [U1, U2])
        self.assertEqual(saved["provenance"]["decisions"], {"question_type": "kept", "expected_status": "kept", "relevant_unit_ids": "changed"})
        with self.assertRaisesRegex(ValueError, "không đổi chế độ"):
            self.store.set_mode(self.set["id"], "vu", False)
        with self.assertRaisesRegex(ValueError, "không có trong phiên bản"):
            self.label(self.store, "vu", self.q1, "lookup", "answer", ["luat/article-9"])
        with self.assertRaisesRegex(ValueError, "ít nhất một đơn vị"):
            self.label(self.store, "vu", self.q1, "lookup", "answer", [])
        self.label(self.store, "vu", self.q4, "out_of_scope", "refuse", [])
        self.assertEqual(self.store.workspace(self.set["id"], "vu")["labelled"], 2)

    def test_two_machines_agreement_adjudication_and_frozen_split(self):
        # Machine A (Vũ) labels with proposals shown and sends a pack to machine B (Kha).
        self.store.set_mode(self.set["id"], "vu", True)
        for q, kind, units in ((self.q1, "lookup", [U1]), (self.q2, "lookup", [A2]), (self.q3, "lookup", [A2])):
            self.label(self.store, "vu", q, kind, "answer", units)
        self.label(self.store, "vu", self.q4, "out_of_scope", "refuse", [])
        pack = json.loads(json.dumps(self.store.export_pack(self.set["id"]), ensure_ascii=False))
        self.assertNotIn("labels", pack)
        corpora_b, store_b = machine(self.temp.name, "kha")
        imported = store_b.import_pack(pack, "kha")
        self.assertEqual((imported["questions"], imported["imported"]), (4, True))
        self.assertEqual(corpora_b.version(self.version["id"])["bundle_sha256"], self.version["bundle_sha256"])
        store_b.set_mode(self.set["id"], "kha", False)
        self.assertIsNone(store_b.workspace(self.set["id"], "kha")["items"][0]["proposal"])
        for q, kind, units in ((self.q1, "lookup", [U1]), (self.q2, "synthesis", [A2]), (self.q3, "lookup", [A2, U1])):
            store_b.save_label(self.set["id"], q["id"], "kha", "Kha", {"question_type": kind, "expected_status": "answer", "relevant_unit_ids": units})
        store_b.save_label(self.set["id"], self.q4["id"], "kha", "Kha", {"question_type": "out_of_scope", "expected_status": "refuse", "relevant_unit_ids": []})
        labels = json.loads(json.dumps(store_b.export_labels(self.set["id"], "kha"), ensure_ascii=False))
        self.assertFalse(labels["show_proposals"])
        with self.assertRaisesRegex(ValueError, "chính bạn"):
            self.store.import_labels(dict(labels, annotator="vu", labels_sha256=labels["labels_sha256"]), "vu")
        tampered = json.loads(json.dumps(labels))
        tampered["labels"][0]["fields"]["relevant_unit_ids"] = [U2]
        with self.assertRaisesRegex(ValueError, "mã băm"):
            self.store.import_labels(tampered, "vu")
        self.assertEqual(self.store.import_labels(labels, "vu")["labels"], 4)

        report = self.store.comparison(self.set["id"], "vu", "kha")
        self.assertEqual(report["labelled_by_both"], 4)
        self.assertEqual((report["first"]["proposals_shown"], report["second"]["proposals_shown"]), (True, False))
        self.assertEqual(report["kappa_expected_status"], 1.0)
        self.assertLess(report["kappa_question_type"], 1.0)
        self.assertAlmostEqual(report["mean_unit_dice"], (1 + 1 + 2 / 3 + 1) / 4)
        self.assertEqual([i["agree"] for i in report["items"]], [True, False, False, True])

        with self.assertRaisesRegex(ValueError, "chưa chốt"):
            self.store.freeze(self.set["id"], "vu", "kha", "vu")
        for item in report["items"]:
            final = item["first"] if item["agree"] else {"question_type": "lookup", "expected_status": "answer", "relevant_unit_ids": [A2]}
            self.store.adjudicate(self.set["id"], item["id"], final, "" if item["agree"] else "Thống nhất sau thảo luận", "vu")
        frozen = self.store.freeze(self.set["id"], "vu", "kha", "vu", held_out=0.5)
        self.assertEqual(frozen["bundle_sha256"], self.version["bundle_sha256"])
        questions = self.store.frozen_file(self.set["id"])["questions"]
        by_id = {q["question_id"]: q for q in questions}
        self.assertEqual(by_id[self.q2["id"]]["split"], by_id[self.q3["id"]]["split"], "paraphrases stay in one split")
        self.assertEqual(by_id[self.q2["id"]]["origin"], "model")
        with self.assertRaisesRegex(ValueError, "đã khóa"):
            self.label(self.store, "vu", self.q1, "lookup", "answer", [U1])

        # The frozen file drives a retrieval run on the exported corpus version.
        bundle = Path(self.temp.name) / "bundle"
        self.corpora.export_version(self.version["id"], bundle)
        questions_file = Path(self.temp.name) / "questions.json"
        write_json(questions_file, self.store.frozen_file(self.set["id"]))
        shared = Path(self.temp.name) / "shared.json"
        write_json(shared, {"status": "draft", "top_k": 1, "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75, "recall_k": [1]}})
        condition = Path(self.temp.name) / "dk2.json"
        write_json(condition, {"condition": "DK2", "representation": "structural_units", "max_tokens": 384})
        metrics = run(bundle, questions_file, condition, shared, Path(self.temp.name) / "run")
        self.assertEqual((metrics["scored_questions"], metrics["excluded_without_gold"]), (3, 1))


if __name__ == "__main__":
    unittest.main()
