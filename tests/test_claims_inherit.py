"""Lead-in inheritance of knowledge-base claims (`claims-inherit-v1`). Synthetic text."""

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_retrieval_run import bundle
from legal_ai.evaluation import extraction_gold as gold, kb_run
from legal_ai.extraction.inherit import VERSION as INHERIT_VERSION, analyse, inherit, lead_in
from legal_ai.extraction.llm_norms import LLM_SLOTS
from legal_ai.validation.evidence import check_evidence

SANCTION_LEAD = "Phạt tiền từ 2.000.000 đồng đến 5.000.000 đồng đối với bên A có một trong các hành vi sau đây:"
LAW = ("Điều 1. Xử phạt giả định\n"
       f"1. {SANCTION_LEAD}\n"
       "a) Không thông báo kết quả thử việc cho bên B;\n"
       "b) Thu tiền của bên B.\n"
       "2. Bên B có các quyền sau đây:\n"
       "a) Chấm dứt thử việc;\n"
       "b) Nhận đủ tiền lương.\n"
       "3. Hằng năm, bên A, bên C phải thực hiện như sau:\n"
       "a) Báo cáo kết quả.\n"
       "4. Phạt tiền từ 12% đến 15% tổng số tiền đối với bên A có hành vi sau đây:\n"
       "a) Chậm đóng tiền.\n"
       "5. Bên A phải lập báo cáo như sau:\n"
       "a) Gửi bên C.\n"
       "Điều 2. Lương giả định\n"
       "Bên A có trách nhiệm trả lương như sau:\n"
       "1. Đúng hạn hằng tháng.\n"
       "2. Đủ tiền.\n")


def norm(sentence_text, modality="obligation", cue=None, **slots):
    """A model norm whose action is the sentence itself unless given."""
    base = {name: None for name in LLM_SLOTS}
    return base | {"action": sentence_text, "modality": modality, "modality_cue": cue} | slots


