import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from legal_ai.retrieval import legal_chain as lc


def unit(unit_id, text, parent, start):
    return {"unit_id": unit_id, "text": text, "parent_id": parent, "document_id": unit_id.split("/")[0], "source_start": start,
            "unit_version_id": unit_id}


LAW, DECREE = "luat", "nd"
UNITS = [
    unit(f"{LAW}/article-26", "Điều 26. Tiền lương thử việc\n", LAW, 0),
    unit(f"{LAW}/article-26/clause-1", "1. Tiền lương thử việc ít nhất phải bằng 85% mức lương.\n", f"{LAW}/article-26", 10),
    unit(f"{LAW}/article-26/clause-2", "2. Hai bên thỏa thuận thời điểm trả.\n", f"{LAW}/article-26", 60),
    unit(f"{LAW}/article-27", "Điều 27. Trường hợp không áp dụng\nKhông áp dụng đối với hợp đồng dưới 01 tháng.\n", LAW, 100),
    unit(f"{DECREE}/article-10", "Điều 10. Vi phạm về thử việc\n", DECREE, 0),
    unit(f"{DECREE}/article-10/clause-1", "1. Phạt tiền khi tuyển dụng sai.\n", f"{DECREE}/article-10", 10),
    unit(f"{DECREE}/article-10/clause-2", "2. Phạt tiền khi trả lương thử việc thấp hơn 85% mức lương.\n", f"{DECREE}/article-10", 40),
]
DOCUMENTS = [{"document_id": LAW, "title": "Bộ luật"}, {"document_id": DECREE, "title": "Nghị định quy định xử phạt vi phạm hành chính"}]
RELATIONS = [
    # The decree article as source, as the model often answers: retyped to a sanction of the law.
    {"source_article": f"{DECREE}/article-10", "target_article": f"{LAW}/article-26", "type": "condition",
     "source_quote": "trả lương thử việc thấp hơn 85%", "target_quote": "ít nhất phải bằng 85% mức lương"},
    {"source_article": f"{LAW}/article-26", "target_article": f"{LAW}/article-27", "type": "exception",
     "source_quote": "Tiền lương thử việc", "target_quote": "không nằm trong Điều"},
]


def records():
    leaves = [u for u in UNITS if u["unit_id"] not in {x["parent_id"] for x in UNITS}]
    return [{"record_id": f"r{n}", "unit_ids": [u["unit_id"]]} for n, u in enumerate(leaves)]


