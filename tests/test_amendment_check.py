"""Check sheet for amendment edges: one row per edge, verdict counts and agreement of two checkers. Synthetic texts only."""

import csv
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_retrieval_run import SYNTHETIC, bundle
from test_validity import AMENDING, AMENDING_V2
from legal_ai.common.io import write_json, write_jsonl
from legal_ai.kb.amendment_check import COLUMNS, agreement, make_sheet, score_sheet
from legal_ai.kb.amendments import detect, link_amending_units


class AmendmentCheckTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        _, units, texts = bundle(self.root / "bundle", {"1-2020-nd-cp": SYNTHETIC, "2-2021-nd-cp": AMENDING})
        self.edges = link_amending_units(detect({"document_id": "2-2021-nd-cp"}, texts["2-2021-nd-cp"], units, "2021-07-01"),
                                         units, texts["2-2021-nd-cp"])
        write_jsonl(self.root / "edges" / "edges.jsonl", self.edges)
        write_json(self.root / "edges" / "manifest.json", {"edge_version": "amendment-rules-v1", "bundle": (self.root / "bundle").as_posix()})
        self.sheet = self.root / "sheet.csv"
        self.report = make_sheet(self.root / "edges", self.sheet)

    def read(self, path):
        with Path(path).open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def fill(self, name, verdicts):
        rows = self.read(self.sheet)
        for row in rows:
            row["verdict"] = verdicts.get(row["edge_key"], "")
        path = self.root / name
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_every_edge_is_a_row_with_its_texts_and_empty_verdict_columns(self):
        self.assertTrue(self.sheet.read_bytes().startswith(b"\xef\xbb\xbf"), "BOM so spreadsheet apps read UTF-8")
        rows = self.read(self.sheet)
        self.assertEqual([r["edge_key"] for r in rows], [e["edge_id"] for e in self.edges], "every edge, in edge order")
        self.assertEqual(self.report["edges"], len(self.edges))
        self.assertTrue({"resolved", "unresolved", "external"} <= {r["status"] for r in rows}, "unresolved targets are listed too")
        self.assertTrue(all(r["verdict"] == "" and r["note"] == "" for r in rows))
        modify = next(r for r in rows if r["status"] == "resolved" and r["kind"].startswith("modify"))
        self.assertEqual(modify["instruction"], "Sửa đổi, bổ sung khoản 2 Điều 1 như sau:")
        self.assertIn("khoản 2 Điều 1", modify["target_named"])
        self.assertIn("[1-2020-nd-cp/chapter-i/article-1/clause-2]", modify["target_unit"])
        self.assertIn("Ít nhất 30 ngày", modify["target_text"], "the text in force before the amendment")
        self.assertIn("Ít nhất 35 ngày", modify["new_wording_text"], "the new wording comes from the amending unit")
        self.assertEqual(modify["effective_from"], "2021-07-01")
        external = next(r for r in rows if r["status"] == "external")
        self.assertEqual((external["target_unit"], external["target_text"]), ("(không có trong corpus)", ""))
        added = next(r for r in rows if r["status"] == "resolved_parent")
        self.assertIn("đơn vị cha gần nhất", added["target_unit"])
        with self.assertRaisesRegex(ValueError, "sheet exists"):
            make_sheet(self.root / "edges", self.sheet)

    def test_scores_count_verdicts_per_status_and_reject_unknown_ones(self):
        keys = [e["edge_id"] for e in self.edges]
        resolved = [e["edge_id"] for e in self.edges if e["status"] == "resolved"]
        filled = self.fill("a.csv", {resolved[0]: "dung", resolved[1]: "sai_dich", keys[-1]: "khac"})
        report = score_sheet(filled)
        self.assertEqual((report["edges"], report["checked"]), (len(keys), 3))
        self.assertEqual(report["by_status"]["resolved"]["verdicts"], {"dung": 1, "sai_dich": 1})
        self.assertEqual(report["by_status"]["resolved"]["correct_rate"], {"value": 0.5, "n": 2})
        self.assertEqual(sum(g["edges"] for g in report["by_kind"].values()), len(keys))
        bad = self.fill("bad.csv", {keys[0]: "correct"})
        with self.assertRaisesRegex(ValueError, "not one of"):
            score_sheet(bad)

    def test_agreement_gives_raw_agreement_kappa_and_the_disagreements(self):
        keys = [e["edge_id"] for e in self.edges][:4]
        first = self.fill("a.csv", dict(zip(keys, ["dung", "dung", "sai_loai", "dung"])))
        second = self.fill("b.csv", dict(zip(keys, ["dung", "sai_dich", "sai_loai", "dung"])))
        report = agreement(first, second)
        self.assertEqual(report["n"], 4)
        self.assertEqual(report["verdicts"]["raw_agreement"], 0.75)
        self.assertEqual(report["disagreements"], [{"edge_key": keys[1], "first": "dung", "second": "sai_dich"}])
        self.assertEqual(report["correct_or_not"]["raw_agreement"], 0.75)
        self.assertAlmostEqual(report["verdicts"]["kappa"], (0.75 - 7 / 16) / (1 - 7 / 16), msg="chance agreement (3x2 + 1x1) / 16")


    def test_heading_only_changes_and_expiry_statements_are_listed_with_their_kind(self):
        _, units, texts = bundle(self.root / "bundle-v2", {"1-2020-nd-cp": SYNTHETIC, "3-2022-nd-cp": AMENDING_V2})
        edges = link_amending_units(detect({"document_id": "3-2022-nd-cp"}, texts["3-2022-nd-cp"], units, "2022-07-01"), units, texts["3-2022-nd-cp"])
        write_jsonl(self.root / "edges-v2" / "edges.jsonl", edges)
        write_json(self.root / "edges-v2" / "manifest.json", {"edge_version": "amendment-rules-v2", "bundle": (self.root / "bundle-v2").as_posix()})
        report = make_sheet(self.root / "edges-v2", self.root / "sheet-v2.csv")
        rows = self.read(self.root / "sheet-v2.csv")
        self.assertEqual(report["edges"], len(edges))
        heading = next(r for r in rows if r["instruction"].startswith("Sửa đổi, bổ sung tên khoản 2"))
        self.assertIn("chỉ tên hoặc câu dẫn", heading["kind"])
        subject = next(r for r in rows if r["kind"].startswith("expire_subject"))
        self.assertEqual((subject["status"], subject["target_unit"]), ("unresolved", "(không xác định được Điều, khoản bằng quy tắc)"))
        self.assertTrue(any(r["kind"].startswith("expire_document") and r["target_unit"] == "(cả văn bản)" for r in rows))


if __name__ == "__main__":
    unittest.main()
