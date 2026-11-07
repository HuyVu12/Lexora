"""DK3/DK4 knowledge base: extraction run, automatic validation and claim records. Synthetic text, stand-in model."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_retrieval_run import bundle
from legal_ai.common.io import read_jsonl
from legal_ai.evaluation import kb_run
from legal_ai.evaluation.retrieval_run import run as retrieval_run
from legal_ai.indexing.records import serialize_claim
from legal_ai.providers.pilot import ProviderError
from legal_ai.validation.claims import validate

LAW = ("Điều 1. Thử việc giả định\n"
       "1. Bên A phải thông báo kết quả thử việc cho bên B.\n"
       "2. Bên B có quyền chấm dứt thử việc mà không cần báo trước.\n"
       "Điều 2. Tiền lương giả định\n"
       "Tiền lương thử việc ít nhất bằng 85% mức lương chính thức.\n")


def norm(actor, action, modality="obligation", cue="phải", **slots):
    base = {name: None for name in ("actor", "action", "object", "beneficiary", "recipient", "conditions", "exceptions", "deadlines", "quantities", "outcome")}
    return base | {"actor": actor, "action": action, "modality": modality, "modality_cue": cue} | slots


class StandIn:
    """Answers by sentence text; `fail_first` makes the first call of Điều 2 fail once."""

    model = "stand-in"

    def __init__(self, fail_first=False):
        self.calls, self.ledger, self.fail_first = 0, [], fail_first

    def structured(self, system, prompt, schema, purpose="structured"):
        self.calls += 1
        request = json.loads(prompt)
        if self.fail_first and "Tiền lương" in request["article_heading"]:
            self.fail_first = False
            raise ProviderError("timeout")
        results = []
        for sentence in request["sentences"]:
            text = sentence["text"]
            if text.startswith("Bên A"):
                norms = [norm("Bên A", "thông báo kết quả thử việc", recipient="bên B"),
                         norm("Bên A", "thông báo kết quả thử việc", recipient="bên B"),  # duplicate
                         norm("Người sử dụng lao động", "thông báo kết quả thử việc")]  # actor not in the sentence
            elif text.startswith("Bên B"):
                norms = [norm("Bên B", "chấm dứt thử việc", "entitlement", "có quyền"),
                         norm("Bên B", "chấm dứt thử việc", "obligation", "có quyền")]  # cue of another modality
            else:
                norms = [norm(None, "bằng 85% mức lương chính thức", "unknown", None, quantities="ít nhất bằng 85%")]
            results.append({"sentence": sentence["id"], "norms": norms})
        output = {"results": results}
        self.ledger.append({"purpose": purpose, "status": "ok"})
        return {"output": output, "usage": {"output_tokens": 10}, "cost_usd": 0.01, "model": "stand-in"}


class KbRunTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.bundle = self.root / "bundle"
        self.documents, self.units, self.texts = bundle(self.bundle, {"syn": LAW})
        self.output = self.root / "kb"

    def run_kb(self, provider):
        kb_run.start(self.bundle, self.output, "stand-in", "medium")
        counts = kb_run.extract(self.units, provider, self.output)
        return counts, kb_run.materialize(self.units, self.output)

    def test_dk4_is_the_validated_subset_of_dk3_with_reasons(self):
        self.assertEqual(kb_run.estimate(self.units)["sentences"], 3)
        counts, report = self.run_kb(StandIn())
        self.assertEqual((counts["called"], counts["failed"]), (2, 0))
        dk3, dk4 = read_jsonl(self.output / "dk3.jsonl"), read_jsonl(self.output / "dk4.jsonl")
        self.assertEqual((report["dk3_claims"], report["dk4_claims"]), (6, 3))
        self.assertTrue({c["claim_id"] for c in dk4} <= {c["claim_id"] for c in dk3})
        self.assertEqual(report["reasons"], {"actor_not_verbatim": 1, "duplicate_of": 1, "modality_cue_mismatch": 1})
        fabricated = next(c for c in dk3 if c["slots"]["actor"] == "Người sử dụng lao động")
        self.assertEqual(fabricated["slots"]["action"], "thông báo kết quả thử việc", "DK3 keeps the model's strings as given")
        kept = next(c for c in dk4 if c["slots"]["actor"] == "Bên A")
        start, end = kept["evidence"]["slots"]["recipient"]
        self.assertEqual(self.texts["syn"][start:end], "bên B")
        self.assertEqual(self.texts["syn"][slice(*kept["evidence"]["modality_cue"])], "phải")
        self.assertIn("Chủ thể: Bên A\nHành vi: thông báo kết quả thử việc\nBên nhận: bên B", serialize_claim(kept))

    def test_failed_batches_resume_without_paying_twice_and_the_manifest_is_pinned(self):
        counts, report = self.run_kb(StandIn(fail_first=True))
        self.assertEqual((counts["called"], counts["failed"], report["sentences_without_answer"]), (1, 1, 1))
        provider = StandIn()
        counts, report = self.run_kb(provider)
        self.assertEqual((counts["already_done"], counts["called"], provider.calls), (1, 1, 1))
        self.assertEqual((report["sentences_without_answer"], report["dk3_claims"]), (0, 6))
        with self.assertRaisesRegex(ValueError, "another bundle, model or effort"):
            kb_run.start(self.bundle, self.output, "other-model", "medium")

    def test_validator_reports_schema_and_integrity_failures_as_not_applicable_downstream(self):
        unit = next(u for u in self.units if u["unit_id"] == "syn/article-2")
        base = {"claim_id": "c1", "unit_id": unit["unit_id"], "unit_version_id": unit["unit_version_id"],
                "sentence": {"start": unit["source_start"] + 28, "end": unit["source_end"] - 2}, "modality": "unknown", "modality_cue": None,
                "slots": norm(None, "bằng 85%", None, None) | {}}
        base["slots"] = {k: v for k, v in base["slots"].items() if k not in ("modality", "modality_cue")}
        results = validate([base, base | {"claim_id": "c2", "unit_id": "syn/missing"}, base | {"claim_id": "c3", "modality": "duty"},
                            base | {"claim_id": "c4", "modality": "obligation", "slots": base["slots"] | {"actor": "Tiền lương"}},
                            base | {"claim_id": "c5", "modality": "obligation", "modality_cue": "phải"}], self.units)
        self.assertEqual([r["decision"] for r in results], ["accepted", "rejected", "rejected", "accepted", "rejected"])
        self.assertEqual(results[3]["checks"]["V4_modality"], "unverified", "a modality without any cue cannot be checked, so it is not rejected")
        self.assertEqual(results[4]["reasons"], ["modality_cue_not_verbatim"], "a cue the sentence does not contain is made up")
        self.assertEqual(results[1]["checks"]["V3_evidence"], "not_applicable")
        self.assertIn("modality_not_in_enum", results[2]["reasons"])

    def test_retrieval_runs_on_dk3_and_dk4_records(self):
        self.run_kb(StandIn())
        questions = self.root / "questions.json"
        questions.write_text(json.dumps({"questions": [{"question_id": "q1", "question": "Ai phải thông báo kết quả thử việc?",
                                                        "relevant_unit_ids": ["syn/article-1/clause-1"]}]}, ensure_ascii=False), encoding="utf-8")
        shared = self.root / "shared.json"
        shared.write_text(json.dumps({"top_k": 1, "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75, "recall_k": [1]}}), encoding="utf-8")
        counts = {}
        for name, representation in (("DK3", "llm_kb_raw"), ("DK4", "llm_kb_validated")):
            condition = self.root / f"{name}.json"
            condition.write_text(json.dumps({"condition": name, "representation": representation, "kb_run": self.output.as_posix()}), encoding="utf-8")
            metrics = retrieval_run(self.bundle, questions, condition, shared, self.root / f"run-{name}")
            counts[name] = metrics["record_count"]
            self.assertEqual(metrics["mean_recall"]["1"], 1.0)
            record = read_jsonl(self.root / f"run-{name}" / "records.jsonl")[0]
            self.assertEqual(record["text"], self.texts["syn"][record["source_start"]:record["source_end"]])
            self.assertTrue(record["context_text"].startswith("Tính quy phạm:"))
        self.assertEqual(counts, {"DK3": 6, "DK4": 3})


if __name__ == "__main__":
    unittest.main()
