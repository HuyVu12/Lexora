"""Derived knowledge bases: `kb-materialize --output` with kb-validator-v4 and claims-inherit-v1. Stand-in model."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_claims_inherit import Fixture, norm
from legal_ai import cli
from legal_ai.common.io import digest, read_jsonl
from legal_ai.evaluation import kb_run
from legal_ai.extraction.inherit import VERSION as INHERIT_VERSION
from legal_ai.validation.evidence import check_evidence


class StandIn:
    """Point (a) of the sanction clause: one norm with an empty actor, one with the lead-in's actor quoted."""

    model = "stand-in"

    def __init__(self):
        self.ledger = []

    def structured(self, system, prompt, schema, purpose="structured"):
        request = json.loads(prompt)
        results = []
        for sentence in request["sentences"]:
            text = sentence["text"]
            if text.startswith("Không thông báo"):
                norms = [norm(text, "prohibition"), norm(text, "prohibition", actor="bên A", object="bên B")]
            elif text.startswith("Chấm dứt"):
                norms = [norm(text, "entitlement")]
            else:
                norms = []
            results.append({"sentence": sentence["id"], "norms": norms})
        return {"output": {"results": results}, "usage": {}, "cost_usd": 0.0, "model": "stand-in"}


class MaterializeTests(Fixture):
    def setUp(self):
        super().setUp()
        self.run = self.root / "kb"
        kb_run.start(self.bundle, self.run, "stand-in", "medium")
        kb_run.extract(self.units, StandIn(), self.run)
        self.report = kb_run.materialize(self.units, self.run)

    def files(self, folder):
        return {path.name: digest(path.read_bytes()) for path in sorted(Path(folder).iterdir())}

    def test_default_rebuild_is_unchanged_and_keeps_its_report_shape(self):
        before = self.files(self.run)
        self.assertEqual(kb_run.materialize(self.units, self.run), self.report)
        self.assertEqual(self.files(self.run), before)
        self.assertEqual(self.report["validator_version"], "kb-validator-v3")
        self.assertFalse({"derivation", "inheritance", "lead_in_evidence"} & set(self.report))

    def test_derived_knowledge_base_goes_to_a_new_directory(self):
        before = self.files(self.run)
        output = self.root / "derived"
        report = kb_run.materialize(self.units, output, source=self.run, validator="kb-validator-v4", inheritance=INHERIT_VERSION)
        self.assertEqual(self.files(self.run), before)  # The source run is untouched.
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["units_sha256"], json.loads((self.run / "manifest.json").read_text(encoding="utf-8"))["units_sha256"])
        self.assertEqual(manifest["derivation"], report["derivation"])
        self.assertEqual((report["derivation"]["validator_version"], report["derivation"]["inheritance_version"]), ("kb-validator-v4", INHERIT_VERSION))
        self.assertEqual(report["derivation"]["raw_sha256"], digest((self.run / "raw.jsonl").read_bytes()))
        self.assertEqual(report["inheritance"]["claims_changed"], 3)
        self.assertEqual((self.report["dk4_claims"], report["dk4_claims"]), (2, 3))
        dk4 = read_jsonl(output / "dk4.jsonl")
        self.assertTrue(all(c["validation"] == "kb-validator-v4" for c in dk4))
        self.assertEqual({c["claim_id"] for c in read_jsonl(self.run / "dk4.jsonl")} <= {c["claim_id"] for c in dk4}, True)
        self.assertEqual(report["lead_in_evidence"], {"accepted_claims": 3, "values": {"actor": 3, "outcome": 2}})
        for claim in dk4:
            for name, row in claim["evidence"].get("lead_in", {}).get("evidence", {}).items():
                self.assertEqual(check_evidence(row, self.units), [], name)
        again = kb_run.materialize(self.units, output, source=self.run, validator="kb-validator-v4", inheritance=INHERIT_VERSION)
        self.assertEqual(again, report)  # Deterministic, and a rerun of the same derivation is allowed.

    def test_unsafe_combinations_are_refused(self):
        derived = self.root / "derived"
        with self.assertRaisesRegex(ValueError, "kb-validator-v4"):
            kb_run.materialize(self.units, derived, source=self.run, inheritance=INHERIT_VERSION)
        with self.assertRaisesRegex(ValueError, "derived"):
            kb_run.materialize(self.units, self.run, validator="kb-validator-v4")
        with self.assertRaisesRegex(ValueError, "new output directory"):
            kb_run.materialize(self.units, self.run, source=self.run, validator="kb-validator-v4")
        kb_run.materialize(self.units, derived, source=self.run, validator="kb-validator-v4")
        with self.assertRaisesRegex(ValueError, "another run or derivation"):
            kb_run.materialize(self.units, derived, source=self.run, validator="kb-validator-v4", inheritance=INHERIT_VERSION)
        with self.assertRaisesRegex(ValueError, "no raw.jsonl"):
            kb_run.materialize(self.units, derived)
        (self.root / "busy").mkdir()
        (self.root / "busy" / "note.txt").write_text("x", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "new, empty"):
            kb_run.materialize(self.units, self.root / "busy", source=self.run, validator="kb-validator-v4")

    def test_cli_writes_the_derived_knowledge_base(self):
        output = self.root / "cli-derived"
        out = io.StringIO()
        argv = ["cli", "kb-materialize", str(self.run), "--bundle", str(self.bundle), "--output", str(output),
                "--validator", "kb-validator-v4", "--inherit", INHERIT_VERSION]
        with patch.object(sys, "argv", argv), redirect_stdout(out):
            cli.main()
        self.assertEqual(json.loads(out.getvalue())["dk4_claims"], 3)
        self.assertTrue((output / "dk4.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
