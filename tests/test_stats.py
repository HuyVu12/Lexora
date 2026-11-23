"""Paired bootstrap, Holm correction, noise and the paired-stats command. Synthetic data, stand-in model."""

import csv
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_answer_run import QUESTIONS, StandIn
from test_retrieval_run import SYNTHETIC, bundle
from legal_ai import cli
from legal_ai.evaluation import answer_grading, outcome_judge, stats
from legal_ai.providers.pilot import ProviderError
from legal_ai.evaluation.answer_run import question_scores, run as answer_run, score
from legal_ai.evaluation.retrieval_run import run as retrieval_run


def run_of(values, unscored=()):
    return {"values": values, "unscored": list(unscored)}


class OutcomeJudge:
    """Stand-in outcome judge: grades differ by question, never by condition."""
    model, effort = "judge-stand-in", "medium"

    def structured(self, system, prompt, schema, purpose="structured"):
        request = json.loads(prompt)
        n, good = len(request["statements"]), "báo trước" in request["question"]
        if schema["properties"]["statements"]["minItems"] != n:
            raise ProviderError("statement_count_mismatch")
        return {"output": {"statements": [{"supported": 2, "citation_correct": True, "legal_error": False} for _ in range(n)],
                           "issues": [{"addressed": 2 if good else 1}, {"addressed": 1}], "outcome": 2 if good else 0,
                           "correctness": 2 if good else 1}, "model": self.model}


class BootstrapTests(unittest.TestCase):
    def test_same_seed_gives_the_same_result_and_the_seed_is_recorded(self):
        diffs = [0.13, -0.71, 0.05, 0.92, 0.27, 1.61, -0.44, 0.38]
        first, second = stats.paired_bootstrap(diffs, 2000, "seed-a"), stats.paired_bootstrap(diffs, 2000, "seed-a")
        self.assertEqual(first, second)
        self.assertNotEqual(first, stats.paired_bootstrap(diffs, 2000, "seed-b"))
        report = stats.build_report("retrieval.recall@1", {"A": run_of({"q1": 0.0, "q2": 1.0}), "B": run_of({"q1": 1.0, "q2": 1.0})},
                                    [("A", "B")], rounds=500, seed="seed-a")
        self.assertEqual((report["method"]["seed"], report["method"]["rounds"], report["stats_version"]), ("seed-a", 500, "paired-stats-v1"))
        self.assertEqual(report, stats.build_report("retrieval.recall@1", {"A": run_of({"q2": 1.0, "q1": 0.0}), "B": run_of({"q1": 1.0, "q2": 1.0})},
                                                    [("A", "B")], rounds=500, seed="seed-a"), "question order does not matter")

    def test_all_zero_differences_are_no_evidence(self):
        result = stats.paired_bootstrap([0.0] * 6, 1000, "s")
        self.assertEqual((result["difference"], result["ci95"], result["p_value"]), (0.0, [0.0, 0.0], 1.0))
        self.assertEqual((result["n"], result["wins"], result["losses"], result["ties"]), (6, 0, 0, 6))

    def test_all_positive_differences_reach_the_smallest_p(self):
        same = stats.paired_bootstrap([1.0] * 5, 1000, "s")
        self.assertEqual((same["difference"], same["ci95"], same["p_value"]), (1.0, [1.0, 1.0], 1 / 1001))
        varied = stats.paired_bootstrap([0.5, 1.0, 2.0], 1000, "s")
        # No resampled mean is <= 0 or >= twice the observed 1.1667, so no shifted mean reaches the observed distance.
        self.assertEqual((varied["p_value"], varied["wins"]), (1 / 1001, 3))
        self.assertTrue(0.5 <= varied["ci95"][0] <= varied["difference"] <= varied["ci95"][1] <= 2.0)

    def test_wins_losses_ties_and_empty_input(self):
        result = stats.paired_bootstrap([1.0, -0.5, 0.0, 0.0, 2.0], 200, "s")
        self.assertEqual((result["wins"], result["losses"], result["ties"]), (2, 1, 2))
        self.assertAlmostEqual(result["difference"], 0.5)
        self.assertEqual(stats.paired_bootstrap([], 200, "s"), {"n": 0, "difference": None, "ci95": None, "p_value": None,
                                                               "wins": 0, "losses": 0, "ties": 0})
        with self.assertRaises(ValueError):
            stats.paired_bootstrap([1.0], 0, "s")

    def test_holm_hand_checked(self):
        # Sorted 0.005, 0.01, 0.03, 0.04 times 4, 3, 2, 1 = 0.02, 0.03, 0.06, 0.04; running maximum keeps 0.06 for the last.
        adjusted = stats.holm([0.01, 0.04, 0.03, 0.005])
        for got, expected in zip(adjusted, [0.03, 0.06, 0.06, 0.02]):
            self.assertAlmostEqual(got, expected)
        self.assertEqual(stats.holm([0.5, 0.6]), [1.0, 1.0], "capped at 1 and monotone")
        self.assertEqual(stats.holm([0.01, None]), [0.02, None], "a comparison without p still counts in the family")
        self.assertEqual(stats.holm([]), [])


