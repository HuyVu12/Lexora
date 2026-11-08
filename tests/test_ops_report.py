"""Results report for the supervisor: data from run folders and stores, team notes, and the exported HTML."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.ops.report import DEFAULT_NOTES, audits, clean_notes, experiment_runs, render_html, report_data


def summary(model, dk3, dk4, planned=95, attempted=95):
    return {"model": model, "provider": "9router", "batches_ok": attempted, "batches_planned": planned, "batches_attempted": attempted,
            "sentence_answer_rate": 0.9, "dk3_claims": dk3, "dk4_claims": dk4, "rejected": dk3 - dk4, "rejected_rate": (dk3 - dk4) / dk3,
            "call_error_rate": 0.0, "injection": {"detectable_rate": 0.98, "semantic_rate": 0.0},
            "rejection_explained": {"categories": {"context": dk3 - dk4 - 1, "not_found": 1}}}


class ReportTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def write(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")

    def test_runs_audits_and_status_come_from_the_folders(self):
        self.write("kb-a/manifest.json", {"run_version": "llm-kb-run-v1", "created_at": "2026-11-08"})
        self.write("dk1/manifest.json", {"condition": {"condition": "DK1"}, "retrieval": {}})
        self.write("answers/manifest.json", {"retrieval_run": "dk1"})
        self.write("inject-a/report.json", {"injection_version": "error-injection-v1"})
        self.write("audit/key.json", {"audit_version": "rejection-audit-v1", "items": {"R1": {}, "R2": {}}})
        self.write("audit/sheet.csv", "item_id,label\nR1,sai\nR2,\n")
        runs = {r["name"]: r["kind"] for r in experiment_runs(self.root)}
        self.assertEqual(runs, {"kb-a": "kb", "dk1": "retrieval", "answers": "answer", "inject-a": "injection"})
        progress = audits(self.root)
        self.assertEqual(progress, [{"name": "audit", "items": 2, "sheets": [{"file": "sheet.csv", "items": 2, "labelled": 1}]}])

        data = report_data([summary("big", 100, 90), summary("weak", 100, 60), summary("sample", 10, 9, attempted=8)],
                           golds=[{"labelled": {"vu": 3}, "adjudicated": 0}], question_sets=[], runs=experiment_runs(self.root),
                           audit_progress=progress, notes=None)
        self.assertEqual([r["model"] for r in data["extraction"]], ["weak", "big"], "most rejected first, sample-only runs left out")
        self.assertEqual(data["sampled_models"], ["sample"])
        self.assertEqual([s["state"] for s in data["status"]], ["partial", "partial", "partial"])
        self.assertIn("1/2 dòng đã gán", data["status"][1]["facts"])
        self.assertEqual(data["notes"], DEFAULT_NOTES)

    def test_html_is_self_contained_and_escapes_text(self):
        notes = clean_notes({"limitations": ["<script>alert(1)</script>", "  "], "next_steps": [], "questions": ["Có nên?"]})
        self.assertEqual(notes["limitations"], ["<script>alert(1)</script>"], "blank lines dropped")
        data = report_data([summary("<b>m</b>", 100, 80)], golds=[], question_sets=[], runs=[], audit_progress=[], notes=notes)
        html = render_html(data)
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertNotIn("<script>alert", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn("&lt;b&gt;m&lt;/b&gt;", html)
        self.assertIn("20,0%", html)
        self.assertNotIn("—", html)

    def test_notes_are_validated(self):
        with self.assertRaisesRegex(ValueError, "chỉ gồm"):
            clean_notes({"other": []})
        with self.assertRaisesRegex(ValueError, "12 dòng"):
            clean_notes({"questions": ["x"] * 13})


if __name__ == "__main__":
    unittest.main()
