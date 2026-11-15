"""Model proposals for question sets with a stand-in provider: candidates, schemas, stored calls and drafts."""

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.providers.claude_code import ProviderError
from legal_ai.research import proposals
from legal_ai.research.corpus import CorpusStore
from legal_ai.research.questions import QuestionStore

LAW = ("Điều 1. Thời hạn báo trước\n1. Bên A phải báo trước 30 ngày.\n2. Bên B phải báo trước 45 ngày.\n"
       "Điều 2. Tiền lương giả định\nTiền lương thử nghiệm ít nhất bằng 85% mức lương chính thức.\n")


class StandIn:
    """Plays a structured provider: records each call and answers with the next scripted output."""

    def __init__(self, outputs):
        self.outputs, self.seen, self.ledger = list(outputs), [], []

    def structured(self, system, prompt, schema, purpose="structured"):
        self.seen.append({"system": system, "prompt": prompt, "schema": schema, "purpose": purpose})
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            self.ledger.append({"purpose": purpose, "status": "error", "code": output.code})
            raise output
        self.ledger.append({"purpose": purpose, "status": "ok", "output": output, "model": "stand-in"})
        return {"output": output, "usage": {}, "cost_usd": 0, "model": "stand-in"}


class ProposalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        path = Path(self.temp.name) / "w.sqlite"
        self.corpora = CorpusStore(path)
        corpus = self.corpora.create("C", "", "vu")
        self.corpora.add_file(corpus["id"], "luat.txt", LAW.encode("utf-8"), "vu")
        self.version = self.corpora.freeze(corpus["id"], "", "vu")
        self.store = QuestionStore(path, self.corpora)
        self.set = self.store.create("B", self.version["id"], "", "vu")

    def test_label_proposal_sees_only_candidates_and_is_stored_with_its_call(self):
        question = self.store.add_question(self.set["id"], "Bên A báo trước mấy ngày?", "vu")
        found = proposals.candidates(self.corpora, self.version["id"], question["text"])
        self.assertEqual(found[0]["unit_id"], "luat/article-1/clause-1")
        self.assertIn("Điều 1 > Khoản 1", found[0]["path"])
        provider = StandIn([{"question_type": "lookup", "expected_status": "answer", "relevant_unit_ids": ["luat/article-1/clause-1"], "rationale": "Khoản 1: 30 ngày"}])
        proposal = proposals.propose_label(provider, self.store, self.set["id"], question["id"])
        sent = provider.seen[0]
        self.assertEqual(sorted(sent["schema"]["properties"]["relevant_unit_ids"]["items"]["enum"]), sorted(c["unit_id"] for c in found))
        self.assertIn("Bên A phải báo trước 30 ngày.", sent["prompt"])
        self.assertTrue(sent["system"].startswith("Bạn hỗ trợ nhóm nghiên cứu gán nhãn"))
        self.assertEqual(proposal["fields"]["relevant_unit_ids"], ["luat/article-1/clause-1"])
        calls = self.store.calls(self.set["id"])
        self.assertEqual((len(calls), calls[0]["purpose"], calls[0]["prompt_file"]), (1, "question-label", "question-label-v1.md"))
        self.assertNotIn("output", calls[0])

    def test_candidates_carry_the_clause_whose_lead_sentence_holds_the_rule(self):
        law = ("Điều 3. Thanh toán khi chấm dứt\n1. Trong thời hạn 14 ngày làm việc, hai bên thanh toán đủ, trừ trường hợp sau đây có thể kéo dài nhưng không quá 30 ngày:\n"
               "a) Doanh nghiệp giải thể;\nb) Do thiên tai, hỏa hoạn.\n2. Người sử dụng lao động trả chi phí.\n")
        corpus = self.corpora.create("D", "", "vu")
        self.corpora.add_file(corpus["id"], "luat2.txt", law.encode("utf-8"), "vu")
        version = self.corpora.freeze(corpus["id"], "", "vu")
        found = {c["unit_id"]: c for c in proposals.candidates(self.corpora, version["id"], "kéo dài thanh toán do thiên tai")}
        point = found["luat2/article-3/clause-1/point-b"]
        self.assertEqual([p["unit_id"] for p in point["parents"]], ["luat2/article-3/clause-1"])
        self.assertTrue(point["parents"][0]["text"].startswith("1. Trong thời hạn 14 ngày"))
        self.assertEqual(point["parents"][0]["path"], "Điều 3 > Khoản 1")
        self.assertEqual(found["luat2/article-3/clause-2"]["parents"], [], "an Article with only its heading is not offered")
        store = QuestionStore(Path(self.temp.name) / "w.sqlite", self.corpora)
        qset = store.create("E", version["id"], "", "vu")
        question = store.add_question(qset["id"], "Thanh toán trong bao lâu?", "vu")
        store.set_mode(qset["id"], "vu", False)
        saved = store.save_label(qset["id"], question["id"], "vu", "Vũ", {"question_type": "lookup", "expected_status": "answer",
                                                                               "relevant_unit_ids": ["luat2/article-3/clause-1"]})
        self.assertEqual(saved["fields"]["relevant_unit_ids"], ["luat2/article-3/clause-1"])

    def test_rows_name_their_document_and_statute_order(self):
        other = ("Điều 1. Thời hạn khác\n1. Bên A phải báo trước 15 ngày, trừ các trường hợp sau đây:\n"
                 "a) Bên A ốm đau;\nb) Bên A báo trước bằng văn bản.\n")
        corpus = self.corpora.create("Hai văn bản", "", "vu")
        self.corpora.add_file(corpus["id"], "luat.txt", LAW.encode("utf-8"), "vu", title="Bộ luật Lao động số 45/2019/QH14")
        self.corpora.add_file(corpus["id"], "nd.txt", other.encode("utf-8"), "vu",
                              title="Nghị định số 145/2020/NĐ-CP Quy định chi tiết một số điều")
        version = self.corpora.freeze(corpus["id"], "", "vu")
        found = {c["unit_id"]: c for c in proposals.candidates(self.corpora, version["id"], "Bên A báo trước")}
        clash = (found["luat/article-1/clause-1"], found["nd/article-1/clause-1/point-b"]["parents"][0])
        self.assertEqual([u["path"] for u in clash], ["Điều 1 > Khoản 1", "Điều 1 > Khoản 1"], "same path in two documents")
        self.assertEqual([u["document"] for u in clash], ["Bộ luật Lao động số 45/2019/QH14", "Nghị định số 145/2020/NĐ-CP"])
        self.assertEqual(clash[1]["document_title"], "Nghị định số 145/2020/NĐ-CP Quy định chi tiết một số điều")
        points = [found[f"nd/article-1/clause-1/point-{p}"]["order"] for p in "ab"]
        self.assertLess(points[0], points[1], "order follows the statute, not the search rank")
        refs = proposals.unit_refs(self.corpora, version["id"], ["nd/article-1/clause-1", "missing/unit", "luat/article-2"])
        self.assertEqual([(r["unit_id"], r["document"], r["path"]) for r in refs],
                         [("nd/article-1/clause-1", "Nghị định số 145/2020/NĐ-CP", "Điều 1 > Khoản 1"),
                          ("luat/article-2", "Bộ luật Lao động số 45/2019/QH14", "Điều 2")])
        self.assertTrue(refs[0]["text"].startswith("1. Bên A phải báo trước 15 ngày"))
        self.assertEqual(proposals.short_title("Luật Việc làm số 74/2025/QH15"), "Luật Việc làm số 74/2025/QH15")
        self.assertEqual(proposals.short_title("Quy định nội bộ"), "Quy định nội bộ")

    def test_failed_calls_are_logged_and_raised(self):
        question = self.store.add_question(self.set["id"], "Lương thử nghiệm bao nhiêu?", "vu")
        with self.assertRaises(ProviderError):
            proposals.propose_label(StandIn([ProviderError("timeout")]), self.store, self.set["id"], question["id"])
        self.assertEqual([c["status"] for c in self.store.calls(self.set["id"])], ["error"])

    def test_drafts_become_model_questions_with_paraphrase_families(self):
        provider = StandIn([{"questions": [
            {"text": "Công ty muốn cho nhân viên thử việc thì trả lương tối thiểu bao nhiêu?", "question_type": "lookup",
             "relevant_unit_ids": ["luat/article-2"], "paraphrases": ["Lương thử việc thấp nhất là bao nhiêu phần trăm?"], "rationale": "Điều 2"}]}])
        with self.assertRaisesRegex(ValueError, "phiên bản corpus"):
            proposals.draft_questions(provider, self.store, self.set["id"], ["luat/article-9"])
        draft = proposals.draft_questions(provider, self.store, self.set["id"], ["luat/article-2"], count=2)
        self.assertEqual(provider.seen[0]["schema"]["properties"]["questions"]["maxItems"], 2)
        self.assertEqual(draft["unit_ids"], ["luat/article-2"])
        added = self.store.accept_draft(self.set["id"], draft["id"], 0,
                                        ["Công ty muốn cho nhân viên thử việc thì trả lương tối thiểu bao nhiêu?", "Lương thử việc tối thiểu là bao nhiêu %?"], "vu")
        self.assertEqual(len({q["family_id"] for q in added}), 1)
        self.assertEqual([q["origin_detail"]["edited"] for q in added], [False, True])
        self.assertEqual({q["origin"] for q in added}, {"model"})
        self.store.set_mode(self.set["id"], "vu", True)
        item = self.store.workspace(self.set["id"], "vu")["items"][0]
        self.assertEqual(item["proposal"]["fields"]["relevant_unit_ids"], ["luat/article-2"])
        with self.assertRaisesRegex(ValueError, "đã được thêm"):
            self.store.accept_draft(self.set["id"], draft["id"], 0, ["x câu"], "vu")


if __name__ == "__main__":
    unittest.main()
