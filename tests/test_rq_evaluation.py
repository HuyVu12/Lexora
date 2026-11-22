"""RQ1 extraction gold set and RQ2 planted errors. Synthetic text, stand-in model, not real law."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_claims_inherit import Fixture as LeadInFixture
from test_kb_run import StandIn, norm
from test_retrieval_run import bundle
from legal_ai.common.io import read_jsonl, write_json, write_jsonl
from legal_ai.evaluation import error_injection, extraction_gold as gold, kb_run
from legal_ai.extraction.inherit import inherit

LAW = ("Điều 1. Thử việc giả định\n"
       "1. Bên A phải thông báo kết quả thử việc cho bên B.\n"
       "2. Bên B có quyền chấm dứt thử việc mà không cần báo trước.\n"
       "3. Bên A không được trả lương thử việc thấp hơn 85% mức lương, trừ trường hợp có thỏa thuận khác.\n"
       "Điều 2. Tiền lương giả định\n"
       "Tiền lương thử việc ít nhất bằng 85% mức lương chính thức.\n")


class ProhibitionStandIn(StandIn):
    """Adds a verbatim prohibition with an exception and a number, so every planted error type applies."""

    def structured(self, system, prompt, schema, purpose="structured"):
        answer = super().structured(system, prompt, schema, purpose)
        import json
        request = json.loads(prompt)
        for item, sentence in zip(answer["output"]["results"], request["sentences"]):
            if "không được" in sentence["text"]:
                item["norms"] = [norm("Bên A", "trả lương thử việc thấp hơn 85% mức lương", "prohibition", "không được",
                                      exceptions="trừ trường hợp có thỏa thuận khác", conditions="thử việc")]
        return answer


class RqEvaluationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.documents, self.units, self.texts = bundle(self.root / "bundle", {"syn": LAW})
        self.kb = self.root / "kb"
        kb_run.start(self.root / "bundle", self.kb, "stand-in", "medium")
        kb_run.extract(self.units, ProhibitionStandIn(), self.kb)
        kb_run.materialize(self.units, self.kb)

    def test_planted_errors_are_caught_by_type_and_semantic_ones_are_reported_as_missed(self):
        report = error_injection.run(self.kb, self.units, self.root / "inject", per_type=5)
        by_type = report["by_type"]
        self.assertEqual(report["false_rejects_on_clean"], 0)
        for name in ("quote_altered", "fabricated_actor", "number_changed", "wrong_unit", "stale_unit_version", "invalid_modality", "modality_flipped"):
            self.assertEqual(by_type[name]["detection_rate"], 1.0, name)
            self.assertEqual(by_type[name]["rejected_by_expected_check"], by_type[name]["injected"], name)
        for name in ("negation_dropped", "exception_dropped", "condition_dropped"):
            self.assertEqual(by_type[name]["detection_rate"], 0.0, name)
            self.assertFalse(by_type[name]["expected_detectable"])
        self.assertEqual(report["detection_rate_detectable_types"], 1.0)
        again = error_injection.inject(read_jsonl(self.kb / "dk4.jsonl"), self.units, per_type=5)
        self.assertEqual([c["claim_id"] for c in again], [c["claim_id"] for c in read_jsonl(self.root / "inject" / "injected.jsonl")], "seeded")

    def test_planted_kb_replaces_target_claims_and_dk4_is_the_validator_on_that_dk3(self):
        dk3 = read_jsonl(self.kb / "dk3.jsonl")
        targets = {c["unit_id"] for c in dk3 if c["modality"] == "prohibition"}
        out = self.root / "planted"
        report = error_injection.plant(self.kb, self.units, out, targets)
        self.assertEqual(report["target_claims"], report["planted"])
        self.assertGreater(report["planted"], 0)
        planted = read_jsonl(out / "dk3.jsonl")
        self.assertEqual(len(planted), len(dk3), "claims are replaced, not added")
        changed = [c for c in planted if c.get("injection")]
        self.assertEqual({c["unit_id"] for c in changed}, targets)
        self.assertEqual({c["claim_id"] for c in changed}, {r["claim_id"] for r in read_jsonl(out / "planted.jsonl")}, "the claim keeps its ID")
        dk4_ids = {c["claim_id"] for c in read_jsonl(out / "dk4.jsonl")}
        self.assertEqual(report["removed_from_dk4"], sum(c["claim_id"] not in dk4_ids for c in changed))
        self.assertEqual(report["removed_from_dk4"], report["planted"], "every planted type here is visible to the validator")
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["bundle"], json.loads((self.kb / "manifest.json").read_text(encoding="utf-8"))["bundle"])
        with self.assertRaisesRegex(ValueError, "empty"):
            error_injection.plant(self.kb, self.units, out, targets)

    def files(self, directory):
        return {path.name: path.read_bytes() for path in sorted(Path(directory).iterdir())}

    def test_inject_defaults_are_unchanged_and_v4_is_an_option(self):
        default = error_injection.run(self.kb, self.units, self.root / "inject", per_type=5)
        explicit = error_injection.run(self.kb, self.units, self.root / "inject-v3", per_type=5, validator="kb-validator-v3")
        self.assertEqual(self.files(self.root / "inject"), self.files(self.root / "inject-v3"), "the default is v3 without inheritance")
        self.assertEqual(set(default), {"injection_version", "validator_version", "seed", "per_type", "kb_run", "dk4_sha256", "clean_claims",
                                        "false_rejects_on_clean", "false_reject_rate", "injected", "caught", "detection_rate_detectable_types",
                                        "detection_precision", "by_type", "notes"}, "no new keys in the default report")
        self.assertEqual(default["validator_version"], explicit["validator_version"])
        self.assertFalse(any("accepted_via_lead_in" in row for row in default["by_type"].values()))
        self.assertFalse(any("inherited_slots" in row for row in read_jsonl(self.root / "inject" / "results.jsonl")))

        v4 = error_injection.run(self.kb, self.units, self.root / "inject-v4", per_type=5, validator="kb-validator-v4")
        self.assertEqual((self.root / "inject-v4" / "injected.jsonl").read_bytes(), (self.root / "inject" / "injected.jsonl").read_bytes(),
                         "the same corrupted claims, only the validator changes")
        self.assertEqual(v4["validator_version"], "kb-validator-v4")
        self.assertEqual(v4["accepted_via_lead_in"], [])
        self.assertEqual({t: r["rejected"] for t, r in v4["by_type"].items()}, {t: r["rejected"] for t, r in default["by_type"].items()},
                         "no lead-ins in this text: v4 judges like v3")
        self.assertEqual({r["validator_version"] for r in read_jsonl(self.root / "inject-v4" / "results.jsonl")}, {"kb-validator-v4"})
        both = error_injection.run(self.kb, self.units, self.root / "inject-v4-inherit", per_type=5, validator="kb-validator-v4", inheritance="claims-inherit-v1")
        self.assertEqual(both["inheritance_version"], "claims-inherit-v1")
        self.assertTrue(all("inherited_slots" in row for row in read_jsonl(self.root / "inject-v4-inherit" / "results.jsonl")))
        with self.assertRaisesRegex(ValueError, "kb-validator-v4"):
            error_injection.run(self.kb, self.units, self.root / "x1", per_type=5, inheritance="claims-inherit-v1")
        with self.assertRaisesRegex(ValueError, "validator must be"):
            error_injection.run(self.kb, self.units, self.root / "x2", per_type=5, validator="kb-validator-v9")

    def test_plant_defaults_are_unchanged_and_v4_with_inheritance_is_an_option(self):
        targets = {c["unit_id"] for c in read_jsonl(self.kb / "dk3.jsonl") if c["modality"] == "prohibition"}
        default = error_injection.plant(self.kb, self.units, self.root / "planted", targets)
        error_injection.plant(self.kb, self.units, self.root / "planted-v3", targets, validator="kb-validator-v3")
        self.assertEqual(self.files(self.root / "planted"), self.files(self.root / "planted-v3"))
        self.assertEqual(set(default), {"plant_version", "seed", "source_run", "validator_version", "target_units", "target_claims", "planted",
                                        "removed_from_dk4", "by_type", "dk3_claims", "dk4_claims"}, "no new keys in the default manifest")
        self.assertFalse(any("via_lead_in" in row for row in read_jsonl(self.root / "planted" / "planted.jsonl")))
        out = self.root / "planted-v4"
        report = error_injection.plant(self.kb, self.units, out, targets, validator="kb-validator-v4", inheritance="claims-inherit-v1")
        self.assertEqual((report["validator_version"], report["inheritance_version"]), ("kb-validator-v4", "claims-inherit-v1"))
        self.assertEqual(report["inheritance"]["claims"], report["dk3_claims"])
        self.assertEqual(report["removed_from_dk4"], default["removed_from_dk4"])
        self.assertEqual({c["validation"] for c in read_jsonl(out / "dk4.jsonl")}, {"kb-validator-v4"})
        self.assertTrue(all(row["via_lead_in"] == [] for row in read_jsonl(out / "planted.jsonl")))

    def test_gold_template_check_agreement_and_scores(self):
        articles = gold.sample_articles(self.units, 1)
        self.assertEqual(len(articles), 1)
        rows = gold.template(self.units, ["syn/article-1"])
        self.assertEqual(len(rows), 3)
        annotator_a = [dict(r) for r in rows]
        annotator_a[0]["norms"] = [{"modality": "obligation", "modality_cue": "phải", "slots": {"actor": "Bên A", "action": "thông báo kết quả thử việc", "recipient": "bên B"}}]
        annotator_a[1]["norms"] = [{"modality": "entitlement", "modality_cue": "có quyền", "slots": {"actor": "Bên B", "action": "chấm dứt thử việc"}}]
        annotator_a[2]["norms"] = [{"modality": "prohibition", "modality_cue": "không được",
                                    "slots": {"actor": "Bên A", "action": "trả lương thử việc thấp hơn 85% mức lương", "exceptions": "trừ trường hợp có thỏa thuận khác"}}]
        self.assertEqual(gold.check(annotator_a, self.units), [])
        broken = [dict(r) for r in annotator_a]
        broken[0] = broken[0] | {"norms": [{"modality": "obligation", "slots": {"action": "thông báo ngay"}}]}
        self.assertEqual(gold.check(broken, self.units), ["row 1 norm 1: action is not an exact quote"])

        annotator_b = [dict(r) for r in annotator_a]
        annotator_b[1] = annotator_b[1] | {"norms": [{"modality": "permission", "slots": {"actor": "Bên B", "action": "chấm dứt thử việc mà không cần báo trước"}}]}
        agreement = gold.agreement(annotator_a, annotator_b)
        self.assertEqual((agreement["kappa_has_norm"], agreement["matched_norm_pairs"]), (1.0, 3))
        self.assertLess(agreement["f1_strict"]["norms"], 1.0)

        dk4 = gold.score(annotator_a, gold.claim_predictions(read_jsonl(self.kb / "dk4.jsonl"), annotator_a))
        self.assertEqual(dk4["strict"]["norms"]["tp"], 3)
        self.assertEqual(dk4["strict"]["norms"]["recall"], 1.0)
        dk3 = gold.score(annotator_a, gold.claim_predictions(read_jsonl(self.kb / "dk3.jsonl"), annotator_a))
        self.assertLess(dk3["strict"]["norms"]["precision"], dk4["strict"]["norms"]["precision"], "unvalidated claims cost precision")
        rules = gold.score(annotator_a, gold.rule_predictions(self.units, annotator_a))
        self.assertEqual(rules["sentences"], 3)
        self.assertIn("qualifiers", rules["lenient"])


class LeadInInjectionTests(LeadInFixture):
    """kb-validator-v4 accepts a modal cue quoted from the lead-in, so a 'fabricated' cue that the lead-in holds passes."""

    def kb(self, claims):
        kb = self.root / "kb"
        write_json(kb / "manifest.json", {"bundle": self.bundle.as_posix(), "run_id": "kb-test"})
        write_jsonl(kb / "dk3.jsonl", claims)
        write_jsonl(kb / "dk4.jsonl", claims)
        return kb

    def test_v4_counts_a_corrupted_cue_found_in_the_lead_in_and_inheritance_runs_after_injection(self):
        # "5. Bên A phải lập báo cáo như sau:" over "a) Gửi bên C."; the claim has no cue, so `phải` is planted.
        kb = self.kb([self.claim("clause-5/point-a", modality="obligation")])
        v3 = error_injection.run(kb, self.units, self.root / "v3", per_type=5)
        v4 = error_injection.run(kb, self.units, self.root / "v4", per_type=5, validator="kb-validator-v4")
        self.assertEqual(v3["by_type"]["modality_cue_fabricated"]["rejected"], 1)
        self.assertEqual(v4["by_type"]["modality_cue_fabricated"]["rejected"], 0)
        self.assertEqual(v4["by_type"]["modality_cue_fabricated"]["accepted_via_lead_in"], 1)
        [entry] = v4["accepted_via_lead_in"]
        self.assertEqual((entry["type"], entry["fields"], entry["values"]), ("modality_cue_fabricated", ["modality_cue"], {"modality_cue": "phải"}))
        self.assertEqual(entry["lead_in_unit_id"], self.unit("article-1/clause-5")["unit_id"])
        self.assertEqual(v4["by_type"]["fabricated_actor"]["accepted_via_lead_in"], 0)

        error_injection.run(kb, self.units, self.root / "v4i", per_type=5, validator="kb-validator-v4", inheritance="claims-inherit-v1")
        rows = {r["claim_id"]: r for r in read_jsonl(self.root / "v4i" / "results.jsonl")}
        injected = {c["injection"]["type"]: c for c in read_jsonl(self.root / "v4i" / "injected.jsonl")}
        self.assertEqual(rows[injected["fabricated_actor"]["claim_id"]]["inherited_slots"], [], "a planted actor is never overwritten")
        self.assertEqual(rows[injected["fabricated_actor"]["claim_id"]]["decision"], "rejected")
        self.assertIn("actor", rows[injected["modality_cue_fabricated"]["claim_id"]]["inherited_slots"])
        self.assertNotIn("inheritance", injected["modality_cue_fabricated"], "injected.jsonl keeps the claim before inheritance")

    def test_a_source_with_inherited_slots_is_refused(self):
        claims, _ = inherit([self.claim("clause-5/point-a", modality="obligation")], self.units)
        self.assertIn("inheritance", claims[0])
        kb = self.kb(claims)
        with self.assertRaisesRegex(ValueError, "already carry inherited slots"):
            error_injection.run(kb, self.units, self.root / "out", validator="kb-validator-v4", inheritance="claims-inherit-v1")
        with self.assertRaisesRegex(ValueError, "already carry inherited slots"):
            error_injection.plant(kb, self.units, self.root / "out2", {claims[0]["unit_id"]}, validator="kb-validator-v4", inheritance="claims-inherit-v1")
        report = error_injection.run(kb, self.units, self.root / "plain", per_type=5, validator="kb-validator-v4")
        self.assertEqual(report["false_rejects_on_clean"], 0, "without --inherit the inherited claims are validated as they are")


if __name__ == "__main__":
    unittest.main()
