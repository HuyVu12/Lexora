"""Review pack tools: the page builder (safe embedding, blind data) and the converters to Lexora formats. Synthetic data only."""

import csv
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.research.audit import AuditStore
from legal_ai.research.corpus import CorpusStore
from legal_ai.research.gold import GoldStore

FIXTURES = ROOT / "tests" / "fixtures" / "review_pack"


def load(name):
    spec = importlib.util.spec_from_file_location(f"review_pack_{name}", ROOT / "scripts" / "review_pack" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build, convert = load("build"), load("convert")
LAW = ("Điều 1. Thử việc giả định\n1. Bên A phải thông báo kết quả thử việc cho bên B.\n2. Bên B có quyền chấm dứt thử việc.\n"
       "Điều 2. Tiền lương giả định\nTiền lương thử việc do hai bên thỏa thuận.\n")
TAG = '<script type="application/json" id="pack-data">'


def embedded(html):
    start = html.index(TAG) + len(TAG)
    return html[start:html.index("</script>", start)]


class BuildTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.out = Path(temp.name)
        build.build(FIXTURES, self.out)

    def test_embedding_is_escaped_and_round_trips(self):
        html = (self.out / "review.html").read_text(encoding="utf-8")
        raw = embedded(html)
        for bad in ("</script", "<b>", " ", "<!--"):
            self.assertNotIn(bad, raw)
        pack = json.loads(raw)
        text = next(i for i in pack["tasks"]["audit"]["items"] if i["id"] == "aud-002")["fields"][0]["text"]
        self.assertIn("</script><b>x</b> &  ", text)
        self.assertEqual(pack["order"][0], "gold")
        self.assertEqual(html.count("</script>"), 2, "only the data tag and the page script close")

    def test_blind_page_has_no_suggestions_in_its_data(self):
        blind = (self.out / "review-blind.html").read_text(encoding="utf-8")
        pack = json.loads(embedded(blind))
        self.assertEqual(pack["mode"], "blind")
        for task in pack["tasks"].values():
            self.assertNotIn("drafted_by", task)
            for item in task["items"]:
                self.assertFalse({"suggestion", "reason", "confidence", "export"} & set(item), item["id"])
                self.assertEqual(item.get("draft", []), [])
        for secret in ("Hết hiệu lực.", "Văn bản có hiệu lực từ 2026-09-10", "Có từ tình thái phải.", "Khớp câu.", "in_force", "target_document_not_in_corpus"):
            self.assertNotIn(secret, blind)
        full = json.loads(embedded((self.out / "review.html").read_text(encoding="utf-8")))
        self.assertEqual(full["mode"], "suggestions")
        self.assertIn("suggestion", full["tasks"]["validity"]["items"][0])
        self.assertNotIn("export", full["tasks"]["validity"]["items"][0])

    def test_duplicate_ids_are_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            task = json.loads((FIXTURES / "audit.json").read_text(encoding="utf-8"))
            task["items"].append(task["items"][0])
            (Path(temp) / "audit.json").write_text(json.dumps(task), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "trùng"):
                build.load_tasks(temp)


class GoldConvertTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.corpora = CorpusStore(root / "vu.sqlite")
        corpus = self.corpora.create("Thử", "Corpus thử", "vu")
        self.corpora.add_file(corpus["id"], "luat.txt", LAW.encode("utf-8"), "vu")
        version = self.corpora.freeze(corpus["id"], "v1", "vu")["id"]
        self.vu = GoldStore(root / "vu.sqlite", self.corpora)
        self.set = self.vu.create("Gold thử", version, "vu", articles=["luat/article-1"])
        self.keys = [i["key"] for i in self.vu.workspace(self.set["id"], "vu")["items"]]
        self.kha = GoldStore(root / "kha.sqlite", CorpusStore(root / "kha.sqlite"))
        self.kha.import_pack(self.vu.export_pack(self.set["id"]), "kha")

    def review(self, items):
        return {"task": "gold", "reviewer": "Vũ", "mode": "suggestions", "exported_at": "2026-11-24T10:00:00Z", "items": items}

    def test_labels_file_is_accepted_by_import_labels(self):
        norm = {"modality": "obligation", "cue": "phải", "slots": {"actor": "Bên A", "action": "thông báo kết quả thử việc", "recipient": "bên B"}}
        review = self.review([{"id": self.keys[0], "value": "norms", "note": "", "edited_norms": [norm], "changed_from_suggestion": False},
                              {"id": self.keys[1], "value": "no_norm", "note": "", "edited_norms": [], "changed_from_suggestion": True}])
        before = Path(self.vu.path).read_bytes()
        body = convert.gold_labels(review, self.vu.path)
        self.assertEqual(Path(self.vu.path).read_bytes(), before, "the source store is never modified")
        self.assertEqual((body["annotator"], body["annotator_name"], body["set_id"]), ("huyvu", "Huy Vũ", self.set["id"]))
        self.assertEqual(body["labels"][0]["norms"][0]["modality_cue"], "phải")
        self.assertEqual(self.kha.import_labels(body, "kha")["labels"], 2)
        tampered = json.loads(json.dumps(body))
        tampered["labels"][0]["norms"] = []
        with self.assertRaisesRegex(ValueError, "mã băm"):
            self.kha.import_labels(tampered, "kha")

    def test_value_that_is_not_in_the_sentence_is_refused(self):
        norm = {"modality": "obligation", "cue": "phải", "slots": {"action": "báo ngay"}}
        with self.assertRaisesRegex(ValueError, "nguyên văn"):
            convert.gold_labels(self.review([{"id": self.keys[0], "value": "norms", "edited_norms": [norm]}]), self.vu.path)
        with self.assertRaisesRegex(ValueError, "không thuộc bộ gold"):
            convert.gold_labels(self.review([{"id": "x@1-2", "value": "no_norm", "edited_norms": []}]), self.vu.path)


class CsvAndAuditTests(unittest.TestCase):
    def test_csv_round_trip_keeps_every_original_column(self):
        for task, human in (("validity", {"annotator_agrees", "annotator_note"}), ("link", {"needs_B (co/khong)", "gold_ok (co/khong)", "note"}),
                            ("amendment", {"verdict", "note"})):
            data = json.loads((FIXTURES / f"{task}.json").read_text(encoding="utf-8"))
            first = data["items"][0]
            note = "ghi chú, có \"dấu\"\nxuống dòng"
            review = {"task": task, "reviewer": "Vũ", "items": [{"id": first["id"], "value": data["options"][0]["value"], "note": note}]}
            with tempfile.TemporaryDirectory() as temp:
                out = Path(temp) / "sheet.csv"
                self.assertEqual(convert.write_csv(task, review, FIXTURES, out), len(data["items"]))
                self.assertTrue(out.read_bytes().startswith(b"\xef\xbb\xbf"))
                with out.open(encoding="utf-8-sig", newline="") as handle:
                    rows = list(csv.DictReader(handle))
            self.assertEqual(list(rows[0]), convert.SHEETS[task]["columns"])
            for column in convert.SHEETS[task]["columns"]:
                if column not in human:
                    self.assertEqual(rows[0][column], first["export"][column], f"{task}.{column}")
            self.assertEqual(rows[0][convert.SHEETS[task]["note"]], note)
            if len(rows) > 1:
                self.assertTrue(all(rows[1][c] == "" for c in human), "an unreviewed item keeps empty human columns")
        rows = convert.csv_rows("validity", {"task": "validity", "items": [{"id": "hl-a02|dap-an|u2", "value": "khong_dong_y", "note": ""}]}, FIXTURES)[1]
        self.assertEqual(rows[1]["annotator_agrees"], "khong")

    def test_csv_refuses_unknown_values(self):
        with self.assertRaisesRegex(ValueError, "options"):
            convert.csv_rows("amendment", {"task": "amendment", "items": [{"id": "98375aaf99ff8c10ad7cdce5", "value": "la"}]}, FIXTURES)
        with self.assertRaisesRegex(ValueError, "không có trong dữ liệu"):
            convert.csv_rows("amendment", {"task": "amendment", "items": [{"id": "zzz", "value": "dung"}]}, FIXTURES)

    def test_audit_labels_saved_on_a_temp_store(self):
        review = {"task": "audit", "reviewer": "Vũ", "items": [{"id": "R0", "value": "dung_ngu_canh", "note": "ghi chú"}, {"id": "R1", "value": None, "note": ""}]}
        labels = convert.audit_labels(review)
        self.assertEqual(labels["labels"], [{"item_id": "R0", "label": "dung_ngu_canh", "note": "ghi chú"}])
        rows = [{"item_id": f"R{n}", "context": "c", "unit_text": "t", "sentence": "s", "norm": "n"} for n in range(2)]
        key = {f"R{n}": {"model": "m", "decision": "rejected", "automatic": None} for n in range(2)}
        with tempfile.TemporaryDirectory() as temp:
            store = AuditStore(Path(temp) / "a.sqlite")
            made = store.create("Thử", rows, key, "vu")
            self.assertEqual(convert.save_audit(labels, store.path, made["id"]), 1)
            mine = store.workspace(made["id"], "huyvu")
            self.assertEqual(mine["rows"][0]["mine"]["label"], "dung_ngu_canh")
            self.assertEqual(mine["labelled"]["huyvu"]["name"], "Huy Vũ")
        with self.assertRaisesRegex(ValueError, "nhãn"):
            convert.audit_labels({"task": "audit", "items": [{"id": "R0", "value": "tốt"}]})


if __name__ == "__main__":
    unittest.main()
