"""Extraction gold sets: two machines, exact-quote labels, exchange, comparison and the adjudicated file. Synthetic text."""

from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.evaluation import extraction_gold
from legal_ai.research.corpus import CorpusStore
from legal_ai.research.gold import GoldStore, provenance

LAW = ("Điều 1. Thử việc giả định\n1. Bên A phải thông báo kết quả thử việc cho bên B.\n2. Bên B có quyền chấm dứt thử việc.\n"
       "Điều 2. Tiền lương giả định\nTiền lương thử việc do hai bên thỏa thuận.\n")
OBLIGATION = {"modality": "obligation", "modality_cue": "phải", "slots": {"actor": "Bên A", "action": "thông báo kết quả thử việc", "recipient": "bên B"}}
RIGHT = {"modality": "entitlement", "modality_cue": "có quyền", "slots": {"actor": "Bên B", "action": "chấm dứt thử việc"}}
# Five documents with 31/6/1/1/1 articles, the shape of the shared gold v1 set.
SPREAD = ([f"luat/chapter-i/article-{n}" for n in range(1, 32)] + [f"nghi-dinh/article-{n}" for n in range(1, 7)]
          + ["thong-tu/article-1", "nghi-dinh-phat/article-1", "nghi-dinh-moi/article-1"])


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


    # Agreement sample: partial double annotation ------------------------------------------------
    def test_agreement_sample_is_a_seeded_proportional_function_of_the_articles(self):
        sample = extraction_gold.agreement_sample(SPREAD)
        self.assertEqual(len(sample), 12, "round(0.3 x 40)")
        self.assertEqual(sample, extraction_gold.agreement_sample(list(reversed(SPREAD)) + SPREAD[:3]), "order and duplicates do not matter")
        self.assertEqual(sample, extraction_gold.agreement_sample(SPREAD, 0.3, "lexora-gold-agreement-v1"), "a float share is read as its decimal")
        seats = extraction_gold.sample_allocation(SPREAD)
        self.assertEqual(sum(seats.values()), 12)
        self.assertEqual(seats["nghi-dinh"], 2, "quota 1.8")
        self.assertIn(seats["luat"], (9, 10), "quota 9.3")
        self.assertLessEqual(seats["thong-tu"] + seats["nghi-dinh-phat"] + seats["nghi-dinh-moi"], 1, "one-article documents are not floored up")
        for document, n in seats.items():
            self.assertEqual(sum(a.startswith(document + "/") for a in sample), n)
        allocations = {tuple(sorted(extraction_gold.sample_allocation(SPREAD, "0.3", f"seed-{i}").items())) for i in range(40)}
        self.assertGreater(len(allocations), 1, "the seed breaks the tie between equal remainders")
        self.assertEqual(extraction_gold.agreement_sample(SPREAD, "1"), sorted(SPREAD))
        self.assertEqual(len(extraction_gold.agreement_sample(SPREAD[:2], "0.01")), 1, "at least one article")
        for bad in ("0", "1.5", "abc"):
            with self.assertRaises(ValueError):
                extraction_gold.agreement_sample(SPREAD, bad)

    def _sampled_set(self, store=None):
        """Both articles (three sentences); the 50% sample is Điều 1 (two sentences) under the chosen seed."""
        store = store or self.vu
        articles = ["luat/article-1", "luat/article-2"]
        seed = next(f"s{i}" for i in range(100) if extraction_gold.agreement_sample(articles, "0.5", f"s{i}") == ["luat/article-1"])
        made = store.create("Gold mẫu", self.version, "phapche", articles=articles)
        return made, seed, [i["key"] for i in store.workspace(made["id"], "kha")["items"]]

    def test_sample_declared_once_before_a_second_annotator_and_bulk_finalised_with_provenance(self):
        made, seed, (first, second, third) = self._sampled_set()
        set_id = made["id"]
        self.vu.save(set_id, first, "kha", "Kha", [OBLIGATION])
        self.vu.save(set_id, second, "kha", "Kha", [RIGHT])
        self.vu.save(set_id, third, "kha", "Kha", [])
        self.assertTrue(self.vu.workspace(set_id, "vu")["sample_declarable"], "one annotator so far")
        declared = self.vu.declare_sample(set_id, "phapche", "0.5", seed)
        self.assertEqual((declared["articles"], declared["sentences"], declared["declared_by"]), (["luat/article-1"], 2, "phapche"))
        with self.assertRaisesRegex(ValueError, "không đổi được"):
            self.vu.declare_sample(set_id, "phapche")
        view = self.vu.workspace(set_id, "vu")
        self.assertEqual([i["in_sample"] for i in view["items"]], [True, True, False])
        self.assertEqual((view["sample"]["seed"], view["sample_declarable"]), (seed, False))
        self.assertEqual(self.vu.summary(set_id)["sample_size"], {"articles": 1, "sentences": 2})

        with self.assertRaisesRegex(ValueError, "cần nhãn của cả hai người"):
            self.vu.adjudicate(set_id, first, [OBLIGATION], "phapche")
        with self.assertRaisesRegex(ValueError, "2 câu trong mẫu đồng thuận chưa có đủ nhãn của hai người; 1 câu ngoài mẫu có nhãn của một người"):
            self.vu.gold_file(set_id)
        self.vu.save(set_id, first, "vu", "Vũ", [OBLIGATION])
        self.vu.save(set_id, second, "vu", "Vũ", [])
        report = self.vu.comparison(set_id, "vu", "kha")
        self.assertEqual((report["sample_progress"], report["labelled_by_both"]), ({"vu": 2, "kha": 2}, 2))
        self.assertEqual([i["status"] for i in report["items"]], ["agreed", "disagree", "single"])
        self.assertEqual(report["plan"], {"final": 0, "agreed": 1, "single": 1, "disagree": 1, "missing_second": 0, "unlabelled": 0})

        self.assertEqual(self.vu.finalise(set_id), {"agreed": 1, "single": 1, "blockers": [
            {"kind": "disagree", "n": 1, "message": "1 câu hai người gán khác nhau, cần đối soát từng câu"}]})
        self.assertEqual(self.vu.finalise(set_id)["agreed"], 0, "finals are kept, not rewritten")
        with self.assertRaisesRegex(ValueError, "^Chưa xuất được gold cuối: 1 câu hai người gán khác nhau"):
            self.vu.gold_file(set_id)
        self.vu.adjudicate(set_id, second, [RIGHT], "phapche")
        rows = self.vu.gold_file(set_id)
        units = self.corpora.bundle(self.version)[1]
        self.assertEqual(extraction_gold.check(rows, units), [])
        self.assertEqual([r["annotation"] for r in rows], [
            {"mode": "double", "annotators": ["kha", "vu"], "decided_by": "agreed:kha+vu", "in_sample": True},
            {"mode": "double", "annotators": ["kha", "vu"], "decided_by": "adjudicated:phapche", "in_sample": True},
            {"mode": "single", "annotators": ["kha"], "decided_by": "single:kha", "in_sample": False}])
        self.assertEqual([r["norms"] for r in rows], [[OBLIGATION], [RIGHT], []])
        self.assertEqual(provenance("agreed:kha+vu"), {"kind": "agreed", "people": ["kha", "vu"]})

        report = extraction_gold.score(rows, extraction_gold.rule_predictions(units, rows))
        self.assertEqual((report["annotation"], report["double_annotated"]["sentences"]), ({"double": 2, "single": 1}, 2))
        self.assertEqual(set(report["double_annotated"]), {"sentences", "strict", "lenient"})
        older = [{k: v for k, v in r.items() if k != "annotation"} for r in rows]
        self.assertNotIn("double_annotated", extraction_gold.score(older, older), "gold files without annotation score as before")

        # A new label drops the bulk final made from the old one; a person's decision stays.
        self.vu.save(set_id, third, "kha", "Kha", [{"modality": "unknown", "modality_cue": None, "slots": {"object": "Tiền lương thử việc"}}])
        with self.assertRaisesRegex(ValueError, "1 câu ngoài mẫu có nhãn của một người chưa được chốt"):
            self.vu.gold_file(set_id)
        self.vu.save(set_id, second, "kha", "Kha", [RIGHT])
        self.assertEqual(self.vu.comparison(set_id, "vu", "kha")["items"][1]["final"]["decided_by"], "adjudicated:phapche")
        self.assertEqual(self.vu.finalise(set_id)["single"], 1)
        self.assertEqual(self.vu.gold_file(set_id)[2]["norms"][0]["slots"], {"object": "Tiền lương thử việc"})

    def test_sample_cannot_be_declared_after_a_second_annotator_labelled(self):
        made, seed, (first, *_rest) = self._sampled_set()
        self.vu.save(made["id"], first, "kha", "Kha", [OBLIGATION])
        self.vu.save(made["id"], first, "vu", "Vũ", [OBLIGATION])
        self.assertFalse(self.vu.workspace(made["id"], "vu")["sample_declarable"])
        with self.assertRaisesRegex(ValueError, r"nhãn của 2 người \(kha, vu\).*trước khi người gán thứ hai"):
            self.vu.declare_sample(made["id"], "phapche", "0.5", seed)
        with self.assertRaisesRegex(ValueError, "Tỉ lệ mẫu"):
            self.vu.declare_sample(made["id"], "phapche", "2")
        # Without a sample a set keeps full double annotation: no single finals, every row must be decided.
        self.assertEqual(self.vu.finalise(made["id"]), {"agreed": 1, "single": 0, "blockers": [
            {"kind": "unfinished", "n": 2, "message": "Còn 2 câu chưa chốt nhãn cuối"}]})

    def test_pack_carries_the_sample_and_tampered_samples_are_refused(self):
        made, seed, _keys = self._sampled_set()
        pack = self.vu.export_pack(made["id"])
        self.assertNotIn("sample", pack)
        self.kha.import_pack(pack, "kha")
        self.vu.declare_sample(made["id"], "phapche", "0.5", seed)
        pack = self.vu.export_pack(made["id"])
        tampered = pack | {"sample": pack["sample"] | {"articles": ["luat/article-2"]}}
        with self.assertRaisesRegex(ValueError, "Mẫu đồng thuận trong gói không khớp"):
            self.kha.import_pack(tampered, "kha")
        self.kha.import_pack(pack, "kha")
        self.assertEqual(self.kha.workspace(made["id"], "kha")["sample"]["articles"], ["luat/article-1"], "a later pack adds the sample")

    def test_store_without_the_sample_table_and_bare_adjudicator_names_keep_working(self):
        made = self.vu.create("Gold cũ", self.version, "vu", articles=["luat/article-2"])
        (key,) = [i["key"] for i in self.vu.workspace(made["id"], "vu")["items"]]
        with closing(sqlite3.connect(self.vu.path)) as db, db:
            db.execute("DROP TABLE gold_samples")
            db.execute("INSERT INTO gold_final VALUES (?,?,?,?,?)", (made["id"], key, "[]", "vu", "2026-11-08T00:00:00+00:00"))
        reopened = GoldStore(self.vu.path, self.corpora)
        view = reopened.workspace(made["id"], "vu")
        self.assertEqual((view["sample"], view["sample_declarable"], view["blockers"]), (None, True, []))
        self.assertEqual(reopened.comparison(made["id"], "vu", "kha")["items"][0]["final"]["kind"], "adjudicated")
        self.assertEqual(reopened.gold_file(made["id"])[0]["annotation"], {"mode": "single", "annotators": ["vu"], "decided_by": "vu"})


if __name__ == "__main__":
    unittest.main()
