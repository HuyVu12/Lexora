import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from test_legal_chain import DECREE, DOCUMENTS, LAW, RELATIONS, UNITS
from legal_ai.evaluation import neighbor_select as ns
from legal_ai.retrieval import legal_chain as lc


def records():
    leaves = [u for u in UNITS if u["unit_id"] not in {x["parent_id"] for x in UNITS}]
    return [{"record_id": u["unit_id"], "unit_ids": [u["unit_id"]], "index_text": u["text"], "token_count": 5} for u in leaves]


class NeighborSelectTests(unittest.TestCase):
    def setUp(self):
        self.records = records()
        self.by_id = {r["record_id"]: r for r in self.records}
        self.edges = lc.typed_edges(UNITS, RELATIONS, DOCUMENTS, with_references=False)

    def test_candidates_are_graph_neighbours_of_the_seeds_not_already_on_top(self):
        prediction = {"ranked": [{"record_id": f"{LAW}/article-26/clause-1"}, {"record_id": f"{DECREE}/article-10/clause-1"}]}
        seeds, pool = ns.candidates(prediction, self.records, self.by_id, self.edges, seeds=1, skip_top=1)
        self.assertEqual(seeds, [f"{LAW}/article-26/clause-1"])
        self.assertEqual([(c["record_id"], c["role"]) for c in pool],
                         [(f"{LAW}/article-27", "exception"), (f"{DECREE}/article-10/clause-2", "sanction")])
        # A neighbour already among the top records is not offered again.
        _, pool = ns.candidates({"ranked": prediction["ranked"] + [{"record_id": f"{LAW}/article-27"}]}, self.records, self.by_id,
                                self.edges, seeds=1, skip_top=3)
        self.assertNotIn(f"{LAW}/article-27", [c["record_id"] for c in pool])

    def test_request_labels_relations_and_schema_limits_choices(self):
        seeds = [f"{LAW}/article-26/clause-1"]
        pool = [{"record_id": f"{DECREE}/article-10/clause-2", "seed": seeds[0], "role": "sanction"},
                {"record_id": f"{LAW}/article-27", "seed": seeds[0], "role": "base"}]
        body = ns.request("Lương thử việc 70% có bị phạt không?", [], seeds, pool, self.by_id)
        self.assertEqual([c["relation"] for c in body["candidates"]],
                         ["chế tài đối với S1", "quy định gốc mà S1 hướng dẫn, ngoại lệ hoặc xử phạt"])
        self.assertNotIn("issues", body)
        self.assertEqual(ns.schema(2, 1)["properties"]["selected"], {"type": "array", "maxItems": 1, "items": {"type": "string", "enum": ["C1", "C2"]}})

    def test_request_by_issue_groups_seeds_and_candidates(self):
        a, b = f"{LAW}/article-26/clause-1", f"{DECREE}/article-10/clause-1"
        groups = [("Mức lương thử việc", [a], [{"record_id": f"{DECREE}/article-10/clause-2", "seed": a, "role": "sanction"}]),
                  ("Xử phạt", [a, b], [{"record_id": f"{LAW}/article-27", "seed": b, "role": "reference"}])]
        body = ns.request_by_issue("Lương thử việc 70% có bị phạt không?", groups, self.by_id)
        self.assertEqual([i["id"] for i in body["issues"]], ["V1", "V2"])
        self.assertEqual([(f["id"], f["issue"]) for f in body["found"]], [("S1", "V1"), ("S2", "V2")], "a shared seed is shown once")
        self.assertEqual([(c["id"], c["issue"], c["relation"]) for c in body["candidates"]],
                         [("C1", "V1", "chế tài đối với S1"), ("C2", "V2", "có dẫn chiếu liên quan tới S2")])


if __name__ == "__main__":
    unittest.main()