class ReportTests(unittest.TestCase):
    def test_missing_unscored_and_valueless_questions_are_reported_not_dropped(self):
        first = run_of({"q1": 1.0, "q2": 0.0, "q3": None, "q4": 1.0}, unscored=["q5"])
        second = run_of({"q1": 0.0, "q2": 0.0, "q3": None, "q4": None, "q5": 1.0, "q6": 1.0})
        result = stats.compare(first, second, 200, "s", ("A", "B"))
        self.assertEqual(result["questions"], {"paired": 2, "not_applicable": 1, "missing": {"A": ["q6"], "B": []},
                                               "unscored": {"A": ["q5"], "B": []}, "no_value": {"A": [], "B": ["q4"]}})
        self.assertEqual((result["n"], result["difference"], result["mean_first"], result["mean_second"]), (2, -0.5, 0.5, 0.0))
        report = stats.build_report("answer.answered", {"A": first, "B": second}, [("A", "B")], rounds=200, seed="s")
        self.assertEqual(report["warnings"], ["A:B: 1 question(s) missing in A, left out of the pairing",
                                              "A:B: 1 question(s) unscored in A, left out of the pairing",
                                              "A:B: 1 question(s) no value in B, left out of the pairing"])
        self.assertEqual(report["runs"]["A"], {"mean": 0.666667, "scored": 3, "not_applicable": 1, "unscored": ["q5"]})

    def test_holm_covers_the_main_family_only_and_noise_sits_next_to_each_difference(self):
        runs = {name: run_of({f"q{i}": float((i + shift) % 3 == 0) for i in range(12)}) for name, shift in
                (("DK1", 0), ("DK2", 1), ("DK3", 1), ("DK4", 2))}
        repeats = {"DK1": run_of({f"q{i}": float(i % 3 == 0) if i else 1.0 - float(i % 3 == 0) for i in range(12)})}
        report = stats.build_report("answer.answered", runs, stats.MAIN_PAIRS, [("DK2", "DK4")], repeats=repeats, rounds=300, seed="s")
        main = [c for c in report["comparisons"] if c["family"] == "main"]
        self.assertEqual([c["pair"] for c in main], ["DK1:DK2", "DK2:DK3", "DK3:DK4", "DK1:DK4"])
        self.assertEqual([c["p_holm"] for c in main], [round(p, 6) for p in stats.holm([c["p_value"] for c in main])])
        self.assertIsNone(report["comparisons"][-1]["p_holm"], "exploratory pairs keep their raw p only")
        self.assertEqual(main[1]["difference"], 0.0)
        noise = report["noise"]["generation"]["by_label"]["DK1"]
        self.assertEqual((noise["n"], noise["changed"], noise["mean_abs_difference"]), (12, 1, round(1 / 12, 6)))
        self.assertEqual(main[0]["noise"]["generation"], {"DK1": {"difference": noise["difference"], "mean_abs_difference": noise["mean_abs_difference"]}})
        self.assertEqual(report["noise"]["generation"]["pooled"]["n"], 12)
        with self.assertRaisesRegex(ValueError, "without a run"):
            stats.build_report("answer.answered", runs, [("DK1", "DK5")], rounds=10)
        with self.assertRaisesRegex(ValueError, "twice"):
            stats.build_report("answer.answered", runs, [("DK1", "DK2")], [("DK1", "DK2")], rounds=10)
        with self.assertRaisesRegex(ValueError, "LABEL=DIR"):
            stats.labelled(["DK1"])
        self.assertEqual(stats.parse_pairs(["DK3-q:DK2"]), [("DK3-q", "DK2")], "labels may hold hyphens")


