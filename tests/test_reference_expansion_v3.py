"""reference-expansion-v3: neighbours of the top N over reference edges, no match requirement, cap of 2. Synthetic data."""

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import test_kb_records_graph as base
from legal_ai.common.io import read_jsonl
from legal_ai.evaluation.retrieval_run import run
from legal_ai.retrieval.graph import EXPANSION_V3, check_config, expand, expand_v3


def records(*specs):
    return [{"unit_ids": [unit], "document_id": doc} for doc, unit in specs]


class ExpandV3Tests(unittest.TestCase):
    def setUp(self):
        # records 0-3 and 6-8 in document a, 4-5 in document b; record 8 is never ranked
        self.records = records(("a", "a/1"), ("a", "a/2"), ("a", "a/3"), ("a", "a/4"), ("b", "b/1"), ("b", "b/2"),
                               ("a", "a/7"), ("a", "a/8"), ("a", "a/9"))
        self.ranked = [(n, 10.0 - n) for n in range(len(self.records) - 1)]

    def test_neighbour_follows_its_source_without_matching_the_question(self):
        result = expand_v3(self.ranked, self.records, {"a/1": ["a/9"]}, depth=9, top_n=5)
        self.assertEqual([i for i, _, _ in result][:3], [0, 8, 1])
        self.assertEqual(result[1], (8, 0.0, 0), "unranked neighbour, via its source, score 0")

    def test_only_the_top_n_sources_are_expanded(self):
        edges = {"a/3": ["a/9"], "a/7": ["a/8"]}
        top5 = [i for i, _, _ in expand_v3(self.ranked, self.records, edges, depth=9, top_n=5)]
        self.assertEqual(top5.index(8), top5.index(2) + 1)
        self.assertEqual(top5.index(7), top5.index(6) + 1, "record 6 is rank 7, outside the top 5: record 7 keeps its ranked place after it")
        top10 = expand_v3(self.ranked, self.records, edges, depth=9, top_n=10)
        self.assertEqual(sorted(v for _, _, v in top10 if v is not None), [2, 6])

    def test_both_directions_and_cap_prefers_other_document_then_text_order(self):
        edges = {"a/1": ["a/2", "a/3", "b/1"]}
        result = expand_v3(self.ranked, self.records, edges, depth=9, top_n=5)
        self.assertEqual([(i, v) for i, _, v in result][:3], [(0, None), (4, 0), (1, 0)], "b/1 first (other document), then a/2")
        back = {"a/9": ["a/1", "b/2"]}
        self.assertEqual([i for i, _, _ in expand_v3([(8, 3.0), (6, 2.0), (7, 1.0)], self.records, back, depth=5, top_n=5)],
                         [8, 5, 0, 6, 7], "citing units are neighbours of the cited one, other document first")

    def test_no_duplicates_and_no_move_of_earlier_ranked(self):
        edges = {"a/2": ["a/1", "a/4"], "a/1": ["a/3"]}
        result = expand_v3(self.ranked, self.records, edges, depth=9, top_n=5)
        order = [i for i, _, _ in result]
        self.assertEqual(len(order), len(set(order)))
        self.assertEqual(order[:4], [0, 2, 1, 3], "a/3 moves up next to a/1; a/1 stays ahead of a/2 and is not moved again; a/4 follows a/2")
        self.assertEqual(dict((i, v) for i, _, v in result)[3], 1)

    def test_ancestor_edges_and_depth_cut(self):
        rows = records(("a", "a/art"), ("a", "a/art/c1"), ("a", "a/other"), ("b", "b/x"))
        result = expand_v3([(1, 3.0), (2, 2.0), (3, 1.0)], rows, {"a/art": ["b/x"]}, depth=2, top_n=5)
        self.assertEqual([i for i, _, _ in result], [1, 3], "an Article's reference serves its Clause; the list keeps its depth")

    def test_old_expansion_is_unchanged(self):
        edges = {"a/1": ["a/9"]}
        old = expand(self.ranked, self.records, edges, depth=9, max_neighbors=2, require_match=True)
        self.assertNotIn(8, [i for i, _, _ in old], "the old expansion still needs the neighbour to match")
        self.assertEqual(old[0], (0, 10.0, None))
        self.assertIn(8, [i for i, _, _ in expand(self.ranked, self.records, edges, depth=9)])

    def test_config(self):
        ok = {"edges": ["reference", "referenced_by"], "expansion": EXPANSION_V3, "top_n": 10}
        self.assertEqual(check_config(ok), ok)
        for bad in ({"top_n": 7}, {"top_n": None}, {"require_match": True}, {"max_neighbors": 3}, {"edges": ["same_article"]}, {"expansion": "v4"}):
            with self.assertRaises(ValueError, msg=str(bad)):
                check_config(ok | bad)
        with self.assertRaises(ValueError):
            check_config({"edges": ["reference"], "top_n": 5})


class RunV3Tests(base.KbRecordGraphTests):
    def test_manifest_and_ranking(self):
        graph = {"edges": ["reference", "referenced_by"], "expansion": EXPANSION_V3, "top_n": 5}
        run(self.root / "bundle", self.questions, self.condition("v3", "DK3", record="unit_with_claims", graph=graph), self.shared, self.root / "rv3")
        manifest = json.loads((self.root / "rv3" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual((manifest["graph"]["version"], manifest["graph"]["top_n"], manifest["graph"]["expansion"]), (EXPANSION_V3, 5, EXPANSION_V3))
        ranked = read_jsonl(self.root / "rv3" / "predictions.jsonl")[0]["ranked"]
        self.assertTrue(any("via_reference_from" in r for r in ranked))
        self.assertEqual(len({r["record_id"] for r in ranked}), len(ranked))

    def test_old_condition_still_records_v5(self):
        run(self.root / "bundle", self.questions, self.condition("old", "DK3", record="unit_with_claims", graph={"edges": ["reference"]}), self.shared, self.root / "rold")
        manifest = json.loads((self.root / "rold" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["graph"]["version"], "reference-expansion-v5")


for _name in [n for n in dir(base.KbRecordGraphTests) if n.startswith("test_")]:
    setattr(RunV3Tests, _name, None)

if __name__ == "__main__":
    unittest.main()
