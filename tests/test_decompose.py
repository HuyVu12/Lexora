"""Issue decomposition shared by every condition: model output cleaning, resume, round-robin merge, retrieval and
answer runs reading the same subqueries. Synthetic statute, stand-in model."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_kb_records_graph import LAW
from test_retrieval_run import bundle
from legal_ai.common.io import read_jsonl, write_json
from legal_ai.evaluation import decompose
from legal_ai.evaluation.answer_run import run as answer_run
from legal_ai.evaluation.preflight import check
from legal_ai.evaluation.retrieval_run import run as retrieval_run
from legal_ai.providers.pilot import ProviderError


class Splitter:
    model, effort, provider = "stand-in", "temperature-0", "9router"

    def __init__(self, fail=()):
        self.calls, self.fail = [], set(fail)

    def structured(self, system, prompt, schema, purpose="structured"):
        question = json.loads(prompt)["question"]
        self.calls.append(question)
        if any(word in question for word in self.fail):
            raise ProviderError("timeout")
        if "bồi thường" in question:
            return {"output": {"issues": [{"issue": "Chấm dứt thử nghiệm", "query": "hợp đồng thử nghiệm chấm dứt"},
                                          {"issue": "Bồi thường", "query": "bên vi phạm phải bồi thường"},
                                          {"issue": "", "query": "rỗng bị bỏ"}]}, "model": "stand-in"}
        return {"output": {"issues": [{"issue": "Thời gian thử nghiệm", "query": "không quá 60 ngày"}]}, "model": "stand-in"}


class Answerer:
    model, effort, provider = "stand-in", "temperature-0", "9router"

    def __init__(self):
        self.requests = []

    def structured(self, system, prompt, schema, purpose="structured"):
        self.requests.append(json.loads(prompt))
        return {"output": {"status": "insufficient_evidence", "statements": [], "limitations": []}, "model": "stand-in"}


class DecomposeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        bundle(self.root / "bundle", {"syn": LAW})
        self.questions = self.root / "q.json"
        write_json(self.questions, {"questions": [
            {"question_id": "q1", "question": "Thử nghiệm xong thì sao, có phải bồi thường không?", "split": "dev", "expected_status": "answer",
             "relevant_unit_ids": ["syn/chapter-i/article-2/clause-2", "syn/chapter-i/article-3/clause-1"]},
            {"question_id": "q2", "question": "Thử nghiệm tối đa bao lâu?", "split": "dev", "expected_status": "answer",
             "relevant_unit_ids": ["syn/chapter-i/article-1/clause-1"]}]})

    def test_clean_keeps_only_complete_issues(self):
        self.assertEqual(decompose.clean({"issues": [{"issue": " A ", "query": " a "}, {"issue": "B"}, "x"]}), [{"issue": "A", "query": "a"}])
        with self.assertRaisesRegex(ValueError, "no_issues"):
            decompose.clean({"issues": []})

    def test_run_resumes_and_refuses_other_inputs(self):
        out = self.root / "dec"
        self.assertEqual(decompose.run(self.questions, Splitter(fail=["tối đa"]), out)["failed"], 1)
        splitter = Splitter()
        counts = decompose.run(self.questions, splitter, out)
        self.assertEqual((counts["already_done"], counts["decomposed"], len(splitter.calls)), (1, 1, 1))
        rows, manifest = decompose.load(out, self.questions)
        self.assertEqual(len(rows["q1"]), 2, "the empty issue is dropped")
        self.assertEqual(manifest["prompt"], "decompose-v1.md")
        other = self.root / "other.json"
        write_json(other, {"questions": []})
        with self.assertRaisesRegex(ValueError, "another question file"):
            decompose.load(out, other)

    def test_merge_is_round_robin_without_duplicates(self):
        merged = decompose.merge([[(1, 9.0), (2, 8.0), (3, 7.0)], [(4, 5.0), (1, 4.0)], [(5, 1.0)]], depth=4)
        self.assertEqual([i for i, _ in merged], [1, 4, 5, 2])

    def test_retrieval_and_answers_share_the_issues(self):
        dec = self.root / "dec"
        decompose.run(self.questions, Splitter(), dec)
        base = {"top_k": 2, "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75, "recall_k": [1, 2]}}
        plain, split = self.root / "plain.json", self.root / "split.json"
        write_json(plain, base)
        write_json(split, base | {"subqueries": dec.as_posix()})
        dk2 = self.root / "dk2.json"
        write_json(dk2, {"condition": "DK2", "representation": "structural_units", "max_tokens": 384})
        before = retrieval_run(self.root / "bundle", self.questions, dk2, plain, self.root / "r-plain")
        after = retrieval_run(self.root / "bundle", self.questions, dk2, split, self.root / "r-split")
        self.assertGreater(after["mean_complete"]["2"], before["mean_complete"]["2"], "the issue queries reach the second provision")
        manifest = json.loads((self.root / "r-split" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["subqueries"]["path"], dec.as_posix())
        status = {c["check"]: c["status"] for c in check([self.root / "r-plain", self.root / "r-split"])["checks"]}
        self.assertEqual(status["same retrieval settings"], "fail", "conditions must share the same decomposition")

        config = self.root / "answer.json"
        write_json(config, {"prompt": "answer-v2.md", "top_k": 2, "context_token_budget": 500})
        answerer = Answerer()
        answer_run(self.root / "r-split", self.questions, config, answerer, self.root / "a-split")
        self.assertEqual(answerer.requests[0]["issues"], ["Chấm dứt thử nghiệm", "Bồi thường"])
        self.assertEqual(len(read_jsonl(self.root / "a-split" / "answers.jsonl")), 2)


if __name__ == "__main__":
    unittest.main()
