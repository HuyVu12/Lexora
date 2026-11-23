"""Context packing (`pack-article-v1`), budget curves and verification load, on a synthetic statute (not real law)."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_retrieval_run import SECOND, SYNTHETIC, bundle
from legal_ai.common.io import canonical, digest, read_jsonl, write_json
from legal_ai.evaluation.answer_run import pack_with_groups, packer_for, verification_load
from legal_ai.evaluation.preflight import check
from legal_ai.evaluation.retrieval_run import _recall, recall_steps, run, score_top, tokens_to_reach, within_budget
from legal_ai.indexing import packing
from legal_ai.indexing.packing import SIBLING_GROUP_TOKENS, Packer, condition_mode, evidence_payload, short_title
from legal_ai.indexing.records import kb_unit_records, structural_records, token_spans


class PackerTests(unittest.TestCase):
    def setUp(self):
        self.documents, self.units, self.texts = bundle(None, {"syn-a": SYNTHETIC, "syn-b": SECOND})
        self.records = structural_records(self.documents, self.units, self.texts)
        self.by_unit = {r["unit_ids"][0]: r for r in self.records}

    def ranked(self, *suffixes):
        return [self.by_unit[f"syn-a/chapter-i/{s}"] for s in suffixes]

    def test_p0_is_the_flat_list_and_dk1_always_packs_flat(self):
        ranked = self.ranked("article-2/clause-2/point-b", "article-1/clause-1")
        packed = Packer("P0").pack(ranked, 10 ** 6)
        self.assertEqual([b["text"] for b in packed["blocks"]], [r["index_text"] for r in ranked])
        self.assertEqual(packed["tokens"], sum(len(token_spans(r["index_text"])) for r in ranked))
        self.assertEqual((condition_mode("DK1", "P2"), condition_mode("DK2", None), condition_mode("DK3", "P1")), ("P0", "P0", "P1"))
        with self.assertRaises(ValueError):
            condition_mode("DK2", "P9")

    def test_p1_groups_by_article_in_first_appearance_order_and_text_order_inside(self):
        ranked = self.ranked("article-2/clause-2/point-b", "article-1/clause-2", "article-2/clause-1", "article-1/clause-1")
        packer = Packer("P1", self.records, self.units, self.documents)
        packed = packer.pack(ranked, 10 ** 6)
        self.assertEqual([b["record"]["unit_ids"][0].split("/", 2)[2] for b in packed["blocks"]],
                         ["article-2/clause-1", "article-2/clause-2/point-b", "article-1/clause-1", "article-1/clause-2"])
        self.assertEqual([b["id"] for b in packed["blocks"]], ["E01", "E02", "E03", "E04"], "block IDs follow the reading order")
        self.assertEqual(len(packed["groups"]), 2)
        header = packed["groups"][0]["header"]
        self.assertTrue(header.startswith("Văn bản giả định syn-a\nChương I > Điều 2\nĐiều 2. Tiền lương giả định"))
        self.assertEqual(packed["blocks"][1]["text"].split("\n")[0], "Khoản 2 > Điểm b", "the body keeps the path below the Article")
        self.assertIn("trừ trường hợp hai bên có thỏa thuận khác", packed["blocks"][1]["text"], "the Clause lead stays with its Point")
        self.assertNotIn("Điều 2. Tiền lương", packed["blocks"][1]["text"], "the Article header is printed once")
        self.assertEqual(packed["tokens"], sum(g["header_tokens"] for g in packed["groups"]) + sum(b["token_count"] for b in packed["blocks"]))
        flat = Packer("P0").pack(ranked, 10 ** 6)
        self.assertLess(packed["tokens"], flat["tokens"], "headers printed once cost less than repeated on every record")
        payload = evidence_payload(packed)
        self.assertEqual([[p["id"] for p in g["passages"]] for g in payload], [["E01", "E02"], ["E03", "E04"]])
        self.assertEqual(evidence_payload(flat)[0], {"id": "E01", "text": ranked[0]["index_text"]})

    def test_p2_siblings_pass_the_admit_function_and_nothing_changes_without_it(self):
        packer = Packer("P2", self.records, self.units, self.documents)
        ranked = self.ranked("article-2/clause-2/point-b")
        dropped = self.by_unit["syn-a/chapter-i/article-2/clause-2/point-a"]["record_id"]
        noted = self.by_unit["syn-a/chapter-i/article-2/clause-1"]["record_id"]

        def admit(record):
            if record["record_id"] == dropped:
                return []
            return [record | {"status_note": "[ghi chú hiệu lực]"}] if record["record_id"] == noted else [record]
        plain = packer.pack(ranked, 10 ** 6)
        self.assertEqual(packer.pack(ranked, 10 ** 6, admit=lambda r: [r]), plain, "admitting every sibling unchanged changes nothing")
        filtered = packer.pack(ranked, 10 ** 6, admit=admit)
        ids = [b["record"]["record_id"] for b in filtered["blocks"]]
        self.assertIn(dropped, [b["record"]["record_id"] for b in plain["blocks"]])
        self.assertNotIn(dropped, ids, "a sibling the filter drops is not added")
        self.assertIn("[ghi chú hiệu lực]", next(b["text"] for b in filtered["blocks"] if b["record"]["record_id"] == noted))
        self.assertEqual(packer.bind(admit).pack(ranked, 10 ** 6), filtered, "a bound packer applies the same function")

    def test_budget_is_never_exceeded_and_units_are_not_repeated(self):
        ranked = self.ranked("article-2/clause-2/point-b", "article-1/clause-2", "article-2/clause-1", "article-1/clause-1", "article-3")
        for mode in ("P0", "P1", "P2", "P3"):
            packer = Packer(mode, self.records, self.units, self.documents)
            full = packer.pack(ranked, 10 ** 6)["tokens"]
            for budget in range(0, full + 5, 7):
                packed = packer.pack(ranked + ranked, budget)
                self.assertTrue(len(packed["blocks"]) == 1 or packed["tokens"] <= budget, (mode, budget))
                ids = [b["record"]["record_id"] for b in packed["blocks"]]
                self.assertEqual(len(ids), len(set(ids)), mode)
                self.assertIn(ranked[0]["record_id"], ids)
                if packed["next_budget"] is not None:
                    self.assertGreater(packer.pack(ranked, packed["next_budget"])["tokens"], packed["tokens"])

    def test_p2_adds_unranked_siblings_of_the_first_articles_within_the_group_cap(self):
        ranked = self.ranked("article-2/clause-1")
        packed = Packer("P2", self.records, self.units, self.documents).pack(ranked, 10 ** 6)
        units = [b["record"]["unit_ids"][0].split("/", 2)[2] for b in packed["blocks"]]
        self.assertEqual(units, ["article-2/clause-1", "article-2/clause-2/point-a", "article-2/clause-2/point-b"])
        self.assertEqual([b["sibling"] for b in packed["blocks"]], [False, True, True])
        self.assertLessEqual(packed["groups"][0]["header_tokens"] + sum(b["token_count"] for b in packed["blocks"]), SIBLING_GROUP_TOKENS)
        self.assertEqual(len(Packer("P1", self.records, self.units, self.documents).pack(ranked, 10 ** 6)["blocks"]), 1, "P1 adds nothing")

    def test_kb_records_keep_their_claim_lines_in_the_body(self):
        unit = next(u for u in self.units if u["unit_id"].endswith("article-2/clause-1"))
        sentence = {"start": unit["source_start"], "end": unit["source_end"] - 1}
        claim = {"claim_id": "c1", "unit_id": unit["unit_id"], "sentence": sentence, "modality": "obligation", "slots": {"actor": "Bên A"}}
        records = kb_unit_records("DK3", self.documents, self.units, self.texts, [claim], view="compact")
        record = next(r for r in records if r["claim_ids"])
        packed = Packer("P1", records, self.units, self.documents).pack([record], 10 ** 6)
        self.assertTrue(packed["blocks"][0]["text"].endswith("[Quy phạm 1] nghĩa vụ · Chủ thể: Bên A"))

    def test_article_packing_rejects_chunks(self):
        from legal_ai.indexing.records import fixed_chunks
        with self.assertRaisesRegex(ValueError, "one leaf unit"):
            Packer("P1", fixed_chunks(self.documents, self.units, self.texts, 400, 10), self.units, self.documents)

    def test_p0_to_p2_outputs_are_unchanged_by_p3(self):
        # Digest of every P0/P1/P2 packing of four rankings at budgets 0..396, computed with pack-article-v1 before P3
        # existed (commit 7937811); P3 must not change what earlier runs packed.
        orders = [self.records, list(reversed(self.records)), self.records[2:] + self.records[:2], self.records[1::2] + self.records[::2]]
        out = []
        for mode in ("P0", "P1", "P2"):
            packer = Packer(mode, self.records, self.units, self.documents)
            for order in orders:
                for budget in range(0, 400, 9):
                    packed = packer.pack(order, budget)
                    self.assertNotIn("leads", packed)
                    out.append({"groups": packed["groups"], "tokens": packed["tokens"], "next": packed["next_budget"],
                                "blocks": [{k: (v["record_id"] if k == "record" else v) for k, v in b.items()} for b in packed["blocks"]]})
        self.assertEqual(digest(canonical(out)), "fbc64e0952e9d74733a06701d459e874ee237643abf791f8e85fb546c6af2611")


class TreePackingTests(unittest.TestCase):
    """P3: the P2 selection in a tree layout (Clause lead once, Points under it) with the short document name."""

    def setUp(self):
        self.documents, self.units, self.texts = bundle(None, {"syn-a": SYNTHETIC, "syn-b": SECOND})
        self.documents[0]["title"] = "Nghị định số 1/2020/NĐ-CP Quy định giả định về tiền lương"
        self.records = structural_records(self.documents, self.units, self.texts)
        self.by_unit = {r["unit_ids"][0]: r for r in self.records}
        self.p2 = Packer("P2", self.records, self.units, self.documents)
        self.p3 = Packer("P3", self.records, self.units, self.documents)

    def ranked(self, *suffixes):
        return [self.by_unit[f"syn-a/chapter-i/{s}"] for s in suffixes]

    def test_short_title_cuts_after_the_document_number(self):
        cases = {
            "Nghị định số 145/2020/NĐ-CP Quy định chi tiết và hướng dẫn thi hành một số điều của Bộ luật Lao động": "Nghị định số 145/2020/NĐ-CP",
            "Thông tư số 10/2020/TT-BLĐTBXH Quy định chi tiết": "Thông tư số 10/2020/TT-BLĐTBXH",
            "Nghị định số 70/2023/NĐ-CP Sửa đổi, bổ sung một số điều của Nghị định số 152/2020/NĐ-CP": "Nghị định số 70/2023/NĐ-CP",
            "Bộ Luật lao động số 45/2019/QH14": "Bộ Luật lao động số 45/2019/QH14",
            "Luật An toàn, vệ sinh lao động số 84/2015/QH13": "Luật An toàn, vệ sinh lao động số 84/2015/QH13",
            "Văn bản giả định syn-a": "Văn bản giả định syn-a",
            "Quy định về số lượng người lao động": "Quy định về số lượng người lao động",
        }
        for title, expected in cases.items():
            self.assertEqual(short_title(title), expected, title)

    def test_clause_lead_is_printed_once_and_points_keep_their_own_ids(self):
        ranked = self.ranked("article-2/clause-2/point-b", "article-2/clause-2/point-a", "article-1/clause-1")
        packed = Packer("P3", self.records, self.units, self.documents).pack(ranked, 10 ** 6)
        lead = "Khoản 2\n2. Tiền lương được trả bằng tiền mặt hoặc chuyển khoản, trừ trường hợp hai bên có thỏa thuận khác:"
        self.assertEqual([x["text"] for x in packed["leads"]], [lead])
        points = [b for b in packed["blocks"] if b["lead"] is not None]
        self.assertEqual([b["text"].split("\n")[0] for b in points], ["Điểm a", "Điểm b"])
        for block in points:
            self.assertNotIn("thỏa thuận khác", block["text"], "a Point no longer repeats its Clause lead")
            self.assertEqual(block["record"]["unit_ids"][0].rsplit("/", 1)[0], "syn-a/chapter-i/article-2/clause-2")
        ids = [b["id"] for b in packed["blocks"]]
        self.assertEqual(ids, [f"E{n:02d}" for n in range(1, len(ids) + 1)], "block IDs are unique and follow the reading order")
        self.assertEqual(packed["groups"][0]["header"], "Nghị định số 1/2020/NĐ-CP\nChương I > Điều 2\nĐiều 2. Tiền lương giả định")
        self.assertEqual(packed["tokens"], sum(g["header_tokens"] for g in packed["groups"]) + sum(x["tokens"] for x in packed["leads"])
                         + sum(b["token_count"] for b in packed["blocks"]), "headers and leads are counted once")
        payload = evidence_payload(packed)

        def read(node):  # Every text the generator reads in the payload: group and lead `source`, passage `text`.
            if isinstance(node, list):
                return [t for item in node for t in read(item)]
            return [node[k] for k in ("source", "text") if k in node] + read(node.get("passages", []))
        self.assertEqual(packed["tokens"], sum(len(token_spans(t)) for t in read(payload)), "the budget counts exactly what is printed")
        self.assertEqual(sum(t == lead for t in read(payload)), 1, "the lead is printed once")
        nested = payload[0]["passages"][1]
        self.assertEqual((nested["source"], [p["id"] for p in nested["passages"]]), (lead, ["E02", "E03"]))
        self.assertEqual([p["id"] for p in payload[0]["passages"] if "id" in p], ["E01"])

    def test_p3_keeps_the_p2_selection_and_order_and_costs_no_more(self):
        rankings = [self.ranked("article-2/clause-2/point-b", "article-1/clause-2", "article-3"), self.ranked("article-2/clause-1"),
                    list(reversed(self.records)), self.records]
        for ranked in rankings:
            two, three = self.p2.pack(ranked, 10 ** 6), self.p3.pack(ranked, 10 ** 6)
            self.assertEqual([(b["id"], b["record"]["record_id"], b["group"], b["sibling"]) for b in three["blocks"]],
                             [(b["id"], b["record"]["record_id"], b["group"], b["sibling"]) for b in two["blocks"]])
            self.assertLessEqual(three["tokens"], two["tokens"])
        shared = self.ranked("article-2/clause-2/point-a")
        self.assertLess(self.p3.pack(shared, 10 ** 6)["tokens"], self.p2.pack(shared, 10 ** 6)["tokens"],
                        "two Points of one Clause share a lead")

    def test_budget_is_never_exceeded_and_no_unit_repeats(self):
        ranked = self.ranked("article-2/clause-2/point-b", "article-1/clause-2", "article-2/clause-2/point-a", "article-1/clause-1", "article-3")
        full = self.p3.pack(ranked, 10 ** 6)["tokens"]
        for budget in range(0, full + 5):
            packed = self.p3.pack(ranked + ranked, budget)
            self.assertTrue(len(packed["blocks"]) == 1 or packed["tokens"] <= budget, budget)
            units = [b["record"]["unit_ids"][0] for b in packed["blocks"]]
            self.assertEqual(len(units), len(set(units)), budget)
            self.assertEqual(len({(x["group"], x["text"]) for x in packed["leads"]}), len(packed["leads"]), "a lead is printed once per group")
            for number, lead in enumerate(packed["leads"]):
                first = min(n for n, b in enumerate(packed["blocks"]) if b["lead"] == number)
                self.assertTrue(all(b["lead"] == number for b in packed["blocks"][first:first + sum(b["lead"] == number for b in packed["blocks"])]),
                                "the Points of one lead are contiguous")
                self.assertEqual(packed["blocks"][first]["group"], lead["group"])

    def test_siblings_pass_admit_and_sibling_cap_counts_leads(self):
        ranked = self.ranked("article-2/clause-1")
        packed = self.p3.pack(ranked, 10 ** 6)
        self.assertEqual([b["sibling"] for b in packed["blocks"]], [False, True, True])
        self.assertLessEqual(packed["tokens"], SIBLING_GROUP_TOKENS)
        dropped = self.by_unit["syn-a/chapter-i/article-2/clause-2/point-a"]["record_id"]
        filtered = self.p3.bind(lambda r: [] if r["record_id"] == dropped else [r]).pack(ranked, 10 ** 6)
        self.assertNotIn(dropped, [b["record"]["record_id"] for b in filtered["blocks"]])
        self.assertEqual(len(filtered["leads"]), 1, "the lead still comes with the remaining Point")

    def test_records_with_their_own_layout_get_the_short_name(self):
        record = dict(self.by_unit["syn-a/chapter-i/article-2/clause-1"])
        title = self.documents[0]["title"]
        record["pack_layout"] = {"group": ["syn-a", "syn-a/chapter-i/article-2"], "header": f"{title}\nChương I > Điều 2", "body": "Khoản 1\n[Quy phạm 1] x"}
        packed = Packer("P3", [record], self.units, self.documents).pack([record], 10 ** 6)
        self.assertEqual(packed["groups"][0]["header"], "Nghị định số 1/2020/NĐ-CP\nChương I > Điều 2")
        self.assertEqual((packed["leads"], packed["blocks"][0]["lead"]), ([], None))
        self.assertEqual(Packer("P2", [record], self.units, self.documents).pack([record], 10 ** 6)["groups"][0]["header"], f"{title}\nChương I > Điều 2")


class TopArticlePackingTests(unittest.TestCase):
    """P4: P3, except that the top-ranked Article is printed with all its leaves up to a larger cap."""

    def setUp(self):
        self.documents, self.units, self.texts = bundle(None, {"syn-a": SYNTHETIC, "syn-b": SECOND})
        self.records = structural_records(self.documents, self.units, self.texts)
        self.by_unit = {r["unit_ids"][0]: r for r in self.records}
        self.p3 = Packer("P3", self.records, self.units, self.documents)
        self.p4 = Packer("P4", self.records, self.units, self.documents)
        self.article2 = [r for r in self.records if r["unit_ids"][0].startswith("syn-a/chapter-i/article-2")]

    def ranked(self, *suffixes):
        return [self.by_unit[f"syn-a/chapter-i/{s}"] for s in suffixes]

    def caps(self, sibling, top):
        return mock.patch.multiple(packing, SIBLING_GROUP_TOKENS=sibling, TOP_ARTICLE_TOKENS=top)

    def test_defaults_and_mode_are_declared(self):
        self.assertEqual((packing.TOP_ARTICLE_TOKENS, packing.SIBLING_GROUP_TOKENS), (1000, 400))
        self.assertTrue(self.p4.adds_siblings)
        self.assertEqual(condition_mode("DK3", "P4"), "P4")

    def test_with_the_default_caps_a_small_article_packs_exactly_as_p3(self):
        for ranked in (self.ranked("article-2/clause-1"), self.ranked("article-1/clause-2", "article-2/clause-2/point-b"), self.records):
            one, two = self.p3.pack(ranked, 10 ** 6), self.p4.pack(ranked, 10 ** 6)
            self.assertEqual({k: v for k, v in one.items()}, {k: v for k, v in two.items()})

    def test_top_article_is_printed_whole_within_its_cap_and_the_others_as_p3(self):
        ranked = self.ranked("article-2/clause-1", "article-1/clause-1")
        full = self.p4.pack(self.ranked("article-2/clause-1"), 10 ** 6)
        whole = full["tokens"]
        with self.caps(sibling=whole - 1, top=whole):
            three, four = self.p3.pack(ranked, 10 ** 6), self.p4.pack(ranked, 10 ** 6)
        top = lambda packed: [b["record"]["unit_ids"][0] for b in packed["blocks"] if b["group"] == 0]
        self.assertEqual(top(four), sorted(r["unit_ids"][0] for r in self.article2), "every leaf of the top Article, in text order")
        self.assertLess(len(top(three)), len(top(four)), "P3 cuts the same block at the lower cap")
        self.assertLessEqual(four["groups"][0]["header_tokens"] + sum(b["token_count"] for b in four["blocks"] if b["group"] == 0)
                             + sum(x["tokens"] for x in four["leads"] if x["group"] == 0), whole)
        rest = lambda packed: [(b["record"]["record_id"], b["sibling"]) for b in packed["blocks"] if b["group"] != 0]
        self.assertEqual(rest(three), rest(four), "the other Articles are packed as in P3")

    def test_top_cap_applies_to_the_first_article_only(self):
        ranked = self.ranked("article-1/clause-1", "article-2/clause-1")
        with self.caps(sibling=1, top=10 ** 6):
            packed = self.p4.pack(ranked, 10 ** 6)
        groups = {}
        for b in packed["blocks"]:
            groups.setdefault(b["group"], []).append(b["sibling"])
        self.assertGreater(len(groups[0]), 1)
        self.assertEqual(groups[1], [False], "the second Article gets no sibling at a tiny cap")

    def test_ids_unique_budget_respected_and_no_unit_repeats(self):
        ranked = self.ranked("article-2/clause-2/point-b", "article-1/clause-2", "article-2/clause-2/point-a", "article-1/clause-1", "article-3")
        full = self.p4.pack(ranked, 10 ** 6)["tokens"]
        with self.caps(sibling=SIBLING_GROUP_TOKENS, top=10 ** 6):
            for budget in range(0, full + 5):
                packed = self.p4.pack(ranked + ranked, budget)
                self.assertTrue(len(packed["blocks"]) == 1 or packed["tokens"] <= budget, budget)
                units = [b["record"]["unit_ids"][0] for b in packed["blocks"]]
                self.assertEqual(len(units), len(set(units)), budget)
                ids = [b["id"] for b in packed["blocks"]]
                self.assertEqual(ids, [f"E{n:02d}" for n in range(1, len(ids) + 1)])
                self.assertEqual(packed["tokens"], sum(g["header_tokens"] for g in packed["groups"]) + sum(x["tokens"] for x in packed["leads"])
                                 + sum(b["token_count"] for b in packed["blocks"]))

    def test_validity_admission_applies_to_the_added_units(self):
        ranked = self.ranked("article-2/clause-1")
        dropped = self.by_unit["syn-a/chapter-i/article-2/clause-2/point-a"]["record_id"]
        with self.caps(sibling=1, top=10 ** 6):
            plain = self.p4.pack(ranked, 10 ** 6)
            filtered = self.p4.bind(lambda r: [] if r["record_id"] == dropped else [r]).pack(ranked, 10 ** 6)
        self.assertIn(dropped, [b["record"]["record_id"] for b in plain["blocks"]])
        self.assertNotIn(dropped, [b["record"]["record_id"] for b in filtered["blocks"]])
        self.assertTrue(self.p4.bind(lambda r: [r]).adds_siblings)

    def test_earlier_modes_do_not_see_the_top_cap(self):
        ranked = self.ranked("article-2/clause-1")
        for mode in ("P2", "P3"):
            packer = Packer(mode, self.records, self.units, self.documents)
            base = packer.pack(ranked, 10 ** 6)
            with self.caps(sibling=SIBLING_GROUP_TOKENS, top=1):
                self.assertEqual(packer.pack(ranked, 10 ** 6), base)


class BudgetCurveTests(unittest.TestCase):
    def setUp(self):
        self.documents, self.units, self.texts = bundle(None, {"syn-a": SYNTHETIC})
        self.records = structural_records(self.documents, self.units, self.texts)

    def test_recall_steps_agree_with_recall_at_every_budget(self):
        gold = ["syn-a/chapter-i/article-2", "syn-a/chapter-i/article-3"]
        for mode in ("P0", "P1", "P2", "P3"):
            packer = Packer(mode, self.records, self.units, self.documents)
            steps = recall_steps(self.records, gold, packer)
            self.assertEqual([t for t, _ in steps], sorted({t for t, _ in steps}), "breakpoints grow strictly")
            for budget in range(0, steps[-1][0] + 20, 3):
                expected = score_top(self.records, gold, [1], [budget], packer=packer)["recall_at_tokens"][str(budget)]
                at = [r for t, r in steps if t <= budget]
                self.assertEqual(at[-1] if at else steps[0][1], expected, (mode, budget))

    def test_tokens_to_reach_is_the_smallest_budget_of_the_mean_curve(self):
        steps = [[(10, 0.0), (30, 1.0)], [(20, 0.5), (40, 1.0)]]
        self.assertEqual(tokens_to_reach(steps, 0.25), 10, "the first record is always kept, even under its cost")
        self.assertEqual(tokens_to_reach(steps, 0.75), 30)
        self.assertEqual(tokens_to_reach(steps, 1.0), 40)
        self.assertIsNone(tokens_to_reach([[(10, 0.2)]], 0.5))

    def test_expanded_head_is_kept_and_the_tail_follows_unexpanded(self):
        from legal_ai.evaluation.retrieval_run import extend_tail
        head = [(3, 0.9), (7, 0.0), (1, 0.8)]
        ranked = [(3, 0.9), (1, 0.8), (5, 0.7), (7, 0.6), (2, 0.5)]
        self.assertEqual(extend_tail(head, ranked, 10), head + [(5, 0.7), (2, 0.5)])
        self.assertEqual(extend_tail(head, ranked, 4), head + [(5, 0.7)])

    def test_within_budget_p0_matches_the_old_rule(self):
        kept = within_budget(self.records, 60)
        used = 0
        for row in kept:
            used += len(token_spans(row["index_text"]))
        self.assertTrue(used <= 60 or len(kept) == 1)
        self.assertEqual(kept, self.records[:len(kept)])


class RunIntegrationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        bundle(self.root / "bundle", {"syn-a": SYNTHETIC})
        self.questions = self.root / "q.json"
        write_json(self.questions, {"questions": [
            {"question_id": "Q1", "question": "Tiền lương trả bằng tiền mặt hay chuyển khoản?", "relevant_unit_ids": ["syn-a/chapter-i/article-2"]}]})
        self.dk1, self.dk2 = self.root / "dk1.json", self.root / "dk2.json"
        write_json(self.dk1, {"condition": "DK1", "representation": "fixed_chunks", "chunk_tokens": 30, "overlap_tokens": 5})
        write_json(self.dk2, {"condition": "DK2", "representation": "structural_units", "max_tokens": 384})

    def shared(self, mode):
        path = self.root / f"shared-{mode}.json"
        write_json(path, {"top_k": 2, "context_packing": mode, "token_budgets": [40, 80],
                          "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75, "recall_k": [1, 3]}})
        return path

    def test_runs_record_packing_budgets_and_tokens_to_reach(self):
        metrics = run(self.root / "bundle", self.questions, self.dk2, self.shared("P1"), self.root / "dk2-p1")
        manifest = json.loads((self.root / "dk2-p1" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["context_packing"], {"version": "pack-article-v1", "mode": "P1"})
        self.assertEqual((manifest["token_budgets"], metrics["context_packing"]), ([40, 80], "P1"))
        self.assertEqual(set(metrics["tokens_to_reach"]), {"0.4", "0.8"})
        self.assertIn("mean_complete_at_tokens", metrics)
        dk1 = run(self.root / "bundle", self.questions, self.dk1, self.shared("P1"), self.root / "dk1-p1")
        self.assertEqual(dk1["context_packing"], "P0", "DK1 is always flat")
        report = check([self.root / "dk1-p1", self.root / "dk2-p1"])
        self.assertEqual(next(c for c in report["checks"] if c["check"] == "DK2-DK4 use the same context packing")["status"], "pass")

    def test_preflight_fails_when_structural_conditions_pack_differently(self):
        run(self.root / "bundle", self.questions, self.dk2, self.shared("P1"), self.root / "a")
        dk3 = self.root / "dk3.json"
        write_json(dk3, {"condition": "DK2", "representation": "structural_units", "max_tokens": 384})
        run(self.root / "bundle", self.questions, dk3, self.shared("P2"), self.root / "b")
        report = check([self.root / "a", self.root / "b"])
        self.assertEqual(next(c for c in report["checks"] if c["check"] == "DK2-DK4 use the same context packing")["status"], "fail")
        self.assertEqual(next(c for c in report["checks"] if c["check"] == "same retrieval settings")["status"], "fail")

    def test_answer_packing_matches_retrieval_packing(self):
        for mode in ("P2", "P3"):
            run(self.root / "bundle", self.questions, self.dk2, self.shared(mode), self.root / f"dk2-{mode}")
            retrieval = json.loads((self.root / f"dk2-{mode}" / "manifest.json").read_text(encoding="utf-8"))
            records = {r["record_id"]: r for r in read_jsonl(self.root / f"dk2-{mode}" / "records.jsonl")}
            prediction = read_jsonl(self.root / f"dk2-{mode}" / "predictions.jsonl")[0]
            packer = packer_for(retrieval, list(records.values()))
            self.assertEqual(packer.mode, mode)
            for budget in (40, 80, 200):
                blocks, packed = pack_with_groups(prediction["ranked"], records, 50, budget, packer)
                self.assertEqual([b["record_id"] for b in blocks],
                                 [r["record_id"] for r in within_budget([records[x["record_id"]] for x in prediction["ranked"]], budget, packer)])
                leads = sum(x["tokens"] for x in packed.get("leads", []))
                self.assertEqual(packed["tokens"], sum(g["header_tokens"] for g in packed["groups"]) + leads + sum(b["token_count"] for b in blocks))
                if str(budget) in prediction["recall_at_tokens"]:
                    self.assertEqual(_recall([records[b["record_id"]] for b in blocks], prediction["gold_unit_ids"]),
                                     prediction["recall_at_tokens"][str(budget)], "the answer reads what the budget recall scored")

    def test_answer_run_with_p3_sends_nested_leads_and_records_them(self):
        from test_answer_run import StandIn
        from legal_ai.evaluation.answer_run import run as answer_run
        write_json(self.questions, {"questions": [{"question_id": "Q1", "question": "Tiền lương trả theo tuần khi làm việc theo giờ?",
                                                   "relevant_unit_ids": ["syn-a/chapter-i/article-2/clause-2/point-b"]}]})
        run(self.root / "bundle", self.questions, self.dk2, self.shared("P3"), self.root / "dk2")
        config = self.root / "answer.json"
        write_json(config, {"prompt": "answer-v4.md", "top_k": 50, "context_token_budget": 300})
        provider = StandIn()
        answer_run(self.root / "dk2", self.questions, config, provider, self.root / "answers")
        row = read_jsonl(self.root / "answers" / "answers.jsonl")[0]
        evidence = provider.prompts[0]["evidence"]
        nested = [p for g in evidence for p in g["passages"] if "passages" in p]
        self.assertTrue(nested and nested[0]["source"].startswith("Khoản 2\n2. Tiền lương được trả"), evidence)
        self.assertEqual(len(row["context_leads"]), len(nested), "one recorded lead per nested Clause")
        cited = [b for b in row["context"] if "lead" in b]
        self.assertTrue(cited and all(row["context_leads"][b["lead"]]["group"] == b["group"] for b in cited))
        self.assertEqual(row["context_tokens"], sum(g["header_tokens"] for g in row["context_groups"]) + sum(x["lead_tokens"] for x in row["context_leads"])
                         + sum(b["token_count"] for b in row["context"]))
        self.assertLessEqual(row["context_tokens"], 300)
        self.assertEqual(json.loads((self.root / "answers" / "manifest.json").read_text(encoding="utf-8"))["context_packing"]["mode"], "P3")

    def test_preflight_accepts_p3_and_fails_when_p2_and_p3_mix(self):
        run(self.root / "bundle", self.questions, self.dk1, self.shared("P3"), self.root / "dk1")
        run(self.root / "bundle", self.questions, self.dk2, self.shared("P3"), self.root / "dk2")
        dk3 = self.root / "dk3.json"
        write_json(dk3, {"condition": "DK2", "representation": "structural_units", "max_tokens": 384})
        status = lambda report, name: next(c for c in report["checks"] if c["check"] == name)["status"]
        report = check([self.root / "dk1", self.root / "dk2"])
        self.assertEqual(status(report, "DK2-DK4 use the same context packing"), "pass")
        run(self.root / "bundle", self.questions, dk3, self.shared("P2"), self.root / "dk3")
        report = check([self.root / "dk1", self.root / "dk2", self.root / "dk3"])
        self.assertEqual(status(report, "DK2-DK4 use the same context packing"), "fail")


class SharedConfigTests(unittest.TestCase):
    def test_rrf100_config_differs_from_shared_only_in_fusion_depth_and_packing(self):
        read = lambda name: json.loads((ROOT / "configs" / "experiments" / name).read_text(encoding="utf-8"))
        base, candidate = read("shared.json"), read("shared-rrf100.json")
        self.assertEqual(candidate["retrieval"], base["retrieval"] | {"rrf_candidates": 100})
        self.assertEqual(condition_mode("DK2", candidate["context_packing"]), "P3")
        self.assertEqual({k: v for k, v in candidate.items() if k not in {"retrieval", "context_packing", "note"}},
                         {k: v for k, v in base.items() if k not in {"retrieval", "note"}})


class VerificationLoadTests(unittest.TestCase):
    def test_cited_tokens_and_single_leaf_citations(self):
        units = {"a": {"unit_id": "a", "parent_id": None}, "a/1": {"unit_id": "a/1", "parent_id": "a"}, "a/2": {"unit_id": "a/2", "parent_id": "a"}}
        records = {"r1": {"unit_ids": ["a/1"]}, "r2": {"unit_ids": ["a", "a/1", "a/2"]}}
        answers = [
            {"status": "answered", "context": [{"id": "E01", "record_id": "r1", "unit_ids": ["a/1"], "token_count": 10, "group": 0},
                                               {"id": "E02", "record_id": "r2", "unit_ids": ["a", "a/1", "a/2"], "token_count": 30, "group": 0}],
             "context_groups": [{"header_tokens": 5}],
             "statements": [{"evidence_ids": ["E01"]}, {"evidence_ids": ["E01", "E02"]}]},
            {"status": "insufficient_evidence", "context": [], "statements": []},
        ]
        load = verification_load(answers, records, units)
        self.assertEqual(load["cited_tokens_per_statement"], ((10 + 5) + (40 + 5)) / 2)
        self.assertEqual((load["single_leaf_citation_rate"], load["citations"]), (2 / 3, 3))

    def test_p3_clause_leads_are_counted_once_per_statement(self):
        units = {"a": {"unit_id": "a", "parent_id": None}, "a/1": {"unit_id": "a/1", "parent_id": "a"},
                 "a/1/x": {"unit_id": "a/1/x", "parent_id": "a/1"}, "a/1/y": {"unit_id": "a/1/y", "parent_id": "a/1"}}
        records = {"r1": {"unit_ids": ["a/1/x"]}, "r2": {"unit_ids": ["a/1/y"]}}
        answers = [{"status": "answered", "context_groups": [{"header_tokens": 5}], "context_leads": [{"group": 0, "lead_tokens": 7}],
                    "context": [{"id": "E01", "record_id": "r1", "unit_ids": ["a/1/x"], "token_count": 10, "group": 0, "lead": 0},
                                {"id": "E02", "record_id": "r2", "unit_ids": ["a/1/y"], "token_count": 20, "group": 0, "lead": 0}],
                    "statements": [{"evidence_ids": ["E01", "E02"]}, {"evidence_ids": ["E02"]}]}]
        load = verification_load(answers, records, units)
        self.assertEqual(load["cited_tokens_per_statement"], ((30 + 5 + 7) + (20 + 5 + 7)) / 2)
        self.assertEqual(load["single_leaf_citation_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
