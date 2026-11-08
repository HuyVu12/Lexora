"""Cited answers, the citation gate, automatic scores, the blinded grading sheet and the judge. Synthetic data, stand-in model."""

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_retrieval_run import SYNTHETIC, bundle
from legal_ai.common.io import read_jsonl
from legal_ai.evaluation import answer_grading
from legal_ai.evaluation.answer_run import gate, pack, run, score
from legal_ai.evaluation.retrieval_run import run as retrieval_run
from legal_ai.providers.pilot import ProviderError

QUESTIONS = {"questions": [
    {"question_id": "q1", "question": "Bên A phải báo trước bao nhiêu ngày với hợp đồng không xác định thời hạn?", "split": "dev",
     "expected_status": "answer", "relevant_unit_ids": ["syn-a/chapter-i/article-1/clause-1"]},
    {"question_id": "q2", "question": "Tiền lương thử nghiệm ít nhất bằng bao nhiêu phần trăm?", "split": "dev",
     "expected_status": "answer", "relevant_unit_ids": ["syn-a/chapter-i/article-2/clause-1"]},
    {"question_id": "q3", "question": "Thuế thu nhập doanh nghiệp là bao nhiêu?", "split": "held_out", "expected_status": "refuse", "relevant_unit_ids": []},
]}


class StandIn:
    model, effort = "stand-in", "medium"

    def __init__(self, fail=()):
        self.prompts, self.fail = [], set(fail)

    def structured(self, system, prompt, schema, purpose="structured"):
        request = json.loads(prompt)
        self.prompts.append(request)
        if purpose == "judge":
            return {"output": {"statements": [{"supported": 2, "citation_correct": True} for _ in request["statements"]],
                               "correctness": 2 if request["statements"] else 1, "refusal_appropriate": None if request["statements"] else True}}
        ids = schema["properties"]["statements"]["items"]["properties"]["evidence_ids"]["items"]["enum"]
        if any(word in request["question"] for word in self.fail):
            raise ProviderError("timeout")
        if "Thuế" in request["question"]:
            return {"output": {"status": "insufficient_evidence", "statements": [], "limitations": []}}
        return {"output": {"status": "answered", "limitations": [], "statements": [
            {"text": "Theo đoạn đầu tiên.", "evidence_ids": [ids[0]]},
            {"text": "Một ý không có trích dẫn.", "evidence_ids": []}]}, "cost_usd": 0.02, "model": "stand-in"}


class AnswerRunTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        bundle(self.root / "bundle", {"syn-a": SYNTHETIC})
        self.questions = self.root / "questions.json"
        self.questions.write_text(json.dumps(QUESTIONS, ensure_ascii=False), encoding="utf-8")
        shared = self.root / "shared.json"
        shared.write_text(json.dumps({"top_k": 3, "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75, "recall_k": [1, 3]}}), encoding="utf-8")
        self.config = self.root / "answer.json"
        self.config.write_text(json.dumps({"prompt": "answer-v1.md", "top_k": 3, "context_token_budget": 200}), encoding="utf-8")
        self.retrieval = {}
        for name, condition in (("DK1", {"representation": "fixed_chunks", "chunk_tokens": 40, "overlap_tokens": 8}),
                                ("DK2", {"representation": "structural_units", "max_tokens": 384})):
            path = self.root / f"{name}.json"
            path.write_text(json.dumps({"condition": name} | condition), encoding="utf-8")
            retrieval_run(self.root / "bundle", self.questions, path, shared, self.root / f"retrieval-{name}")
            self.retrieval[name] = self.root / f"retrieval-{name}"

    def test_a_9router_chat_model_answers_through_the_structured_adapter(self):
        from legal_ai.providers.router import ChatStructured

        class Chat:
            model, calls, max_calls = "ollama/stand-in", 0, 10

            def __init__(self):
                self.systems = []

            def complete(self, system, user, max_tokens=900):
                self.calls += 1
                self.systems.append(system)
                request = json.loads(user)
                if "Thuế" in request["question"]:
                    return {"content": "Không đủ căn cứ, không phải JSON."}
                first = request["evidence"][0]["id"]
                body = {"status": "answered", "statements": [{"text": "Theo đoạn đầu.", "evidence_ids": [first, "E99"]}, "một chuỗi trần", {"text": "Không trích dẫn"}]}
                return {"content": "Đây là kết quả:\n```json\n" + json.dumps(body, ensure_ascii=False) + "\n```", "usage": {"prompt_tokens": 50, "completion_tokens": 20}}

        chat = Chat()
        provider = ChatStructured(chat, max_tokens=2000)
        output = self.root / "answers-router"
        counts = run(self.retrieval["DK2"], self.questions, self.config, provider, output)
        self.assertEqual((counts["answered"], counts["failed"]), (2, 1), "unparseable chat output is a failed call, not a crash")
        self.assertIn("JSON Schema", chat.systems[0])
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual((manifest["provider"], manifest["model"], manifest["effort"]), ("9router", "ollama/stand-in", "temperature-0"))
        rows = {r["question_id"]: r for r in read_jsonl(output / "answers.jsonl")}
        self.assertEqual(rows["q1"]["statements"][0]["evidence_ids"], ["E01"], "evidence IDs outside the bundle are dropped")
        self.assertEqual(rows["q1"]["gate"]["uncited_removed"], 2, "a bare string and an uncited statement are both removed")
        self.assertIn("```json", rows["q1"]["raw_content"])
        self.assertEqual(rows["q3"]["error"], "invalid_output")

    def test_gate_removes_uncited_statements_and_downgrades_empty_answers(self):
        blocks = [{"id": "E01", "record_id": "r1", "unit_ids": ["u1"]}]
        kept = gate({"status": "answered", "statements": [{"text": "A", "evidence_ids": ["E01", "E01"]}, {"text": "B", "evidence_ids": []}]}, blocks)
        self.assertEqual((kept["status"], kept["statements"][0]["record_ids"], kept["gate"]["uncited_removed"]), ("answered", ["r1"], 1))
        empty = gate({"status": "partial", "statements": [{"text": "B", "evidence_ids": ["E09"]}]}, blocks)
        self.assertEqual((empty["status"], empty["gate"]["downgraded_to_insufficient"]), ("insufficient_evidence", True))

    def test_pack_keeps_rank_order_within_the_budget(self):
        records = {r["record_id"]: r for r in read_jsonl(self.retrieval["DK2"] / "records.jsonl")}
        ranked = read_jsonl(self.retrieval["DK2"] / "predictions.jsonl")[0]["ranked"]
        blocks = pack(ranked, records, 3, 25)
        self.assertEqual(blocks[0]["record_id"], ranked[0]["record_id"])
        self.assertTrue(len(blocks) == 1 or sum(b["token_count"] for b in blocks) <= 25)
        self.assertEqual([b["id"] for b in pack(ranked, records, 3, 10_000)], ["E01", "E02", "E03"])

    def test_answer_run_resumes_scores_and_pools_into_a_blinded_sheet(self):
        output = self.root / "answers-DK2"
        counts = run(self.retrieval["DK2"], self.questions, self.config, StandIn(fail=["Tiền lương"]), output)
        self.assertEqual((counts["answered"], counts["failed"]), (2, 1))
        provider = StandIn()
        counts = run(self.retrieval["DK2"], self.questions, self.config, provider, output)
        self.assertEqual((counts["already_done"], counts["answered"], len(provider.prompts)), (2, 1, 1))
        with self.assertRaisesRegex(ValueError, "other inputs"):
            run(self.retrieval["DK2"], self.questions, self.config, StandIn(), output, split="dev")
        metrics = score(output, self.questions)
        self.assertEqual((metrics["questions"], metrics["errors"], metrics["refusal_rate_when_expected"], metrics["false_refusal_rate"]), (3, 0, 1.0, 0.0))
        self.assertEqual(metrics["uncited_statements_removed"], 2)
        self.assertIsNotNone(metrics["citation_gold_precision"])

        run(self.retrieval["DK1"], self.questions, self.config, StandIn(), self.root / "answers-DK1")
        sheet, key = self.root / "sheet.csv", self.root / "key.json"
        made = answer_grading.make_sheet([output, self.root / "answers-DK1"], self.questions, sheet, key)
        self.assertEqual(made["items"], 6)
        text = sheet.read_text(encoding="utf-8-sig")
        self.assertNotIn("DK1", text)
        self.assertNotIn("DK2", text)
        self.assertIn("[syn-a/chapter-i/article-1/clause-1]", text, "graders see canonical unit text")

        rows = answer_grading.read_sheet(sheet)
        for row in rows:
            if row["row"] == "answer":
                row["correctness"] = "2" if row["status"] == "answered" else "1"
                row["refusal_appropriate"] = "1" if row["status"] != "answered" else ""
            else:
                row["supported"], row["citation_correct"] = "2", "1"
        filled = self.root / "filled.csv"
        with filled.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=answer_grading.COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        report = answer_grading.score_sheet(filled, key)["by_condition"]
        self.assertEqual(set(report), {"DK1", "DK2"})
        self.assertEqual(report["DK2"]["citation_support"], {"value": 1.0, "n": 2})
        self.assertEqual(report["DK2"]["refusal_appropriate"], {"value": 1.0, "n": 1})

        judged = self.root / "judge.csv"
        self.assertEqual(answer_grading.judge_sheet(sheet, StandIn(), judged)["failures"], 0)
        agreement = answer_grading.agreement(filled, judged)
        self.assertEqual(agreement["supported"]["kappa"], 1.0)
        rows[0]["correctness"] = "7"
        with filled.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=answer_grading.COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, "grade '7'"):
            answer_grading.score_sheet(filled, key)


if __name__ == "__main__":
    unittest.main()
