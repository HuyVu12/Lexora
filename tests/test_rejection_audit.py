"""Why claims were rejected (automatic) and whether they are wrong (blinded human sheet). Synthetic statute, stand-in model."""

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_kb_run import norm
from test_retrieval_run import bundle
from legal_ai.evaluation import kb_run
from legal_ai.evaluation.rejection_audit import agreement, explain, make_sheet, score_sheet

LAW = ("Điều 1. Chấm dứt thử việc giả định\n"
       "1. Bên B có quyền chấm dứt thử việc trong trường hợp sau đây:\n"
       "a) Bên A không trả lương đúng hạn;\n"
       "b) Bên A vi phạm thỏa thuận về điều kiện làm việc.\n"
       "2. Bên A phải thông báo kết quả thử việc cho bên B.\n")


class ListStandIn:
    model = "stand-in-list"

    def structured(self, system, prompt, schema, purpose="structured"):
        results = []
        for sentence in json.loads(prompt)["sentences"]:
            text = sentence["text"]
            if "không trả lương" in text:  # Actor and action from the lead-in of clause 1: right, not in the sentence.
                norms = [norm("Bên B", "chấm dứt thử việc", "entitlement", "có quyền", conditions="Bên A không trả lương đúng hạn")]
            elif "vi phạm" in text:  # An actor found nowhere in the statute.
                norms = [norm("Người lao động", "chấm dứt thử việc", "entitlement", None, conditions="Bên A vi phạm thỏa thuận")]
            elif "thông báo" in text:
                norms = [norm("Bên A", "thông báo kết quả thử việc", recipient="bên B"),
                         norm("Bên A", "thông báo", "entitlement", "phải")]  # "phải" is an obligation cue.
            else:
                norms = [norm("Bên B", "chấm dứt thử việc", "entitlement", "có quyền")]
            results.append({"sentence": sentence["id"], "norms": norms})
        return {"output": {"results": results}, "usage": {}, "cost_usd": 0, "model": self.model}


class RejectionAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        _, units, _ = bundle(self.root / "bundle", {"syn": LAW})
        self.run = self.root / "kb"
        kb_run.start(self.root / "bundle", self.run, "stand-in-list", "medium")
        kb_run.extract(units, ListStandIn(), self.run)
        self.report = kb_run.materialize(units, self.run)

    def test_rejections_are_split_by_where_the_missing_text_is(self):
        found = explain(self.run)
        self.assertEqual(found["rejected"], self.report["rejected"])
        self.assertEqual(found["categories"], {"context": 1, "modality_only": 1, "not_found": 1})
        self.assertEqual(found["values_found"], {"ancestor": 4, "nowhere": 1},
                         "actor, action, cue of point a) and the action of point b) are in the lead-in; the actor of point b) is nowhere")

    def test_blinded_sheet_scores_wrong_rates_per_decision_and_agreement(self):
        sheet, key = self.root / "audit.csv", self.root / "key.json"
        counts = make_sheet([self.run], sheet, key, rejected=10, accepted=10)
        self.assertEqual((counts["rejected"], counts["accepted"]), (3, self.report["dk4_claims"]))
        text = sheet.read_text(encoding="utf-8-sig")
        self.assertNotIn("stand-in-list", text, "annotators do not see the model")
        self.assertNotIn("not_verbatim", text, "annotators do not see the validator's reasons")
        with sheet.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        point_a = next(r for r in rows if "không trả lương" in r["sentence"])
        self.assertIn("Bên B có quyền chấm dứt thử việc trong trường hợp sau đây", point_a["context"])
        self.assertIn("Chủ thể: Bên B", point_a["norm"])

        items = json.loads(key.read_text(encoding="utf-8"))["items"]
        first = [dict(r, label=("dung_ngu_canh" if "không trả lương" in r["sentence"] else "sai") if items[r["item_id"]]["decision"] == "rejected" else "dung")
                 for r in rows]
        second = [dict(r, label=("sai" if "không trả lương" in r["sentence"] else r["label"])) for r in first]
        for path, data in ((self.root / "a.csv", first), (self.root / "b.csv", second)):
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(data)
        report = score_sheet(self.root / "a.csv", key)["by_model"]["stand-in-list"]
        self.assertEqual(report["rejected"]["wrong_rate"], {"value": 2 / 3, "n": 3})
        self.assertEqual(report["accepted"]["wrong_rate"]["value"], 0)
        self.assertEqual(report["rejected"]["by_automatic"]["context"], {"dung_ngu_canh": 1})
        self.assertLess(agreement(self.root / "a.csv", self.root / "b.csv")["labels"]["kappa"], 1)

        bad = [dict(r, label="đúng") for r in rows]
        with (self.root / "bad.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(bad)
        with self.assertRaisesRegex(ValueError, "not one of"):
            score_sheet(self.root / "bad.csv", key)


if __name__ == "__main__":
    unittest.main()
