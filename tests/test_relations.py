"""Typed article relations for the KB graph: candidates, verbatim-quote validation, resume and graph use.
Synthetic statute, stand-in model."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_retrieval_run import bundle
from legal_ai.common.io import read_jsonl, write_json
from legal_ai.evaluation import relation_run
from legal_ai.evaluation.retrieval_run import run as retrieval_run
from legal_ai.providers.pilot import ProviderError
from legal_ai.retrieval.graph import graph_edges

LAW = ("Chương I\nQUY ĐỊNH GIẢ ĐỊNH\n"
       "Điều 1. Sa thải giả định\n"
       "Bên A được sa thải bên B khi bên B tự ý bỏ việc 05 ngày.\n"
       "Điều 2. Trường hợp không được sa thải\n"
       "Không được sa thải bên B đang nuôi con dưới 12 tháng tuổi.\n"
       "Điều 3. Hậu quả sa thải trái luật\n"
       "Bên A sa thải trái luật phải nhận bên B trở lại làm việc.\n"
       "Điều 4. Hội đồng giả định\n"
       "Hội đồng giả định họp mỗi quý một lần.\n")


class Relater:
    model, effort, provider = "stand-in", "temperature-0", "9router"

    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def structured(self, system, prompt, schema, purpose="structured"):
        request = json.loads(prompt)
        self.calls.append(request["source"]["heading"])
        if self.fail:
            raise ProviderError("timeout")
        if not request["source"]["heading"].startswith("Điều 1."):
            return {"output": {"relations": []}, "model": "stand-in"}
        ids = {c["heading"].split(".")[0]: c["id"] for c in request["candidates"]}
        return {"output": {"relations": [
            {"target": ids["Điều 2"], "type": "exception", "source_quote": "được sa thải", "target_quote": "Không được sa thải"},
            {"target": ids["Điều 3"], "type": "consequence", "source_quote": "được   sa thải", "target_quote": "phải nhận bên B trở lại làm việc"},
            {"target": ids["Điều 4"], "type": "detail", "source_quote": "câu không có trong Điều", "target_quote": "Hội đồng"},
            {"target": "A99", "type": "exception", "source_quote": "sa thải", "target_quote": "sa thải"},
            {"target": ids["Điều 2"], "type": "rule", "source_quote": "sa thải", "target_quote": "sa thải"}]}, "model": "stand-in"}


class RelationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        _, self.units, _ = bundle(self.root / "bundle", {"syn": LAW})

    def test_articles_and_candidates_come_from_the_corpus(self):
        rows = relation_run.articles(self.units)
        self.assertEqual([r["id"] for r in rows], [f"syn/chapter-i/article-{n}" for n in range(1, 5)])
        self.assertIn("Bên A được sa thải", rows[0]["text"])
        offered = relation_run.candidates(self.units, rows)
        self.assertNotIn(rows[0]["id"], offered[rows[0]["id"]], "an article is never its own candidate")
        self.assertIn("syn/chapter-i/article-2", offered[rows[0]["id"]])

    def test_dense_candidates_add_nearest_articles_not_chosen_yet(self):
        try:
            import numpy
        except ImportError:
            self.skipTest("numpy (embeddings extra) not installed")

        class Embedder:
            def encode(self, texts):  # Articles 1 and 3 share a direction; 2 and 4 another.
                return numpy.asarray([[1.0, 0.0] if ("Sa thải" in t or "Hậu quả" in t) else [0.0, 1.0] for t in texts], dtype="float32")

        rows = relation_run.articles(self.units)
        offered = relation_run.candidates(self.units, rows, k=1, dense=1, embedder=Embedder())
        first = offered["syn/chapter-i/article-1"]
        self.assertEqual(len(first), 2)
        self.assertIn("syn/chapter-i/article-3", first, "the nearest article by embedding is added")

    def test_extract_validates_quotes_targets_and_types_and_resumes(self):
        out = self.root / "rel"
        relation_run.start(self.root / "bundle", out, "stand-in", "9router")
        self.assertEqual(relation_run.extract(self.units, Relater(fail=True), out)["failed"], 4)
        relater = Relater()
        counts = relation_run.extract(self.units, relater, out, workers=3)
        self.assertEqual((counts["ok"], len(relater.calls)), (4, 4))
        report = relation_run.materialize(self.units, out)
        self.assertEqual(report["by_type"], {"consequence": 1, "exception": 1})
        self.assertEqual(report["rejected"], {"source_quote_not_verbatim": 1, "target_not_offered": 1, "unknown_type": 1})
        self.assertEqual(len(read_jsonl(out / "relations.jsonl")), 2)
        self.assertEqual(relation_run.extract(self.units, Relater(), out)["already_done"], 4)
        with self.assertRaisesRegex(ValueError, "other inputs"):
            relation_run.start(self.root / "bundle", out, "other-model", "9router")

    def test_relation_edges_join_rule_exception_and_consequence_both_ways(self):
        out = self.root / "rel"
        relation_run.start(self.root / "bundle", out, "stand-in", "9router")
        relation_run.extract(self.units, Relater(), out)
        relation_run.materialize(self.units, out)
        edges = graph_edges(self.units, ["relation"], relations=read_jsonl(out / "relations.jsonl"))
        self.assertEqual(sorted(edges["syn/chapter-i/article-1"]), ["syn/chapter-i/article-2", "syn/chapter-i/article-3"])
        self.assertEqual(edges["syn/chapter-i/article-3"], ["syn/chapter-i/article-1"])
        kb = self.root / "kb"
        from legal_ai.common.io import digest, write_jsonl
        write_json(kb / "manifest.json", {"units_sha256": digest((self.root / "bundle" / "units.jsonl").read_bytes())})
        write_jsonl(kb / "dk3.jsonl", [])
        condition, shared, questions = self.root / "dk3.json", self.root / "shared.json", self.root / "q.json"
        write_json(condition, {"condition": "DK3", "representation": "llm_kb_raw", "record": "unit_with_claims", "kb_run": kb.as_posix(),
                               "graph": {"edges": ["relation"], "relation_run": out.as_posix(), "require_match": False}})
        write_json(shared, {"top_k": 2, "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75, "recall_k": [1, 2]}})
        write_json(questions, {"questions": [{"question_id": "q1", "question": "Bỏ việc 05 ngày thì có bị sa thải không?", "split": "dev",
                                              "expected_status": "answer", "relevant_unit_ids": ["syn/chapter-i/article-1", "syn/chapter-i/article-2"]}]})
        metrics = retrieval_run(self.root / "bundle", questions, condition, shared, self.root / "run")
        self.assertEqual(metrics["mean_complete"]["2"], 1.0, "the exception follows the rule that was found")
        manifest = json.loads((self.root / "run" / "manifest.json").read_text(encoding="utf-8"))
        self.assertIn("relations_sha256", manifest["graph"])


if __name__ == "__main__":
    unittest.main()