class ClusteredBootstrapTests(unittest.TestCase):
    DIFFS = [0.5, 0.25, 0.75, -0.25, 0.5, 1.0, 0.0, -0.5]

    def test_resamples_families_deterministically_and_collapses_to_one_cluster(self):
        clusters = ["f1", "f1", "f1", "f2", "f2", "q:5", "q:6", "q:7"]
        first = stats.paired_bootstrap(self.DIFFS, 2000, "seed-a", clusters)
        self.assertEqual(first, stats.paired_bootstrap(self.DIFFS, 2000, "seed-a", clusters))
        self.assertNotEqual(first, stats.paired_bootstrap(self.DIFFS, 2000, "seed-b", clusters))
        self.assertEqual((first["clusters"], first["n"]), (5, 8))
        self.assertAlmostEqual(first["difference"], sum(self.DIFFS) / 8, msg="the observed mean is the plain mean over questions")
        one = stats.paired_bootstrap(self.DIFFS, 500, "s", ["same"] * 8)
        self.assertEqual(one["clusters"], 1)
        self.assertAlmostEqual(one["ci95"][0], one["ci95"][1])
        self.assertAlmostEqual(one["ci95"][0], sum(self.DIFFS) / 8)

    def test_all_singleton_clusters_equal_the_plain_bootstrap_and_families_widen_the_interval(self):
        plain = stats.paired_bootstrap(self.DIFFS, 1000, "s")
        single = stats.paired_bootstrap(self.DIFFS, 1000, "s", [f"q:{i}" for i in range(8)])
        self.assertEqual((single.pop("clusters"), plain["ci95"]), (8, single["ci95"]))
        self.assertEqual(plain["p_value"], single["p_value"])
        paraphrases = [1.0, 1.0, 1.0, 1.0, -1.0, -1.0, -1.0, -1.0]
        width = lambda r: r["ci95"][1] - r["ci95"][0]
        self.assertGreater(width(stats.paired_bootstrap(paraphrases, 2000, "s", ["a"] * 4 + ["b"] * 4)),
                           width(stats.paired_bootstrap(paraphrases, 2000, "s")), "four paraphrases of one question are not four independent questions")
        with self.assertRaises(ValueError):
            stats.paired_bootstrap([1.0, 2.0], 10, "s", ["a"])

    def test_report_uses_family_ids_and_questions_without_one_are_their_own_cluster(self):
        a = {"values": {"q1": 0.0, "q2": 0.0, "q3": 1.0}, "unscored": [], "families": {"q1": "F", "q2": "F", "q3": None}}
        b = {"values": {"q1": 1.0, "q2": 1.0, "q3": 1.0}, "unscored": [], "families": {"q1": "F", "q2": "F", "q3": None}}
        self.assertEqual(stats.cluster_keys(["q1", "q2", "q3"], a, b), ["family:F", "family:F", "question:q3"])
        report = stats.build_report("retrieval.recall@1", {"A": a, "B": b}, [("A", "B")], rounds=200, seed="s", clustered=True)
        self.assertEqual(report["comparisons"][0]["clusters"], 2)
        self.assertIn("family-clustered", report["method"]["resampling"])
        plain = stats.build_report("retrieval.recall@1", {"A": a, "B": b}, [("A", "B")], rounds=200, seed="s")
        self.assertNotIn("clusters", plain["comparisons"][0])
        self.assertEqual(plain["method"]["resampling"].split(";")[0], "paired bootstrap over questions")


