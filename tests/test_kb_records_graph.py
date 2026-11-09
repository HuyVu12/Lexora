"""DK3/DK4 records with the source text kept, cross-reference graph expansion, token-budget recall and
character-level citation precision. Synthetic statute, not real law."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_retrieval_run import bundle
from legal_ai.common.io import digest, read_jsonl, write_json, write_jsonl
from legal_ai.evaluation.answer_run import char_precision
from legal_ai.evaluation.preflight import check
from legal_ai.evaluation.retrieval_run import run
from legal_ai.indexing.records import kb_unit_records, structural_records
from legal_ai.retrieval.graph import expand, graph_edges, reference_edges

LAW = ("Chương I\nQUY ĐỊNH GIẢ ĐỊNH\n"
       "Điều 1. Thời gian thử nghiệm\n"
       "Thời gian thử nghiệm do hai bên thỏa thuận và bảo đảm điều kiện sau đây:\n"
       "1. Không quá 60 ngày đối với công việc cần trình độ cao đẳng.\n"
       "2. Không quá 6 ngày đối với công việc khác.\n"
       "Điều 2. Kết thúc thử nghiệm\n"
       "1. Bên A phải thông báo kết quả thử nghiệm cho bên B.\n"
       "2. Hợp đồng thử nghiệm chấm dứt theo quy định tại khoản 1 Điều 3.\n"
       "Điều 3. Bồi thường giả định\n"
       "1. Bên vi phạm phải bồi thường một khoản tiền tương ứng.\n"
       "Điều 4. Hội đồng giả định\n"
       "Hội đồng giả định họp mỗi quý một lần.\n")


def claim(units, unit_id, sentence, claim_id, **slots):
    unit = next(u for u in units if u["unit_id"] == unit_id)
    start = unit["source_start"] + unit["text"].index(sentence)
    base = {k: None for k in ("actor", "action", "object", "beneficiary", "recipient", "conditions", "exceptions", "deadlines", "quantities", "outcome")}
    return {"claim_id": claim_id, "unit_id": unit_id, "sentence": {"start": start, "end": start + len(sentence)},
            "modality": "obligation", "modality_cue": "phải", "slots": base | slots}


class KbRecordGraphTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.documents, self.units, self.texts = bundle(self.root / "bundle", {"syn": LAW})
        self.claims = [claim(self.units, "syn/chapter-i/article-1/clause-1", "Không quá 60 ngày", "kb:1", quantities="60 ngày"),
                       claim(self.units, "syn/chapter-i/article-2/clause-1", "Bên A phải thông báo kết quả thử nghiệm cho bên B", "kb:2",
                             actor="Bên A", action="thông báo kết quả thử nghiệm")]
        kb = self.root / "kb"
        write_json(kb / "manifest.json", {"units_sha256": digest((self.root / "bundle" / "units.jsonl").read_bytes())})
        write_jsonl(kb / "dk3.jsonl", self.claims)
        write_jsonl(kb / "dk4.jsonl", self.claims[:1])
        self.kb = kb
        self.questions = self.root / "q.json"
        write_json(self.questions, {"questions": [
            {"question_id": "q1", "question": "Hợp đồng thử nghiệm chấm dứt theo quy định nào?", "split": "dev", "expected_status": "answer",
             "relevant_unit_ids": ["syn/chapter-i/article-2/clause-2", "syn/chapter-i/article-3/clause-1"]}]})
        self.shared = self.root / "shared.json"
        write_json(self.shared, {"top_k": 2, "token_budgets": [40, 400],
                                 "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75, "recall_k": [1, 2]}})

    def condition(self, name, condition, **extra):
        path = self.root / f"{name}.json"
        body = {"condition": condition, "representation": {"DK2": "structural_units", "DK3": "llm_kb_raw", "DK4": "llm_kb_validated"}[condition],
                "max_tokens": 384} | extra
        if condition != "DK2":
            body["kb_run"] = self.kb.as_posix()
        write_json(path, body)
        return path

    def test_unit_records_keep_the_dk2_text_and_add_the_claims(self):
        dk2 = structural_records(self.documents, self.units, self.texts)
        dk3 = kb_unit_records("DK3", self.documents, self.units, self.texts, self.claims)
        self.assertEqual(len(dk3), len(dk2), "one record per DK2 record, including units without a claim")
        for before, after in zip(dk2, dk3):
            self.assertEqual((after["text"], after["unit_ids"], after["source_start"]), (before["text"], before["unit_ids"], before["source_start"]))
            self.assertTrue(after["index_text"].startswith(before["index_text"].rstrip("\n")))
            self.assertTrue(after["record_id"].startswith("dk3:"))
        with_claim = next(r for r in dk3 if r["claim_ids"] == ["kb:1"])
        self.assertIn("Không quá 60 ngày đối với công việc cần trình độ cao đẳng", with_claim["index_text"], "the source sentence stays")
        self.assertIn("Thời gian thử nghiệm do hai bên thỏa thuận", with_claim["index_text"], "and the lead text")
        self.assertIn("Định lượng: 60 ngày", with_claim["index_text"])
        self.assertGreater(with_claim["token_count"], next(r for r in dk2 if r["unit_ids"] == with_claim["unit_ids"])["token_count"])
        plain = next(r for r in dk3 if r["unit_ids"] == ["syn/chapter-i/article-4"])
        self.assertEqual(plain["claim_ids"], [])
        stray = dict(self.claims[0], unit_id="syn/chapter-i/article-4")
        with self.assertRaisesRegex(ValueError, "outside the corpus"):
            kb_unit_records("DK3", self.documents, self.units, self.texts, [stray])

    def test_compact_view_searches_full_claims_but_hands_over_one_line_each(self):
        full = kb_unit_records("DK3", self.documents, self.units, self.texts, self.claims)
        compact = kb_unit_records("DK3", self.documents, self.units, self.texts, self.claims, view="compact")
        a = next(r for r in full if r["claim_ids"] == ["kb:2"])
        b = next(r for r in compact if r["claim_ids"] == ["kb:2"])
        self.assertEqual(a["index_text"], b["index_text"], "search reads the same full claims")
        self.assertNotIn("generator_text", a)
        self.assertIn("[Quy phạm 1] nghĩa vụ · Chủ thể: Bên A", b["generator_text"])
        self.assertIn("Bên A phải thông báo kết quả thử nghiệm cho bên B", b["generator_text"], "the source text stays")
        self.assertLess(b["token_count"], a["token_count"])
        with self.assertRaisesRegex(ValueError, "claims_view"):
            kb_unit_records("DK3", self.documents, self.units, self.texts, self.claims, view="short")

    def test_reference_edges_and_expansion_keep_the_list_length(self):
        edges = reference_edges(self.units)
        self.assertEqual(edges, {"syn/chapter-i/article-2/clause-2": ["syn/chapter-i/article-3/clause-1"]})
        records = kb_unit_records("DK3", self.documents, self.units, self.texts, self.claims)
        index = {r["unit_ids"][0]: i for i, r in enumerate(records)}
        citing, cited = index["syn/chapter-i/article-2/clause-2"], index["syn/chapter-i/article-3/clause-1"]
        others = [i for i in range(len(records)) if i not in (citing, cited)]
        ranked = [(citing, 3.0)] + [(i, 2.0 - n * 0.1) for n, i in enumerate(others)] + [(cited, 0.1)]
        result = expand(ranked, records, edges, depth=3)
        self.assertEqual([i for i, _, _ in result], [citing, cited, others[0]], "the cited unit follows the citing one")
        self.assertEqual(result[1][2], citing)
        self.assertEqual(len(expand(ranked, records, edges, depth=len(records))), len(records), "no record appears twice")
        unmatched = [(i, s) for i, s in ranked if i != cited]
        self.assertNotIn(cited, [i for i, _, _ in expand(unmatched, records, edges, depth=3, require_match=True)],
                         "a neighbour the question does not match is not pulled in")
        self.assertIn(cited, [i for i, _, _ in expand(ranked, records, edges, depth=3, require_match=True)])
        back = graph_edges(self.units, ["referenced_by"])
        self.assertEqual(back, {"syn/chapter-i/article-3/clause-1": ["syn/chapter-i/article-2/clause-2"]})
        result = expand([(cited, 3.0)] + [(i, 1.0) for i in others] + [(citing, 0.1)], records, back, depth=2)
        self.assertEqual([i for i, _, _ in result], [cited, citing], "a found provision brings the provision that cites it")
        siblings = graph_edges(self.units, ["same_article"])
        self.assertEqual(siblings["syn/chapter-i/article-1/clause-1"], ["syn/chapter-i/article-1/clause-2"])
        self.assertNotIn("syn/chapter-i/article-4", siblings, "an Article without clauses has no sibling")
        self.assertEqual(graph_edges(self.units, ["reference", "referenced_by"]),
                         {"syn/chapter-i/article-2/clause-2": ["syn/chapter-i/article-3/clause-1"],
                          "syn/chapter-i/article-3/clause-1": ["syn/chapter-i/article-2/clause-2"]})

    def test_run_with_graph_and_token_budgets(self):
        plain = run(self.root / "bundle", self.questions, self.condition("dk3", "DK3", record="unit_with_claims"), self.shared, self.root / "r3")
        graph = run(self.root / "bundle", self.questions, self.condition("dk3g", "DK3", record="unit_with_claims", graph={"edges": ["reference"]}),
                    self.shared, self.root / "r3g")
        self.assertEqual(sorted(graph["mean_recall_at_tokens"]), ["40", "400"])
        self.assertLessEqual(graph["mean_recall_at_tokens"]["40"], graph["mean_recall_at_tokens"]["400"])
        self.assertGreater(graph["mean_recall"]["2"], plain["mean_recall"]["2"], "the cited Article 3 clause reaches the top 2")
        self.assertEqual((plain["mean_complete"]["2"], graph["mean_complete"]["2"]), (0.0, 1.0), "both gold units only with the graph")
        ranked = read_jsonl(self.root / "r3g" / "predictions.jsonl")[0]["ranked"]
        self.assertTrue(any("via_reference_from" in r for r in ranked[:2]))
        manifest = json.loads((self.root / "r3g" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual((manifest["graph"]["version"], manifest["graph"]["edge_count"]), ("reference-expansion-v3", 1))
        with self.assertRaisesRegex(ValueError, "DK3/DK4 only"):
            run(self.root / "bundle", self.questions, self.condition("dk2g", "DK2", graph={"edges": ["reference"]}), self.shared, self.root / "r2g")
        with self.assertRaisesRegex(ValueError, "record must be"):
            run(self.root / "bundle", self.questions, self.condition("bad", "DK3", record="whole_law"), self.shared, self.root / "bad")

    def test_preflight_requires_the_same_record_shape_for_dk3_and_dk4(self):
        three = self.root / "p3"
        run(self.root / "bundle", self.questions, self.condition("p3", "DK3", record="unit_with_claims"), self.shared, three)
        same = self.root / "p4"
        run(self.root / "bundle", self.questions, self.condition("p4", "DK4", record="unit_with_claims"), self.shared, same)
        other = self.root / "p4c"
        run(self.root / "bundle", self.questions, self.condition("p4c", "DK4", record="claims"), self.shared, other)
        status = lambda dirs: {c["check"]: c["status"] for c in check(dirs)["checks"]}["DK3 and DK4 use the same record shape and graph"]
        self.assertEqual(status([three, same]), "pass")
        self.assertEqual(status([three, other]), "fail")

    def test_char_precision_does_not_reward_long_records(self):
        gold = [{"document_id": "d", "source_start": 100, "source_end": 150}]
        self.assertEqual(char_precision([{"document_id": "d", "source_start": 100, "source_end": 150}], gold), 1.0)
        self.assertEqual(char_precision([{"document_id": "d", "source_start": 0, "source_end": 500}], gold), 0.1)
        overlapping = [{"document_id": "d", "source_start": 90, "source_end": 140}, {"document_id": "d", "source_start": 100, "source_end": 150}]
        self.assertEqual(char_precision(overlapping, gold), 50 / 60, "overlapping citations count once")
        self.assertEqual(char_precision([{"document_id": "x", "source_start": 0, "source_end": 10}], gold), 0.0)


if __name__ == "__main__":
    unittest.main()
