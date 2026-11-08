"""Fairness preflight of a DK1-DK4 comparison. Synthetic statute, stand-in models."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_answer_run import StandIn as AnswerStandIn
from test_kb_run import LAW, StandIn
from test_retrieval_run import bundle
from legal_ai.evaluation import kb_run
from legal_ai.evaluation.answer_run import run as answer_run
from legal_ai.evaluation.preflight import check
from legal_ai.evaluation.retrieval_run import run as retrieval_run

CONDITIONS = {"DK1": {"representation": "fixed_chunks", "chunk_tokens": 20, "overlap_tokens": 4},
              "DK2": {"representation": "structural_units", "max_tokens": 384},
              "DK3": {"representation": "llm_kb_raw"}, "DK4": {"representation": "llm_kb_validated"}}


class PreflightTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        _, self.units, _ = bundle(self.root / "bundle", {"syn": LAW})
        self.kb = self.root / "kb"
        kb_run.start(self.root / "bundle", self.kb, "stand-in", "medium")
        kb_run.extract(self.units, StandIn(), self.kb)
        kb_run.materialize(self.units, self.kb)
        self.questions = self.root / "q.json"
        self.questions.write_text(json.dumps({"questions": [
            {"question_id": "q1", "question": "Ai phải thông báo kết quả thử việc?", "split": "dev", "expected_status": "answer",
             "relevant_unit_ids": ["syn/article-1/clause-1"]}]}, ensure_ascii=False), encoding="utf-8")

    def shared(self, name="shared", top_k=1):
        path = self.root / f"{name}.json"
        path.write_text(json.dumps({"top_k": top_k, "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75,
                                                                  "recall_k": [1]}}), encoding="utf-8")
        return path

    def retrieval(self, condition, shared, kb=None, tag=""):
        path = self.root / f"{condition}{tag}.json"
        body = {"condition": condition} | CONDITIONS[condition]
        if condition in ("DK3", "DK4"):
            body["kb_run"] = (kb or self.kb).as_posix()
        path.write_text(json.dumps(body), encoding="utf-8")
        output = self.root / f"run-{condition}{tag}"
        retrieval_run(self.root / "bundle", self.questions, path, shared, output)
        return output

    def test_four_matching_conditions_pass_and_answer_runs_are_checked(self):
        shared = self.shared()
        runs = [self.retrieval(c, shared) for c in CONDITIONS]
        report = check(runs)
        self.assertEqual(report["status"], "pass", [c for c in report["checks"] if c["status"] != "pass"])
        names = {c["check"] for c in report["checks"]}
        self.assertTrue({"index isolation", "DK4 is a subset of DK3", "same retrieval settings"} <= names)

        config = self.root / "answer.json"
        config.write_text(json.dumps({"prompt": "answer-v1.md", "top_k": 1, "context_token_budget": 500}), encoding="utf-8")
        answers = []
        for run in runs:
            output = self.root / f"answers-{run.name}"
            answer_run(run, self.questions, config, AnswerStandIn(), output)
            answers.append(output)
        self.assertEqual(check(runs, answers)["status"], "pass")
        other = self.root / "answer-other.json"
        other.write_text(json.dumps({"prompt": "answer-v1.md", "top_k": 1, "context_token_budget": 900}), encoding="utf-8")
        answer_run(runs[0], self.questions, other, AnswerStandIn(), self.root / "answers-odd")
        report = check(runs, answers[1:] + [self.root / "answers-odd"])
        failed = {c["check"] for c in report["checks"] if c["status"] == "fail"}
        self.assertEqual(failed, {"same answer settings"})

    def test_differences_between_conditions_fail(self):
        shared = self.shared()
        dk1 = self.retrieval("DK1", shared)
        dk2 = self.retrieval("DK2", self.shared("other", top_k=3))
        report = check([dk1, dk2])
        statuses = {c["check"]: c["status"] for c in report["checks"]}
        self.assertEqual((statuses["same retrieval settings"], statuses["all four conditions present"], report["status"]), ("fail", "warn", "fail"))

        second_kb = self.root / "kb-2"
        kb_run.start(self.root / "bundle", second_kb, "stand-in", "medium")
        kb_run.extract(self.units, StandIn(), second_kb)
        kb_run.materialize(self.units, second_kb)
        report = check([self.retrieval("DK3", shared), self.retrieval("DK4", shared, kb=second_kb, tag="-b")])
        self.assertIn({"check": "DK3 and DK4 from one extraction run", "status": "fail"},
                      [{k: c[k] for k in ("check", "status")} for c in report["checks"]])

        tampered = self.retrieval("DK2", shared, tag="-t")
        records = (tampered / "records.jsonl").read_text(encoding="utf-8").replace('"condition":"DK2"', '"condition":"DK1"', 1)
        (tampered / "records.jsonl").write_text(records, encoding="utf-8")
        statuses = {c["check"]: c["status"] for c in check([tampered])["checks"]}
        self.assertEqual(statuses["index isolation"], "fail")


if __name__ == "__main__":
    unittest.main()