class EvidenceMetricsTests(unittest.TestCase):
    def test_evidence_metrics_are_read_from_predictions_or_from_a_rescore(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows = [{"question_id": "q1", "family_id": "F", "evidence_coverage": {"leaf_recall_tau1.0": {"3000": 0.5}, "complete": {"3000": 0.0}}},
                    {"question_id": "q2", "family_id": None, "evidence_coverage": {"leaf_recall_tau1.0": {"3000": None}, "complete": {"3000": None}}}]
            old = [{"question_id": "q1", "family_id": "F"}, {"question_id": "q2", "family_id": None}]
            for name, preds in (("new", rows), ("old", old)):
                (root / name).mkdir()
                (root / name / "predictions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in preds), encoding="utf-8")
                (root / name / "manifest.json").write_text(json.dumps({"condition": {"condition": "DK1"}, "inputs": {"questions": {"sha256": "x"}}}), encoding="utf-8")
            (root / "old" / "metrics-evidence.json").write_text(json.dumps({"questions": {r["question_id"]: r["evidence_coverage"] for r in rows}}), encoding="utf-8")
            loaded = stats.load_values("retrieval.leaf_recall_tau1.0_at_tokens@3000", {"N": root / "new", "O": root / "old"})
            self.assertEqual(loaded["N"]["values"], {"q1": 0.5, "q2": None})
            self.assertEqual(loaded["O"]["values"], loaded["N"]["values"])
            self.assertEqual(loaded["N"]["families"], {"q1": "F", "q2": None})
            complete = stats.load_values("retrieval.evidence_complete_at_tokens@3000", {"N": root / "new"})
            self.assertEqual(complete["N"]["values"], {"q1": 0.0, "q2": None})
            with self.assertRaisesRegex(ValueError, "not measured"):
                stats.load_values("retrieval.evidence_complete_at_tokens@500", {"N": root / "new"})
            with self.assertRaisesRegex(ValueError, "budget"):
                stats.load_values("retrieval.evidence_complete_at_tokens", {"N": root / "new"})
            (root / "old" / "metrics-evidence.json").unlink()
            with self.assertRaisesRegex(ValueError, "retrieval-rescore"):
                stats.load_values("retrieval.evidence_complete_at_tokens@3000", {"O": root / "old"})


class RunsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        bundle(self.root / "bundle", {"syn-a": SYNTHETIC})
        self.questions = self.root / "questions.json"
        self.questions.write_text(json.dumps(QUESTIONS, ensure_ascii=False), encoding="utf-8")
        shared = self.root / "shared.json"
        shared.write_text(json.dumps({"top_k": 3, "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75,
                                                                "recall_k": [1, 3]}}), encoding="utf-8")
        self.config = self.root / "answer.json"
        self.config.write_text(json.dumps({"prompt": "answer-v1.md", "top_k": 3, "context_token_budget": 200}), encoding="utf-8")
        for name, condition in (("DK1", {"representation": "fixed_chunks", "chunk_tokens": 40, "overlap_tokens": 8}),
                                ("DK2", {"representation": "structural_units", "max_tokens": 384})):
            path = self.root / f"{name}.json"
            path.write_text(json.dumps({"condition": name} | condition), encoding="utf-8")
            retrieval_run(self.root / "bundle", self.questions, path, shared, self.root / f"retrieval-{name}")

    def cli(self, *args):
        out = io.StringIO()
        with patch.object(sys, "argv", ["cli", "paired-stats", *args]), redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = cli.main()
        return code, out.getvalue()

    def test_cli_compares_retrieval_runs_and_writes_a_new_report(self):
        output = self.root / "report" / "recall.json"
        runs = ["--runs", f"DK1={self.root / 'retrieval-DK1'}", f"DK2={self.root / 'retrieval-DK2'}"]
        code, printed = self.cli("--metric", "retrieval.recall@3", *runs, "--pairs", "DK1:DK2", "--rounds", "500", "--output", str(output))
        self.assertEqual(code, 0)
        self.assertIn("DK1:DK2", printed)
        report = json.loads(output.read_text(encoding="utf-8"))
        comparison = report["comparisons"][0]
        self.assertEqual((comparison["n"], comparison["questions"]["not_applicable"], comparison["p_holm"] is not None), (2, 1, True),
                         "the refusal question has no gold units, so recall does not apply")
        self.assertEqual(report["inputs"]["runs"]["DK2"]["condition"], "DK2")
        with self.assertRaises(SystemExit):
            self.cli("--metric", "retrieval.recall@3", *runs, "--pairs", "DK1:DK2", "--output", str(output))  # never overwrites
        with self.assertRaises(SystemExit):
            self.cli("--metric", "retrieval.recall@7", *runs, "--pairs", "DK1:DK2", "--output", str(self.root / "other.json"))
        with self.assertRaises(SystemExit):
            self.cli("--metric", "retrieval.recall@3", *runs, "--output", str(self.root / "other.json"))  # default pairs need DK3, DK4

    def test_cli_rescore_and_clustered_evidence_comparison(self):
        runs = ["--runs", f"DK1={self.root / 'retrieval-DK1'}", f"DK2={self.root / 'retrieval-DK2'}"]
        metric = "retrieval.leaf_recall_tau1.0_at_tokens@250"
        plain, clustered = self.root / "plain.json", self.root / "clustered.json"
        self.assertEqual(self.cli("--metric", metric, *runs, "--pairs", "DK1:DK2", "--rounds", "300", "--output", str(plain))[0], 0)
        self.assertEqual(self.cli("--metric", metric, *runs, "--pairs", "DK1:DK2", "--rounds", "300", "--cluster-families", "--output", str(clustered))[0], 0)
        first, second = (json.loads(p.read_text(encoding="utf-8"))["comparisons"][0] for p in (plain, clustered))
        self.assertNotIn("clusters", first)
        self.assertEqual((second["clusters"], second["n"], second["difference"]), (2, 2, first["difference"]))
        out = io.StringIO()
        with patch.object(sys, "argv", ["cli", "retrieval-rescore", str(self.root / "retrieval-DK1"), str(self.root / "retrieval-DK2")]), redirect_stdout(out):
            self.assertEqual(cli.main(), 0)
        self.assertEqual(out.getvalue().count("legacy mismatches 0"), 2)
        self.assertTrue((self.root / "retrieval-DK2" / "metrics-evidence.json").exists())

    def test_answer_metrics_report_failed_answers_and_match_the_run_score(self):
        for name, provider in (("DK1", StandIn()), ("DK2", StandIn(fail=["Tiền lương"]))):
            answer_run(self.root / f"retrieval-{name}", self.questions, self.config, provider, self.root / f"answers-{name}")
        scores = question_scores(self.root / "answers-DK2", self.questions)
        self.assertEqual(scores["q2"]["error"], "timeout")
        self.assertIsNone(scores["q2"]["answered"])
        metrics = score(self.root / "answers-DK1", self.questions)
        per = question_scores(self.root / "answers-DK1", self.questions)
        precision = [s["citation_gold_precision"] for s in per.values() if s["citation_gold_precision"] is not None]
        self.assertAlmostEqual(sum(precision) / len(precision), metrics["citation_gold_precision"])
        self.assertEqual([s["refusal_when_expected"] for s in per.values() if s["refusal_when_expected"] is not None], [1.0])
        output = self.root / "answered.json"
        code, printed = self.cli("--metric", "answer.answered", "--questions", str(self.questions), "--runs",
                                 f"DK1={self.root / 'answers-DK1'}", f"DK2={self.root / 'answers-DK2'}", "--pairs", "DK1:DK2",
                                 "--rounds", "200", "--output", str(output))
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["comparisons"][0]["questions"]["unscored"], {"DK1": [], "DK2": ["q2"]})
        self.assertIn("1 question(s) unscored in DK2", printed)
        with self.assertRaises(SystemExit):
            self.cli("--metric", "answer.answered", "--runs", f"DK1={self.root / 'answers-DK1'}", "--pairs", "DK1:DK1",
                     "--output", str(self.root / "no-questions.json"))

    def test_grades_are_read_per_item_through_the_key_with_grading_noise(self):
        for name in ("DK1", "DK2"):
            answer_run(self.root / f"retrieval-{name}", self.questions, self.config, StandIn(), self.root / f"answers-{name}")
        sheet, key = self.root / "sheet.csv", self.root / "key.json"
        answer_grading.make_sheet([self.root / "answers-DK1", self.root / "answers-DK2"], self.questions, sheet, key)
        items = json.loads(key.read_text(encoding="utf-8"))["items"]

        def fill(path, grade):
            rows = answer_grading.read_sheet(sheet)
            for row in rows:
                if row["row"] == "answer":
                    row["correctness"] = str(grade(items[row["item_id"]]))
                else:
                    row["supported"], row["citation_correct"] = "2", "1"
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=answer_grading.COLUMNS)
                writer.writeheader()
                writer.writerows(rows)

        first, second = self.root / "grader-1.csv", self.root / "grader-2.csv"
        fill(first, lambda item: 2 if item["condition"] == "DK2" else 1)
        fill(second, lambda item: 2 if item["condition"] == "DK2" or item["question_id"] == "q1" else 1)
        report = stats.compare_runs("grades.correctness", {"DK1": self.root / "answers-DK1", "DK2": self.root / "answers-DK2"}, [("DK1", "DK2")],
                                    regrade=second, sheet=first, key=key, rounds=200)
        self.assertEqual((report["comparisons"][0]["difference"], report["comparisons"][0]["wins"]), (1.0, 3))
        grading = report["noise"]["grading"]
        self.assertEqual((grading["by_label"]["DK1"]["changed"], grading["by_label"]["DK2"]["changed"], grading["pooled"]["n"]), (1, 0, 6))
        self.assertEqual(report["inputs"]["regrade"]["path"], second.as_posix())
        with self.assertRaisesRegex(ValueError, "not in the key"):
            stats.compare_runs("grades.correctness", {"DK1": self.root / "retrieval-DK1"}, [("DK1", "DK1")], sheet=first, key=key, rounds=10)
        with self.assertRaisesRegex(ValueError, "grades.<name>"):
            stats.parse_metric("correctness")

    def outcome_questions(self):
        questions = json.loads(self.questions.read_text(encoding="utf-8"))
        for q in questions["questions"]:
            q |= {"issues": ["Vấn đề một", "Vấn đề hai"], "reference_outcome": "Tòa chấp nhận yêu cầu."}
        path = self.root / "questions-outcome.json"
        path.write_text(json.dumps(questions, ensure_ascii=False), encoding="utf-8")
        return path

    def test_failed_answers_stay_off_the_sheet_but_are_recorded_and_counted(self):
        answer_run(self.root / "retrieval-DK1", self.questions, self.config, StandIn(), self.root / "answers-DK1")
        answer_run(self.root / "retrieval-DK2", self.questions, self.config, StandIn(fail=["Tiền lương"]), self.root / "answers-DK2")
        sheet, key = self.root / "sheet.csv", self.root / "key.json"
        made = answer_grading.make_sheet([self.root / "answers-DK1", self.root / "answers-DK2"], self.questions, sheet, key)
        self.assertEqual((made["items"], made["failed_answers"], made["answers_not_in_questions"]), (5, 1, 0))
        key_file = json.loads(key.read_text(encoding="utf-8"))
        (failed_id, failed), = key_file["failed"].items()
        self.assertEqual((failed["condition"], failed["question_id"], failed["error"]), ("DK2", "q2", "timeout"))
        self.assertNotIn(failed_id, {row["item_id"] for row in answer_grading.read_sheet(sheet)}, "graders never get a failed answer")
        report = answer_grading.score_sheet(sheet, key)
        self.assertEqual((report["by_condition"]["DK2"]["failed_answers"], report["by_condition"]["DK1"]["failed_answers"],
                          report["failed_answers"], report["by_condition"]["DK2"]["items"]), (1, 0, 1, 2))
        judged = self.root / "judged.csv"
        answer_grading.judge_sheet(sheet, StandIn(), judged)
        rows = [r for r in answer_grading.read_sheet(judged) if r["item_id"] != next(iter(key_file["items"]))]
        partial = self.root / "partial.csv"
        with partial.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=answer_grading.COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        agreement = answer_grading.agreement(judged, partial, key)
        self.assertEqual((len(agreement["unpaired_items"]["first_only"]), agreement["unpaired_items"]["second_only"], agreement["failed_answers"]),
                         (1, [], {"DK2": 1}))
        old = self.root / "old-key.json"  # A key made before failures were recorded still loads; the count is unknown.
        old.write_text(json.dumps({k: v for k, v in key_file.items() if k not in ("failed", "not_in_questions")}), encoding="utf-8")
        report = answer_grading.score_sheet(sheet, old)
        self.assertEqual((report["failed_answers"], report["by_condition"]["DK2"]["failed_answers"], report["answers_not_in_questions"]), (None, None, None))
        self.assertIsNone(answer_grading.agreement(judged, partial, old)["failed_answers"])

    def test_answers_to_questions_outside_the_file_are_counted(self):
        answer_run(self.root / "retrieval-DK1", self.questions, self.config, StandIn(), self.root / "answers-DK1")
        fewer = self.root / "fewer.json"
        fewer.write_text(json.dumps({"questions": QUESTIONS["questions"][:2]}, ensure_ascii=False), encoding="utf-8")
        metrics = score(self.root / "answers-DK1", fewer)
        self.assertEqual((metrics["questions"], metrics["answers_not_in_questions"], metrics["answers_not_in_questions_ids"]), (2, 1, ["q3"]))
        made = answer_grading.make_sheet([self.root / "answers-DK1"], fewer, self.root / "sheet.csv", self.root / "key.json")
        self.assertEqual(made["answers_not_in_questions"], 1)
        report = stats.compare_runs("answer.answered", {"DK1": self.root / "answers-DK1"}, [("DK1", "DK1")], questions=fewer, rounds=10)
        self.assertIn("runs DK1: 1 answer(s) to questions not in --questions, left out", report["warnings"])

    def test_outcome_score_keeps_two_runs_of_one_condition_apart_and_lists_unpaired_questions(self):
        questions = self.outcome_questions()
        answer_run(self.root / "retrieval-DK1", self.questions, self.config, StandIn(), self.root / "answers-DK1")
        answer_run(self.root / "retrieval-DK1", self.questions, self.config, StandIn(), self.root / "answers-DK1-again")
        answer_run(self.root / "retrieval-DK2", self.questions, self.config, StandIn(fail=["Tiền lương"]), self.root / "answers-DK2")
        runs = [self.root / name for name in ("answers-DK1", "answers-DK1-again", "answers-DK2")]
        sheet, key = self.root / "sheet.csv", self.root / "key.json"
        answer_grading.make_sheet(runs, questions, sheet, key)
        counts = outcome_judge.judge(sheet, key, questions, OutcomeJudge(), self.root / "judge")
        self.assertEqual((counts["judged"], counts["failed_answers"]), (8, 1))
        report = outcome_judge.score(self.root / "judge", sheet, key)
        block = report["by_model"]["stand-in"]
        self.assertEqual(set(block["conditions"]), {"DK1:answers-DK1", "DK1:answers-DK1-again", "DK2"})
        self.assertEqual((block["conditions"]["DK2"]["failed_answers"], block["conditions"]["DK2"]["n"], report["failed_answers"]), (1, 2, 1))
        self.assertEqual(set(block["paired"]), {"DK2-DK1:answers-DK1", "DK2-DK1:answers-DK1-again"})
        self.assertEqual(block["unpaired"]["DK2-DK1:answers-DK1"], {"count": 1, "only_in": {"DK1:answers-DK1": ["q2"], "DK2": []}})
        self.assertEqual(block["paired"]["DK2-DK1:answers-DK1"]["correctness"]["n"], 2)

        single = outcome_judge.score(self.root / "judge", sheet, key, pairs=[("DK1", "DK2")])
        self.assertEqual(len(single["by_model"]["stand-in"]["paired"]), 2)
        output = self.root / "judge-report.json"
        code, printed = self.cli("--metric", "judge.correctness", "--runs", f"DK1={runs[0]}", f"DK2={runs[2]}", "--repeat", f"DK1={runs[1]}",
                                 "--pairs", "DK1:DK2", "--sheet", str(sheet), "--key", str(key), "--judge", str(self.root / "judge"),
                                 "--rounds", "200", "--output", str(output))
        self.assertEqual(code, 0)
        report = json.loads(output.read_text(encoding="utf-8"))
        comparison = report["comparisons"][0]
        self.assertEqual((comparison["n"], comparison["difference"], comparison["questions"]["unscored"]), (2, 0.0, {"DK1": [], "DK2": ["q2"]}),
                         "the failed answer is unscored, not missing")
        self.assertEqual(report["noise"]["generation"]["by_label"]["DK1"]["changed"], 0)
        self.assertEqual(report["inputs"]["runs"]["DK2"]["failed_answers"], 1)
        self.assertIn("1 question(s) unscored in DK2", printed)


if __name__ == "__main__":
    unittest.main()
