"""Lead-in evidence in the knowledge-base validator (`kb-validator-v4`), with v3 unchanged. Synthetic text."""

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_claims_inherit import Fixture
from legal_ai.extraction.inherit import inherit
from legal_ai.validation import claims as v3, claims_v4 as v4
from legal_ai.validation.evidence import check_evidence


class ValidatorV4Tests(Fixture):
    def test_lead_in_values_pass_v4_with_checkable_evidence_and_fail_v3(self):
        claim = self.claim("clause-1/point-a", modality="prohibition", actor="bên A", outcome="Phạt tiền")
        [old] = v3.validate([claim], self.units)
        [new] = v4.validate([claim], self.units)
        self.assertEqual((old["decision"], sorted(old["reasons"])), ("rejected", ["actor_not_verbatim", "outcome_not_verbatim"]))
        self.assertEqual((new["decision"], new["validator_version"]), ("accepted", "kb-validator-v4"))
        lead = new["evidence"]["lead_in"]
        parent = self.unit("article-1/clause-1")
        self.assertEqual((lead["unit_id"], lead["slots"], lead["modality_cue"]), (parent["unit_id"], ["actor", "outcome"], False))
        for name in ("actor", "outcome"):
            self.assertEqual(check_evidence(lead["evidence"][name], self.units), [])
            start, end = new["evidence"]["slots"][name]
            self.assertEqual(self.texts["syn"][start:end], claim["slots"][name])
        start, end = new["evidence"]["slots"]["action"]  # Sentence values keep the v3 document offsets.
        self.assertEqual(self.texts["syn"][start:end], claim["slots"]["action"])

    def test_values_found_nowhere_still_fail(self):
        claim = self.claim("clause-1/point-a", actor="bên Z")
        [result] = v4.validate([claim], self.units)
        self.assertEqual((result["decision"], result["reasons"], result["evidence"]), ("rejected", ["actor_not_verbatim"], {}))

    def test_modal_cue_from_the_lead_in_passes_the_lexicon_checks(self):
        good = self.claim("clause-5/point-a", modality="obligation", cue="phải")
        wrong = self.claim("clause-5/point-a", 1, modality="entitlement", cue="phải", object="bên C")
        old = v3.validate([good, wrong], self.units)
        new = v4.validate([good, wrong], self.units)
        self.assertEqual([r["reasons"] for r in old], [["modality_cue_not_verbatim"], ["modality_cue_not_verbatim"]])
        self.assertEqual((new[0]["decision"], new[0]["checks"]["V4_modality"]), ("accepted", "pass"))
        self.assertTrue(new[0]["evidence"]["lead_in"]["modality_cue"])
        self.assertEqual(check_evidence(new[0]["evidence"]["lead_in"]["evidence"]["modality_cue"], self.units), [])
        self.assertEqual((new[1]["decision"], new[1]["reasons"]), ("rejected", ["modality_cue_mismatch"]))

    def test_inherited_slots_are_checked_against_their_own_evidence(self):
        [inherited], _ = inherit([self.claim("clause-1/point-a", modality="prohibition")], self.units)
        [result] = v4.validate([inherited], self.units)
        self.assertEqual(result["decision"], "accepted")
        self.assertEqual(result["evidence"]["lead_in"]["evidence"]["actor"], inherited["inheritance"]["slots"]["actor"]["evidence"])
        tampered = json.loads(json.dumps(inherited))
        tampered["inheritance"]["slots"]["actor"]["evidence"]["start"] += 1
        forged = json.loads(json.dumps(inherited))
        forged["slots"]["actor"] = "bên B"  # The value no longer matches its evidence row.
        results = v4.validate([tampered, forged], self.units)
        self.assertEqual([r["reasons"] for r in results], [["actor_inheritance_invalid"], ["actor_inheritance_invalid"]])

    def test_v3_is_unchanged(self):
        claim = self.claim("clause-2/point-a", modality="entitlement")
        [old] = v3.validate([claim], self.units)
        self.assertEqual(old["validator_version"], "kb-validator-v3")
        self.assertEqual(old["decision"], "accepted")
        self.assertNotIn("lead_in", old["evidence"])
        [new] = v4.validate([claim], self.units)
        self.assertEqual({k: v for k, v in new.items() if k != "validator_version"}, {k: v for k, v in old.items() if k != "validator_version"})


if __name__ == "__main__":
    unittest.main()
