"""Rejection audit labelled in the app: blinded items, two annotators, kappa, adjudication, score and CSV."""

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.research.audit import AuditStore

ROWS = [{"item_id": f"R{n}", "context": "Điều 1", "unit_text": f"Câu {n}.", "sentence": f"Câu {n}", "norm": "Chủ thể: A", "label": ""} for n in range(4)]
KEY = {"R0": {"model": "m1", "decision": "rejected", "automatic": "context"}, "R1": {"model": "m1", "decision": "rejected", "automatic": "not_found"},
       "R2": {"model": "m1", "decision": "accepted", "automatic": None}, "R3": {"model": "m2", "decision": "rejected", "automatic": "context"}}


class AuditStoreTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.store = AuditStore(Path(temp.name) / "w.sqlite")
        self.set = self.store.create("Bảng thử", ROWS, KEY, "vu")

    def test_workspace_hides_the_key_and_labels_are_per_account(self):
        workspace = self.store.workspace(self.set["id"], "vu")
        text = repr(workspace)
        self.assertNotIn("m1", text)
        self.assertNotIn("rejected", text)
        self.store.save_label(self.set["id"], "R0", "vu", "Vũ", "dung_ngu_canh")
        self.assertEqual(self.store.workspace(self.set["id"], "vu")["rows"][0]["mine"]["label"], "dung_ngu_canh")
        self.assertIsNone(self.store.workspace(self.set["id"], "kha")["rows"][0]["mine"])
        with self.assertRaisesRegex(ValueError, "Nhãn"):
            self.store.save_label(self.set["id"], "R0", "vu", "Vũ", "đúng")
        with self.assertRaisesRegex(ValueError, "Không tìm thấy dòng"):
            self.store.save_label(self.set["id"], "R9", "vu", "Vũ", "sai")
        with self.assertRaisesRegex(ValueError, "không khớp"):
            self.store.create("Lệch", ROWS + [{"item_id": "R9"}], KEY, "vu")

    def test_compare_adjudicate_score_and_sheet(self):
        for item, (a, b) in zip(("R0", "R1", "R2", "R3"), (("dung_ngu_canh", "dung_ngu_canh"), ("sai", "sai"), ("dung", "dung"), ("sai", "dung_ngu_canh"))):
            self.store.save_label(self.set["id"], item, "vu", "Vũ", a)
            self.store.save_label(self.set["id"], item, "kha", "Kha", b)
        compared = self.store.comparison(self.set["id"], "vu", "kha")
        self.assertEqual([i["agree"] for i in compared["items"]], [True, True, True, False])
        self.assertEqual(compared["agreement"]["labels"]["n"], 4)
        self.assertNotIn("m1", repr(compared))
        self.assertEqual(self.store.accept_agreed(self.set["id"], "vu", "kha", "vu"), {"accepted": 3})
        self.store.adjudicate(self.set["id"], "R3", "dung_ngu_canh", "mượn câu dẫn", "kha")
        score = self.store.score(self.set["id"])
        self.assertEqual(score["by_model"]["m1"]["rejected"]["wrong_rate"], {"value": 0.5, "n": 2})
        self.assertEqual(score["by_model"]["m2"]["rejected"]["labels"], {"dung_ngu_canh": 1})
        self.assertEqual(self.store.score(self.set["id"], "kha")["by_model"]["m1"]["accepted"]["wrong_rate"]["value"], 0)
        sheet = self.store.sheet_csv(self.set["id"], "final")
        self.assertTrue(sheet.startswith("﻿item_id,context"))
        self.assertIn("R3,Điều 1,Câu 3.,Câu 3,Chủ thể: A,dung_ngu_canh,mượn câu dẫn", sheet)


if __name__ == "__main__":
    unittest.main()
