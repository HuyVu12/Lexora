"""Semantic span extraction tests on explicitly synthetic legal text."""

from copy import deepcopy
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from legal_ai.extraction.norms import extract_norms
from legal_ai.ingestion.parser import parse
from legal_ai.kb.graph import make_graph
from legal_ai.normalization.text import normalize
from legal_ai.schemas.contract import VERSION, validate_claim
from legal_ai.validation.evidence import validate_record, check_evidence


def fixture(text):
    normalized = normalize(text)
    document = {"schema_version": VERSION, "document_id": "synthetic", "document_version_id": normalized["normalized_sha256"], "snapshot_id": "0" * 64, "source_sha256": "0" * 64, "title": "SYNTHETIC — NOT REAL LAW", "source_url": "fixture://norms", "accessed_at": "2026-11-03T00:00:00Z", "effective_from": None, "effective_to": None, "legal_status": "unknown", "synthetic": True}
    return document, parse(normalized, "synthetic", document["document_version_id"])["units"]


class NormTests(unittest.TestCase):
    def extracted(self, body):
        _, units = fixture("Điều 1. Quy tắc giả định\n" + body + "\n")
        claims, evidence, report = extract_norms(units)
        return units, claims, evidence, report

    def test_actor_action_condition_exception_deadline_and_modal_have_spans(self):
        units, claims, evidence, report = self.extracted("Trong trường hợp A, chủ thể B phải thực hiện C trong 7 ngày, trừ trường hợp D.")
        self.assertEqual(len(claims), 1)
        claim = claims[0]
        expected = {"actor": "chủ thể B", "action": "thực hiện C", "conditions": "Trong trường hợp A", "deadlines": "trong 7 ngày", "exceptions": "trừ trường hợp D"}
        for name, text in expected.items():
            self.assertEqual(claim["slots"][name]["text"], text)
        self.assertEqual(claim["modality"], "obligation")
        for row in evidence:
            self.assertEqual(check_evidence(row, units), [])
        self.assertEqual(validate_record(claim, evidence, units)["decision"], "needs_review")

    def test_graph_has_typed_entity_and_qualifier_relations(self):
        document, units = fixture("Điều 1. Giả định\nTrong trường hợp A, B phải làm C trong 7 ngày, trừ trường hợp D.\n")
        graph = make_graph([document], units, [], [], include_candidates=True, extraction_mode="norm-rules-v1")
        kinds = {edge["kind"] for edge in graph["edges"]}
        self.assertTrue({"HAS_ACTOR", "HAS_ACTION", "HAS_CONDITION", "HAS_EXCEPTION", "HAS_DEADLINE", "HAS_MODALITY"} <= kinds)
        self.assertTrue({"Entity", "Action", "Condition", "Exception", "Deadline", "Modality"} <= {node["kind"] for node in graph["nodes"]})
        self.assertEqual(graph["summary"]["claim_decisions"], {"needs_review": 1})

    def test_prohibition_is_not_obligation(self):
        _, claims, _, _ = self.extracted("Chủ thể A không được làm B.")
        self.assertEqual(claims[0]["modality"], "prohibition")
        self.assertEqual(claims[0]["slots"]["action"]["text"], "làm B")

    def test_negative_obligation_and_passive_possibility_are_not_mislabeled(self):
        for body in ("Chủ thể A không phải làm B.", "Chủ thể A không bắt buộc phải làm B.", "Chủ thể A có thể bị xử lý."):
            _, claims, _, report = self.extracted(body)
            self.assertTrue(all(claim["modality"] == "unknown" for claim in claims))
            self.assertEqual(sum(row["structured_claim_count"] for row in report), 0)

    def test_joint_actor_and_disjunctive_action_not_split_into_inferred_rights(self):
        _, claims, _, _ = self.extracted("A và B có thể làm C hoặc thực hiện D.")
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0]["slots"]["actor"]["text"], "A và B")
        self.assertEqual(claims[0]["slots"]["action"]["text"], "làm C hoặc thực hiện D")

    def test_working_days_parent_scope_and_unknown_actor_are_retained(self):
        _, units = fixture("Điều 1. Giả định\nChỉ áp dụng trong phạm vi A, trừ trường hợp B:\n1. Không quá 06 ngày làm việc đối với công việc khác.\n")
        claims, evidence, _ = extract_norms(units)
        claim = claims[0]
        self.assertEqual(claim["slots"]["quantities"]["text"], "Không quá 06 ngày làm việc")
        self.assertIn("trừ trường hợp B", claim["slots"]["scope"]["text"])
        self.assertEqual(claim["slots"]["actor"]["state"], "unknown")
        self.assertEqual(claim["modality"], "unknown")
        self.assertEqual(len(claim["source_unit_version_ids"]), 2)
        self.assertEqual(validate_record(claim, evidence, units)["decision"], "needs_review")

    def test_calendar_unspecified_days_not_changed_to_working_days(self):
        _, claims, _, _ = self.extracted("Không quá 60 ngày đối với công việc A.")
        self.assertEqual(claims[0]["slots"]["quantities"]["text"], "Không quá 60 ngày")

    def test_salary_actor_not_invented_and_bound_keeps_basis(self):
        units, claims, evidence, _ = self.extracted("Tiền lương của người lao động trong thời gian thử việc do hai bên thỏa thuận nhưng ít nhất phải bằng 85% mức lương của công việc đó.")
        claim = claims[0]
        self.assertEqual(claim["slots"]["actor"]["state"], "unknown")
        self.assertEqual(claim["slots"]["beneficiary"]["text"], "người lao động")
        self.assertEqual(claim["slots"]["quantities"]["text"], "ít nhất phải bằng 85% mức lương của công việc đó")
        self.assertEqual(validate_record(claim, evidence, units)["decision"], "needs_review")

    def test_unparsed_conditional_branch_is_reported(self):
        _, claims, _, report = self.extracted("A phải làm B. Trường hợp C thì D xảy ra.")
        self.assertEqual(len(claims), 1)
        self.assertTrue(any("Trường hợp C" in sentence["text"] for row in report for sentence in row["unparsed_sentences"]))
        self.assertEqual(claims[0]["completeness"], "unknown")

    def test_explicit_recipient_is_a_separate_evidence_span(self):
        _, claims, _, _ = self.extracted("Khi kết thúc thời gian thử việc, người sử dụng lao động phải thông báo kết quả thử việc cho người lao động.")
        claim = claims[0]
        self.assertEqual(claim["slots"]["actor"]["text"], "người sử dụng lao động")
        self.assertEqual(claim["slots"]["recipient"]["text"], "người lao động")
        self.assertEqual(claim["slots"]["beneficiary"]["state"], "unknown")
        self.assertEqual(claim["slots"]["action"]["text"], "thông báo")
        self.assertEqual(claim["slots"]["object"]["text"], "kết quả thử việc")
        self.assertNotEqual(claim["slots"]["actor"]["evidence_ids"], claim["slots"]["recipient"]["evidence_ids"])

    def test_tampered_modality_is_rejected(self):
        units, claims, evidence, _ = self.extracted("A phải làm B.")
        claim = deepcopy(claims[0])
        claim["modality"] = "permission"
        self.assertIn("modality_evidence_mismatch", validate_record(claim, evidence, units)["reasons"])

    def test_same_surface_actor_is_not_globally_merged(self):
        document, units = fixture("Điều 1. Giả định\nA phải làm B. A có quyền làm C.\n")
        graph = make_graph([document], units, [], [], include_candidates=True, extraction_mode="norm-rules-v1")
        actors = [node for node in graph["nodes"] if node["kind"] == "Entity"]
        self.assertEqual(len(actors), 2)
        self.assertNotEqual(actors[0]["id"], actors[1]["id"])

    def test_deterministic_under_unit_order(self):
        document, units = fixture("Điều 1. Giả định\n1. A phải làm B.\n2. C có quyền làm D.\n")
        first = make_graph([document], units, [], [], include_candidates=True, extraction_mode="norm-rules-v1")
        second = make_graph([document], list(reversed(units)), [], [], include_candidates=True, extraction_mode="norm-rules-v1")
        self.assertEqual(first, second)

    def test_optional_modality_evidence_cannot_be_missing_for_known_value(self):
        _, claims, _, _ = self.extracted("A phải làm B.")
        claim = deepcopy(claims[0])
        claim["modality_evidence_ids"] = []
        with self.assertRaises(ValueError):
            validate_claim(claim)

    def test_cancellation_keeps_disjunction_and_negative_outcome(self):
        units, claims, evidence, _ = self.extracted("Trong thời gian thử việc, mỗi bên có quyền hủy bỏ hợp đồng thử việc hoặc hợp đồng lao động đã giao kết mà không cần báo trước và không phải bồi thường.")
        claim = claims[0]
        self.assertEqual(claim["slots"]["action"]["text"], "hủy bỏ")
        self.assertEqual(claim["slots"]["object"]["text"], "hợp đồng thử việc hoặc hợp đồng lao động đã giao kết")
        self.assertEqual(claim["slots"]["outcome"]["text"], "mà không cần báo trước và không phải bồi thường")
        self.assertEqual(claim["slots"]["exceptions"]["state"], "unknown")
        self.assertEqual(validate_record(claim, evidence, units)["decision"], "needs_review")

    def test_duration_object_is_anchored_to_parent_not_invented_in_child(self):
        _, units = fixture("Điều 1. Thời gian thử việc\nThời gian thử việc áp dụng theo phạm vi A:\n1. Không quá 06 ngày làm việc đối với công việc B.\n")
        claims, evidence, _ = extract_norms(units)
        claim = claims[0]
        self.assertEqual(claim["slots"]["object"]["text"], "Thời gian thử việc")
        anchor = next(row for row in evidence if row["evidence_id"] == claim["slots"]["object"]["evidence_ids"][0])
        self.assertEqual(anchor["unit_version_id"], units[0]["unit_version_id"])
