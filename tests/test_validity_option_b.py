"""Validity option B (22/11/2026): DK2 filters by document dates only, DK3 follows amendment edges as knowledge-base
relations without checking status, DK4 adds the checks (edge dates, unit status, claims of stale units unused). Synthetic texts only, not real law."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_kb_records_graph import claim
from test_retrieval_run import SYNTHETIC, bundle
from test_validity import AMENDING
from legal_ai.common.io import digest, read_jsonl, write_json, write_jsonl
from legal_ai.evaluation.retrieval_run import run
from legal_ai.kb.amendments import detect, link_amending_units
from legal_ai.retrieval import amendment_graph

OLD = "1-2020-nd-cp/chapter-i/article-1/clause-2"
REPEALED = "1-2020-nd-cp/chapter-i/article-3"
NOTICE = "Báo trước bao nhiêu ngày đối với hợp đồng xác định thời hạn?"
LEAVE = "Người làm việc đủ 12 tháng được nghỉ hằng năm bao nhiêu ngày?"


class OptionBTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        documents, units, texts = bundle(self.root / "bundle", {"1-2020-nd-cp": SYNTHETIC, "2-2021-nd-cp": AMENDING})
        dates = {"1-2020-nd-cp": "2020-07-01", "2-2021-nd-cp": "2021-07-01"}
        for document in documents:
            document |= {"effective_from": dates[document["document_id"]], "effective_to": None}
        documents[1]["title"] = "Nghị định số 2/2021/NĐ-CP sửa đổi, bổ sung một số điều của Nghị định số 1/2020/NĐ-CP"
        write_jsonl(self.root / "bundle" / "documents.jsonl", documents)
        self.units, self.documents = units, documents
        self.edges = link_amending_units(detect({"document_id": "2-2021-nd-cp"}, texts["2-2021-nd-cp"], units, "2021-07-01"), units, texts["2-2021-nd-cp"])
        units_sha = digest((self.root / "bundle" / "units.jsonl").read_bytes())
        self.edge_dir = self.root / "edges"
        write_jsonl(self.edge_dir / "edges.jsonl", self.edges)
        write_json(self.edge_dir / "manifest.json", {"units_sha256": units_sha})
        self.new = next(e["amending_unit_id"] for e in self.edges if e["target_unit_id"] == OLD)
        claims = [claim(units, OLD, "Ít nhất 30 ngày đối với hợp đồng xác định thời hạn", "kb:old", quantities="30 ngày"),
                  claim(units, REPEALED, "Người làm việc đủ 12 tháng được nghỉ 12 ngày", "kb:leave", quantities="12 ngày")]
        self.kb = self.root / "kb"
        write_json(self.kb / "manifest.json", {"units_sha256": units_sha})
        write_jsonl(self.kb / "dk3.jsonl", claims)
        write_jsonl(self.kb / "dk4.jsonl", claims)
        self.shared = self.root / "shared.json"
        write_json(self.shared, {"top_k": 3, "validity_as_of": "2022-01-01", "token_budgets": [2000], "context_packing": "P2",
                                 "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75, "recall_k": [1, 3]}})
        self.graph = {"edges": ["reference", "referenced_by"], "max_neighbors": 2, "require_match": True,
                      "amendments": {"run": self.edge_dir.as_posix(), "max_neighbors": 2}}

    def condition(self, name, dk, **extra):
        body = {"condition": dk, "max_tokens": 384,
                "representation": {"DK2": "structural_units", "DK3": "llm_kb_raw", "DK4": "llm_kb_validated"}[dk]}
        if dk != "DK2":
            body |= {"kb_run": self.kb.as_posix(), "record": "unit_with_claims", "claims_view": "compact", "graph": self.graph}
        path = self.root / f"{name}.json"
        write_json(path, body | extra)
        return path

    def dk3(self):
        return self.condition("dk3", "DK3", validity={"level": "document"})

    def dk4(self):
        return self.condition("dk4", "DK4", validity={"level": "unit", "amendments": self.edge_dir.as_posix()})

    def dk2(self):
        return self.condition("dk2", "DK2", validity={"level": "document"})

    def questions(self, as_of):
        path = self.root / f"q-{as_of}.json"
        write_json(path, {"questions": [
            {"question_id": "notice", "question": NOTICE, "as_of": as_of, "relevant_unit_ids": [self.new if as_of >= "2021-07-01" else OLD],
             **({"stale_unit_ids": [OLD]} if as_of >= "2021-07-01" else {"not_yet_effective_unit_ids": [self.new]})},
            {"question_id": "leave", "question": LEAVE, "as_of": as_of, "relevant_unit_ids": [REPEALED] if as_of < "2021-07-01" else [],
             **({"stale_unit_ids": [REPEALED]} if as_of >= "2021-07-01" else {})}]})
        return path

    def run_at(self, condition, as_of, name):
        metrics = run(self.root / "bundle", self.questions(as_of), condition, self.shared, self.root / name)
        rows = {r["question_id"]: r for r in read_jsonl(self.root / name / "predictions.jsonl")}
        manifest = json.loads((self.root / name / "manifest.json").read_text(encoding="utf-8"))
        return metrics, rows, manifest

    @staticmethod
    def units_of(row):
        return [r["unit_ids"][0] for r in row["ranked"]]

    def test_relations_use_resolved_edges_only_and_count_the_rest(self):
        links, report = amendment_graph.relations(self.edges, self.units)
        self.assertIn(OLD, links)
        self.assertEqual([(other, role) for other, _, role in links[OLD]], [(self.new, "amending")])
        self.assertIn((OLD, "amended"), [(other, role) for other, _, role in links[self.new]])
        used = {e["edge_id"] for rows in links.values() for _, e, _ in rows}
        self.assertTrue(used and all(e["status"] in amendment_graph.USABLE for e in self.edges if e["edge_id"] in used))
        unusable = [e for e in self.edges if e["status"] not in amendment_graph.USABLE]
        self.assertTrue(unusable, "the fixture holds unresolved and external edges")
        self.assertFalse({e["edge_id"] for e in unusable} & used, "an edge without a corpus unit is never followed")
        self.assertEqual(sum(report["unused"].values()), len(unusable))
        self.assertEqual(sum(report["used"].values()) + sum(report["unused"].values()), len(self.edges))
        self.assertEqual(amendment_graph.describe(self.new, {u["unit_id"]: u for u in self.units}, {d["document_id"]: d for d in self.documents}),
                         "điểm a khoản 1 Điều 1 Nghị định số 2/2021/NĐ-CP")

    def test_dk3_pulls_amendment_neighbours_and_keeps_stale_units(self):
        metrics, rows, manifest = self.run_at(self.dk3(), "2022-01-01", "dk3")
        notice = rows["notice"]
        self.assertIn(OLD, self.units_of(notice), "no status check: the outdated wording stays")
        self.assertIn(self.new, self.units_of(notice))
        pulled = [r for r in notice["ranked"] if "via_amendment" in r]
        self.assertTrue(pulled and notice["amendment_neighbours"] >= 1)
        self.assertTrue(all(r["status_note"].startswith("[Quan hệ trong kho: quy định này") for r in pulled))
        self.assertIn(REPEALED, self.units_of(rows["leave"]), "a repealed unit stays in DK3")
        repeal = [r for r in rows["leave"]["ranked"] if "via_amendment" in r and r["via_amendment"]["role"] == "amending"]
        self.assertTrue(repeal and "bãi bỏ" in repeal[0]["status_note"], "the repealing unit comes along with its relation note")
        self.assertEqual(metrics["stale_context_rate_at_tokens"]["2000"], 1.0)
        relations = manifest["graph"]["amendment_relations"]
        self.assertEqual((relations["version"], relations["date_check"]), ("amendment-expansion-v1", False))
        self.assertEqual(relations["edges_sha256"], digest((self.edge_dir / "edges.jsonl").read_bytes()))
        self.assertEqual(manifest["validity"]["level"], "document")
        followed = {r["via_amendment"]["edge_id"] for row in rows.values() for r in row["ranked"] if "via_amendment" in r}
        self.assertTrue(followed <= {e["edge_id"] for e in self.edges if e["status"] in amendment_graph.USABLE})

    def test_dk3_keeps_the_document_dates_of_dk2(self):
        metrics, rows, _ = self.run_at(self.dk3(), "2021-01-01", "dk3-past")
        self.assertNotIn(self.new, self.units_of(rows["notice"]), "an amending document not yet in force is dropped, as in DK2")
        self.assertIn(OLD, self.units_of(rows["notice"]))
        self.assertEqual(metrics["wrong_version_context_rate_at_tokens"]["2000"], 0.0)
        without = self.condition("dk3-nodates", "DK3")  # Without any validity block the relation is followed whatever the date.
        metrics, rows, _ = self.run_at(without, "2021-01-01", "dk3-nodates")
        self.assertIn(self.new, self.units_of(rows["notice"]))
        self.assertEqual(metrics["wrong_version_context_rate_at_tokens"]["2000"], 1.0)

    def test_dk4_drops_and_replaces_per_status_and_marks_claims_unused(self):
        metrics, rows, manifest = self.run_at(self.dk4(), "2022-01-01", "dk4")
        self.assertNotIn(OLD, self.units_of(rows["notice"]), "the amended unit is replaced by its new wording")
        self.assertIn(self.new, self.units_of(rows["notice"]))
        self.assertNotIn(REPEALED, self.units_of(rows["leave"]), "the repealed unit is dropped")
        self.assertEqual(metrics["stale_context_rate_at_tokens"]["2000"], 0.0)
        self.assertGreaterEqual(rows["notice"]["validity"]["unused_claims"], 1, "claims of the replaced unit are not used")
        self.assertGreaterEqual(rows["leave"]["validity"]["unused_claims"], 1)
        self.assertEqual((manifest["graph"]["amendment_relations"]["date_check"], manifest["validity"]["level"]), (True, "unit"))

    def test_dk4_does_not_follow_an_edge_before_it_takes_effect(self):
        metrics, rows, _ = self.run_at(self.dk4(), "2021-01-01", "dk4-past")
        self.assertIn(OLD, self.units_of(rows["notice"]))
        self.assertNotIn(self.new, self.units_of(rows["notice"]))
        self.assertFalse([r for r in rows["notice"]["ranked"] if "via_amendment" in r])
        self.assertIn(REPEALED, self.units_of(rows["leave"]), "before the repeal the Article applies")
        self.assertEqual(metrics["wrong_version_context_rate_at_tokens"]["2000"], 0.0)

    def test_expansion_date_check_skips_undated_and_later_edges(self):
        records = [{"record_id": "a", "unit_ids": [OLD]}, {"record_id": "b", "unit_ids": [self.new]}]
        edge = {"edge_id": "e", "kind": "modify", "status": "resolved", "target_unit_id": OLD, "amending_unit_id": self.new, "effective_from": None}
        links, _ = amendment_graph.relations([edge], self.units)
        self.assertEqual(len(amendment_graph.expand([(0, 1.0)], records, links, 5)), 2, "DK3 follows an undated edge")
        self.assertEqual(len(amendment_graph.expand([(0, 1.0)], records, links, 5, as_of="2022-01-01")), 1, "DK4 does not")
        links, _ = amendment_graph.relations([edge | {"effective_from": "2023-01-01"}], self.units)
        self.assertEqual(len(amendment_graph.expand([(0, 1.0)], records, links, 5, as_of="2022-01-01")), 1)
        self.assertEqual(len(amendment_graph.expand([(0, 1.0)], records, links, 5, as_of="2023-01-01")), 2)
        self.assertEqual(amendment_graph.expand([(0, 1.0)], records, links, 1), [(0, 1.0, None)], "the list keeps its length")

    def test_dk2_filters_by_document_dates_only(self):
        metrics, rows, manifest = self.run_at(self.dk2(), "2022-01-01", "dk2")
        self.assertIn(OLD, self.units_of(rows["notice"]), "no unit status in DK2")
        self.assertIn(REPEALED, self.units_of(rows["leave"]))
        self.assertFalse(any("via_amendment" in r or "status_note" in r for row in rows.values() for r in row["ranked"]))
        self.assertNotIn("amendment_neighbours", rows["notice"])
        self.assertEqual((manifest["validity"]["level"], manifest["validity"]["edges_sha256"], manifest["graph"]), ("document", None, None))
        self.assertEqual(metrics["stale_context_rate_at_tokens"]["2000"], 1.0)
        _, early, _ = self.run_at(self.dk2(), "2021-01-01", "dk2-past")
        self.assertFalse(any(u.startswith("2-2021-nd-cp/") for u in self.units_of(early["notice"])), "a document not yet in force is dropped")
        with self.assertRaisesRegex(ValueError, "DK3/DK4 only"):
            run(self.root / "bundle", self.questions("2022-01-01"), self.condition("dk2g", "DK2", graph=self.graph), self.shared, self.root / "dk2g")


if __name__ == "__main__":
    unittest.main()
