"""Extraction gold sets: two machines, exact-quote labels, exchange, comparison and the adjudicated file. Synthetic text."""

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.evaluation import extraction_gold
from legal_ai.research.corpus import CorpusStore
from legal_ai.research.gold import GoldStore

LAW = ("Điều 1. Thử việc giả định\n1. Bên A phải thông báo kết quả thử việc cho bên B.\n2. Bên B có quyền chấm dứt thử việc.\n"
       "Điều 2. Tiền lương giả định\nTiền lương thử việc do hai bên thỏa thuận.\n")
OBLIGATION = {"modality": "obligation", "modality_cue": "phải", "slots": {"actor": "Bên A", "action": "thông báo kết quả thử việc", "recipient": "bên B"}}


class GoldTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.corpora = CorpusStore(root / "vu.sqlite")
        corpus = self.corpora.create("Thử", "Corpus thử", "vu")
        self.corpora.add_file(corpus["id"], "luat.txt", LAW.encode("utf-8"), "vu")
        self.version = self.corpora.freeze(corpus["id"], "v1", "vu")["id"]
        self.vu = GoldStore(root / "vu.sqlite", self.corpora)
        self.kha_corpora = CorpusStore(root / "kha.sqlite")
        self.kha = GoldStore(root / "kha.sqlite", self.kha_corpora)

    def test_two_annotators_label_exchange_compare_and_adjudicate(self):
        made = self.vu.create("Gold thử", self.version, "vu", articles=["luat/article-1"])
        self.assertEqual((made["articles"], made["sentences"]), (1, 2))
        view = self.vu.workspace(made["id"], "vu")
        first, second = view["items"]
        self.assertEqual((first["path"], first["norms"]), ("Điều 1 > Khoản 1", None))

        with self.assertRaisesRegex(ValueError, "ô “Hành vi” phải là cụm chép nguyên văn"):
            self.vu.save(made["id"], first["key"], "vu", "Vũ", [{"modality": "obligation", "slots": {"action": "báo ngay"}}])
        self.vu.save(made["id"], first["key"], "vu", "Vũ", [OBLIGATION])
        self.vu.save(made["id"], second["key"], "vu", "Vũ", [])
        self.assertEqual(self.vu.workspace(made["id"], "vu")["items"][1]["norms"], [], "[] records a sentence without a norm")

        imported = self.kha.import_pack(self.vu.export_pack(made["id"]), "kha")
        self.assertTrue(imported["imported"])
        self.kha.save(made["id"], first["key"], "kha", "Kha", [OBLIGATION | {"slots": {"actor": "Bên A", "action": "thông báo kết quả thử việc"}}])
        self.kha.save(made["id"], second["key"], "kha", "Kha", [])
        with self.assertRaisesRegex(ValueError, "chính bạn"):
            self.vu.import_labels(self.vu.export_labels(made["id"], "vu"), "vu")
        self.assertEqual(self.vu.import_labels(self.kha.export_labels(made["id"], "kha"), "vu")["labels"], 2)

        report = self.vu.comparison(made["id"], "vu", "kha")
        self.assertEqual(report["labelled_by_both"], 2)
        self.assertEqual(report["agreement"]["kappa_has_norm"], 1.0)
        self.assertEqual([i["agree"] for i in report["items"]], [False, True])

        with self.assertRaisesRegex(ValueError, "chưa chốt"):
            self.vu.gold_file(made["id"])
        self.vu.adjudicate(made["id"], first["key"], [OBLIGATION], "vu")
        self.vu.adjudicate(made["id"], second["key"], [], "vu")
        rows = self.vu.gold_file(made["id"])
        units = self.corpora.bundle(self.version)[1]
        self.assertEqual(extraction_gold.check(rows, units), [])
        self.assertEqual(rows[0]["norms"], [OBLIGATION])

    def test_sampled_sets_and_tampered_files_are_refused(self):
        sampled = self.vu.create("Mẫu", self.version, "vu", sample=1)
        self.assertEqual(sampled["articles"], 1)
        pack = self.vu.export_pack(sampled["id"])
        pack["rows"][0]["text"] = "Đã sửa"
        with self.assertRaisesRegex(ValueError, "mã băm"):
            self.kha.import_pack(pack, "kha")
        with self.assertRaisesRegex(ValueError, "Chọn các Điều"):
            self.vu.create("Trống", self.version, "vu")


if __name__ == "__main__":
    unittest.main()