class Fixture(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.bundle = self.root / "bundle"
        self.documents, self.units, self.texts = bundle(self.bundle, {"syn": LAW})
        self.by_id = {u["unit_id"]: u for u in self.units}

    def unit(self, suffix):
        matches = [u for u in self.units if u["unit_id"].endswith(suffix)]
        self.assertEqual(len(matches), 1, suffix)
        return matches[0]

    def claim(self, suffix, number=0, **norm_fields):
        """A DK3 claim on the first sentence of a unit, shaped as `kb_run._claims` builds it."""
        unit = self.unit(suffix)
        start, end, text = kb_run.sentences(unit)[0]
        values = norm(text, **norm_fields)
        return {"claim_id": f"kb:{suffix}:{number}", "kb_version": kb_run.KB_VERSION, "document_id": unit["document_id"], "unit_id": unit["unit_id"],
                "unit_version_id": unit["unit_version_id"],
                "sentence": {"start": unit["source_start"] + start, "end": unit["source_start"] + end},
                "modality": values.pop("modality"), "modality_cue": values.pop("modality_cue"), "slots": values,
                "extraction": {"run_id": "kb-test"}}


class InheritTests(Fixture):
    def test_sanction_lead_in_gives_actor_and_outcome_with_contract_evidence(self):
        before = self.claim("clause-1/point-a", modality="prohibition")
        [after], report = inherit([before], self.units)
        parent = self.unit("article-1/clause-1")
        self.assertEqual(after["claim_id"], before["claim_id"])
        self.assertEqual(after["slots"]["actor"], "bên A")
        self.assertEqual(after["slots"]["outcome"], "Phạt tiền từ 2.000.000 đồng đến 5.000.000 đồng")
        self.assertEqual(after["slots"]["action"], before["slots"]["action"])  # A filled slot is never replaced.
        self.assertEqual(after["inheritance"]["version"], INHERIT_VERSION)
        self.assertEqual(after["inheritance"]["parent_unit_id"], parent["unit_id"])
        self.assertEqual({k: v["rule"] for k, v in after["inheritance"]["slots"].items()},
                         {"actor": "leadin-sanction-actor", "outcome": "leadin-sanction"})
        for name, entry in after["inheritance"]["slots"].items():
            row = entry["evidence"]
            self.assertEqual(check_evidence(row, self.units), [])
            self.assertEqual(parent["text"][row["start"]:row["end"]], row["quote"])
            self.assertEqual(row["quote"], after["slots"][name])
            self.assertEqual((row["unit_version_id"], row["normalized_sha256"]), (parent["unit_version_id"], parent["normalized_sha256"]))
            start, end = entry["span"]
            self.assertEqual(self.texts["syn"][start:end], row["quote"])
        self.assertNotIn("inheritance", before)  # The input claim is not mutated.
        self.assertEqual(report["claims_changed"], 1)
        self.assertEqual((report["actor_before"], report["actor_after"]), (0, 1))

    def test_subject_lead_in_needs_an_agreeing_modality(self):
        agree = self.claim("clause-2/point-a", modality="entitlement")
        unknown = self.claim("clause-2/point-b", modality="unknown")
        other = self.claim("clause-2/point-a", 1, modality="obligation")
        result, report = inherit([agree, unknown, other], self.units)
        self.assertEqual([c["slots"]["actor"] for c in result], ["Bên B", "Bên B", None])
        self.assertNotIn("inheritance", result[2])
        self.assertEqual(report["skipped_modality"], 1)
        self.assertNotIn("action", result[0]["inheritance"]["slots"])  # "có các quyền sau đây" has no verb phrase.

    def test_action_comes_from_the_lead_in_without_the_list_tail(self):
        empty = self.claim("article-2/clause-1", action=None, conditions="Đúng hạn hằng tháng")
        [after], _ = inherit([empty], self.units)
        self.assertEqual((after["slots"]["actor"], after["slots"]["action"]), ("Bên A", "trả lương"))
        self.assertEqual(after["inheritance"]["slots"]["action"]["rule"], "leadin-action")
        self.assertEqual(check_evidence(after["inheritance"]["slots"]["action"]["evidence"], self.units), [])

    def test_ambiguous_or_unplain_lead_ins_and_filled_slots_inherit_nothing(self):
        claims = [self.claim("clause-3/point-a"),  # Two commas after the condition: subject unclear.
                  self.claim("clause-4/point-a"),  # Amount is not "từ X đồng đến Y đồng".
                  self.claim("clause-1/point-b", actor="bên B", outcome="Thu tiền")]  # Already filled.
        result, report = inherit(claims, self.units)
        self.assertEqual(result, claims)
        self.assertEqual(report["claims_changed"], 0)
        self.assertEqual(analyse(*lead_in(self.unit("clause-3/point-a"), self.by_id)), ({}, set()))
        self.assertEqual(analyse(*lead_in(self.unit("clause-4/point-a"), self.by_id)), ({}, set()))

    def test_lead_in_is_the_parent_body_without_label_or_heading(self):
        parent, start, end = lead_in(self.unit("clause-1/point-a"), self.by_id)
        self.assertEqual(parent["text"][start:end], SANCTION_LEAD)
        parent, start, end = lead_in(self.unit("article-2/clause-1"), self.by_id)
        self.assertEqual(parent["text"][start:end], "Bên A có trách nhiệm trả lương như sau:")
        self.assertIsNone(lead_in(self.unit("article-1/clause-1"), self.by_id))  # Article 1 has a heading only.

    def test_rules_on_real_lead_in_shapes(self):
        cases = {
            "Người lao động có quyền đơn phương chấm dứt hợp đồng lao động không cần báo trước trong trường hợp sau đây:":
                {"actor": "Người lao động", "action": "đơn phương chấm dứt hợp đồng lao động không cần báo trước"},
            "Ngoài quy định tại khoản 1 Điều này, người sử dụng lao động có trách nhiệm:": {"actor": "người sử dụng lao động"},
            "Người sử dụng lao động khi thực hiện trang cấp phương tiện bảo vệ cá nhân phải bảo đảm các nguyên tắc sau đây:":
                {"actor": "Người sử dụng lao động", "action": "bảo đảm"},
            "Phạt tiền từ 75.000.000 đồng đến 90.000.000 đồng khi có một trong các hành vi sau đây:":
                {"outcome": "Phạt tiền từ 75.000.000 đồng đến 90.000.000 đồng"},
            "Phạt tiền đối với người sử dụng lao động có hành vi không đóng bảo hiểm theo một trong các mức sau đây:":
                {"outcome": "Phạt tiền", "actor": "người sử dụng lao động"},
            # Left empty: a cap after the amount, a thing as subject, a cue inside the condition, two sentences.
            "Phạt tiền từ 2.000.000 đồng đến 4.000.000 đồng khi vi phạm với mỗi người lao động nhưng tối đa không quá 75.000.000 đồng:": {},
            "Việc đánh giá kỹ năng nghề quốc gia phải tuân thủ các nguyên tắc sau đây:": {},
            "Trường hợp phải ngừng việc, người lao động được trả lương như sau:": {},
            "Sở có trách nhiệm chủ trì. Nội dung phương án phải bao gồm:": {},
        }
        for lead, expected in cases.items():
            parent = {"unit_type": "clause", "text": f"2. {lead}\n"}
            found, _ = analyse(parent, 3, 3 + len(lead))
            self.assertEqual({k: parent["text"][s:e] for k, (s, e, _) in found.items()}, expected, lead)


class GoldInheritedScoringTests(Fixture):
    """RQ1 `gold-inherited-v1`: the gold leaves lead-in values empty, so `ignore` scores without inherited slots."""

    def gold_rows(self):
        rows = gold.template(self.units, ["syn/article-1"])
        point = self.unit("clause-1/point-a")
        for row in rows:
            if row["unit_id"] == point["unit_id"]:
                row["norms"] = [{"modality": "prohibition", "modality_cue": None, "slots": {"action": row["text"]}}]
        return rows

    def test_ignore_removes_only_inherited_slots_and_default_scores_them(self):
        rows = self.gold_rows()
        model = self.claim("clause-2/point-a", modality="entitlement", actor="Bên B")  # Not in the sentence, but not inherited.
        claims, _ = inherit([self.claim("clause-1/point-a", modality="prohibition"), model], self.units)
        self.assertEqual(set(claims[0]["inheritance"]["slots"]), {"actor", "outcome"})
        self.assertNotIn("inheritance", claims[1])

        kept = {tuple(sorted(n["slots"])) for r in gold.claim_predictions(claims, rows, "ignore") for n in r["norms"]}
        self.assertEqual(kept, {("action",), ("action", "actor")}, "the model's own actor stays, the inherited actor and outcome go")
        self.assertEqual(gold.claim_predictions(claims, rows), gold.claim_predictions(claims, rows, "score"))
        with self.assertRaisesRegex(ValueError, "inherited"):
            gold.claim_predictions(claims, rows, "drop")

        scored = gold.score_claims(rows, claims, self.units)
        ignored = gold.score_claims(rows, claims, self.units, "ignore")
        self.assertEqual(scored["strict"]["norms"]["tp"], 0, "an inherited actor the gold left empty breaks the norm match")
        self.assertEqual(ignored["strict"]["norms"]["tp"], 1)
        self.assertEqual(scored["strict"]["per_slot"]["outcome"]["predicted"], 1)
        self.assertNotIn("outcome", ignored["strict"]["per_slot"])
        self.assertEqual({k: v for k, v in scored.items() if k != "inherited"}, gold.score(rows, gold.claim_predictions(claims, rows)))

        block = ignored["inherited"]
        self.assertEqual((block["scoring"], block["mode"], block["claims_with_inherited_slots"]), (gold.INHERITED_SCORING, "ignore", 1))
        self.assertEqual(block["total"], {"values": 2, "gold_slot_empty": 2, "gold_slot_empty_lead_in_verbatim": 2, "gold_sentence_without_norm": 0,
                                          "gold_slot_filled": 0, "gold_slot_filled_lenient_match": 0})
        self.assertEqual(scored["inherited"]["total"], block["total"], "the counts do not depend on the mode")

    def test_claims_without_inheritance_score_exactly_as_before(self):
        rows = self.gold_rows()
        claims = [self.claim("clause-1/point-a", modality="prohibition", actor="bên A")]
        before = gold.score(rows, gold.claim_predictions(claims, rows))
        self.assertEqual(gold.score_claims(rows, claims, self.units), before, "no inherited block, same numbers")
        ignored = gold.score_claims(rows, claims, self.units, "ignore")
        self.assertEqual({k: v for k, v in ignored.items() if k != "inherited"}, before)
        self.assertEqual(ignored["inherited"]["total"]["values"], 0)

    def test_gold_slot_filled_and_a_moved_span_are_counted_apart(self):
        rows = self.gold_rows()
        for row in rows:
            for item in row["norms"]:
                item["slots"]["outcome"] = None
        [claim], _ = inherit([self.claim("clause-1/point-a", modality="prohibition")], self.units)
        point = next(r for r in rows if r["unit_id"] == claim["unit_id"])
        point["norms"][0]["slots"]["actor"] = "bên B"  # The gold names an actor of the sentence; the inherited one does not match it.
        claim["inheritance"]["slots"]["outcome"]["span"] = [0, 5]  # Not inside the lead-in any more.
        block = gold.inherited_report([claim], rows, self.units)
        self.assertEqual(block["per_slot"]["actor"]["gold_slot_filled"], 1)
        self.assertEqual(block["per_slot"]["actor"]["gold_slot_filled_lenient_match"], 0)
        self.assertEqual((block["per_slot"]["outcome"]["gold_slot_empty"], block["per_slot"]["outcome"]["gold_slot_empty_lead_in_verbatim"]), (1, 0))


if __name__ == "__main__":
    unittest.main()