class LegalChainTests(unittest.TestCase):
    def test_sanction_retyped_and_oriented_with_model_type_kept(self):
        rows = lc.retype_sanctions(RELATIONS, lc.sanction_documents(DOCUMENTS))
        self.assertEqual((rows[0]["type"], rows[0]["llm_type"]), ("sanction", "condition"))
        self.assertEqual((rows[0]["source_article"], rows[0]["target_article"]), (f"{LAW}/article-26", f"{DECREE}/article-10"))
        self.assertEqual(rows[0]["target_quote"], "trả lương thử việc thấp hơn 85%")
        self.assertEqual(rows[1]["type"], "exception")

    def test_quotes_anchor_at_their_unit_or_fall_back_to_the_article(self):
        edges = lc.typed_edges(UNITS, RELATIONS, DOCUMENTS, with_references=False)
        self.assertIn((f"{DECREE}/article-10/clause-2", "sanction"), [(n, r) for n, r, _ in edges[f"{LAW}/article-26/clause-1"]])
        self.assertIn((f"{LAW}/article-26/clause-1", "base"), [(n, r) for n, r, _ in edges[f"{DECREE}/article-10/clause-2"]])
        # A quote found nowhere anchors at the Article.
        self.assertIn((f"{LAW}/article-27", "exception"), [(n, r) for n, r, _ in edges[f"{LAW}/article-26/clause-1"]])
        self.assertIn((f"{LAW}/article-26/clause-1", "base"), [(n, r) for n, r, _ in edges[f"{LAW}/article-27"]])

    def test_expand_follows_roles_without_keyword_match_and_keeps_length(self):
        rows = records()
        edges = lc.typed_edges(UNITS, RELATIONS, DOCUMENTS, with_references=False)
        ids = [r["unit_ids"][0] for r in rows]
        seed = ids.index(f"{LAW}/article-26/clause-1")
        other = ids.index(f"{DECREE}/article-10/clause-1")
        expanded = lc.expand([(seed, 1.0), (other, 0.5)], rows, edges, depth=2, order=("sanction",))
        self.assertEqual(len(expanded), 2)
        self.assertEqual(expanded[0][:3], (seed, 1.0, None))
        neighbour, _, via, role = expanded[1]
        self.assertEqual((rows[neighbour]["unit_ids"][0], via, role), (f"{DECREE}/article-10/clause-2", seed, "sanction"))

    def test_role_order_decides_which_neighbours_come_first(self):
        rows = records()
        edges = lc.typed_edges(UNITS, RELATIONS, DOCUMENTS, with_references=False)
        ids = [r["unit_ids"][0] for r in rows]
        seed = ids.index(f"{LAW}/article-26/clause-1")
        first = lc.expand([(seed, 1.0)], rows, edges, depth=5, order=("exception", "sanction"), max_neighbors=1)
        self.assertEqual(first[1][3], "exception")
        only = lc.expand([(seed, 1.0)], rows, edges, depth=5, order=("sanction",), max_neighbors=2)
        self.assertEqual([r for *_, r in only[1:]], ["sanction"])

    def test_block_relations_read_from_the_sanction_side(self):
        rows = records()
        edges = lc.typed_edges(UNITS, RELATIONS, DOCUMENTS, with_references=False)
        by_unit = {r["unit_ids"][0]: r["record_id"] for r in rows}
        blocks = [{"id": "E01", "record_id": by_unit[f"{LAW}/article-26/clause-1"]},
                  {"id": "E02", "record_id": by_unit[f"{DECREE}/article-10/clause-2"]}]
        relations = lc.block_relations(blocks, rows, edges)
        self.assertEqual(relations, [{"from": "E02", "role": "sanction", "to": "E01"}])
        self.assertEqual(lc.relation_lines(relations), ["E02 là chế tài đối với E01"])

    def test_relation_lines_group_targets(self):
        rows = [{"from": "E02", "role": "sanction", "to": "E03"}, {"from": "E02", "role": "sanction", "to": "E01"},
                {"from": "E04", "role": "reference", "to": "E01"}]
        self.assertEqual(lc.relation_lines(rows), ["E02 là chế tài đối với E01, E03", "E04 có dẫn chiếu liên quan tới E01"])

    def test_affinity_picks_the_neighbour_closest_to_the_question(self):
        rows = records()
        edges = lc.typed_edges(UNITS, RELATIONS, DOCUMENTS, with_references=False)
        ids = [r["unit_ids"][0] for r in rows]
        seed = ids.index(f"{LAW}/article-26/clause-1")
        sanction, exception = ids.index(f"{DECREE}/article-10/clause-2"), ids.index(f"{LAW}/article-27")
        close_to_sanction = {seed: 0, sanction: 1, exception: 50}
        picked = lc.expand([(seed, 1.0)], rows, edges, depth=5, max_neighbors=1, affinity=close_to_sanction, select="affinity")
        self.assertEqual(picked[1][0], sanction)
        # Role order alone would take the exception first.
        self.assertEqual(lc.expand([(seed, 1.0)], rows, edges, depth=5, max_neighbors=1)[1][0], exception)
        # Neighbours ranked below the limit are not followed.
        self.assertEqual(len(lc.expand([(seed, 1.0)], rows, edges, depth=5, affinity=close_to_sanction, select="affinity",
                                       max_affinity_rank=1)), 1)

    def test_config_rejects_unknown_roles(self):
        with self.assertRaises(ValueError):
            lc.check_config({"relation_run": "x", "order": ["exception", "precedence"]})
        with self.assertRaises(ValueError):
            lc.check_config({"order": ["exception"]})


if __name__ == "__main__":
    unittest.main()
