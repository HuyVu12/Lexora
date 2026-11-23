"""Model-written retrieval keys (`kb-keys-gen`, `kb-keys-v2`): plan and prompts without any call, one stand-in model,
budget stop, failures on record, reuse of earlier answers, calibrated estimate, and the keys only in the index text
(DK4 without the keys of units whose claims were all rejected). Synthetic statute and stand-in model, not real law."""

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_kb_records_graph import LAW, claim
from test_retrieval_run import bundle
from legal_ai import cli
from legal_ai.common.io import canonical, digest, read_jsonl, write_json, write_jsonl
from legal_ai.evaluation import kb_run, keys_run
from legal_ai.evaluation.retrieval_run import run
from legal_ai.extraction.llm_norms import SCHEMA as EXTRACTION_SCHEMA, SYSTEM as EXTRACTION_SYSTEM
from legal_ai.indexing.kb_keys import KbKeys, check_config, load_model_keys
from legal_ai.providers.pilot import ProviderError

A1C1, A1C2 = "syn/chapter-i/article-1/clause-1", "syn/chapter-i/article-1/clause-2"
A2C1, A3C1 = "syn/chapter-i/article-2/clause-1", "syn/chapter-i/article-3/clause-1"
QUESTION = "Kẻ gây lỗi đền bù gì?"


class StandIn:
    """Answers every unit of the batch's schema enum with fixed questions; `fail` maps an Article heading to an error
    code raised once; `budget` makes calls past it raise `budget_exhausted` like ClaudeCodeProvider."""

    model = "stand-in"

    def __init__(self, fail=None, budget=None, answers=None):
        self.calls, self.ledger, self.fail, self.budget, self.answers = 0, [], dict(fail or {}), budget, answers or {}

    def structured(self, system, prompt, schema, purpose="structured"):
        if self.budget is not None and self.calls >= self.budget:
            raise ProviderError("budget_exhausted")
        self.calls += 1
        request = json.loads(prompt)
        for heading, code in list(self.fail.items()):
            if heading in request["article_heading"]:
                del self.fail[heading]
                self.ledger.append({"purpose": purpose, "status": "error", "code": code})
                raise ProviderError(code)
        unit_ids = schema["properties"]["units"]["items"]["properties"]["unit_id"]["enum"]
        output = {"units": [{"unit_id": u, "questions": self.answers.get(u, [f"Tôi hỏi về {u.rsplit('/', 2)[-2]} thì sao?",
                                                                            QUESTION if u == A3C1 else "Người ta có phải làm gì không?"])}
                            for u in unit_ids]}
        self.ledger.append({"purpose": purpose, "status": "ok"})
        return {"output": output, "usage": {"input_tokens": 3, "cache_creation_input_tokens": 100, "output_tokens": 20}, "cost_usd": 0.01,
                "model": "stand-in"}


class Fixture(unittest.TestCase):
    """Synthetic bundle, a knowledge base with four claims (kb:2 rejected by the validator) and an alias table."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.bundle = self.root / "bundle"
        self.documents, self.units, self.texts = bundle(self.bundle, {"syn": LAW})
        self.claims = [claim(self.units, A1C1, "Không quá 60 ngày", "kb:1", quantities="60 ngày"),
                       claim(self.units, A1C2, "Không quá 6 ngày", "kb:4", quantities="6 ngày"),
                       claim(self.units, A2C1, "Bên A phải thông báo kết quả thử nghiệm cho bên B", "kb:2", actor="Bên A", action="thông báo kết quả thử nghiệm"),
                       claim(self.units, A3C1, "Bên vi phạm phải bồi thường một khoản tiền tương ứng", "kb:3", actor="Bên vi phạm",
                             action="bồi thường một khoản tiền tương ứng")]
        self.kb = self.root / "kb"
        write_json(self.kb / "manifest.json", {"units_sha256": digest((self.bundle / "units.jsonl").read_bytes()), "model": "x"})
        write_jsonl(self.kb / "dk3.jsonl", self.claims)
        write_jsonl(self.kb / "dk4.jsonl", [c for c in self.claims if c["claim_id"] != "kb:2"])  # The validator rejected kb:2.
        self.aliases = self.root / "aliases.json"
        write_json(self.aliases, {"status": "draft", "actors": {"Bên A": ["bên thứ nhất"]}})

    def plan(self, **options):
        return keys_run.plan(self.bundle, self.kb, **options)

    def keys(self, output, provider=None, **options):
        head, summary, planned, system = self.plan(**options)
        keys_run.start(output, head, "stand-in", "medium")
        keys_run.write_plan(output, head, summary, planned, system)
        counts = keys_run.generate(planned, system, provider or StandIn(), output)
        return counts, keys_run.materialize(output)

    def cli(self, *argv):
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["lexora", *map(str, argv)]), contextlib.redirect_stdout(out):
            code = cli.main()
        return code, out.getvalue()


class KeysRunTests(Fixture):
    def test_batches_stay_in_one_article_and_the_schema_enum_is_the_batch(self):
        head, summary, planned, system = self.plan(batch_size=1)
        self.assertEqual(summary["units"], 4, "every leaf unit with claims")
        self.assertEqual([b["units"][0]["unit_id"] for b in planned], [A1C1, A1C2, A2C1, A3C1])
        _, _, grouped, _ = self.plan(batch_size=8)
        self.assertEqual([[u["unit_id"] for u in b["units"]] for b in grouped], [[A1C1, A1C2], [A2C1], [A3C1]], "one Article per call")
        for batch in grouped:
            ids = [u["unit_id"] for u in batch["units"]]
            item = batch["schema"]["properties"]["units"]["items"]
            self.assertEqual(item["properties"]["unit_id"]["enum"], ids)
            self.assertEqual((item["properties"]["questions"]["minItems"], item["properties"]["questions"]["maxItems"]), (2, 3))
            self.assertFalse(item["additionalProperties"])
            request = json.loads(batch["request"])
            self.assertEqual([u["unit_id"] for u in request["units"]], ids)
            self.assertEqual(request["article_heading"].split(".")[0], "Điều " + batch["article_id"].rsplit("-", 1)[1])
        first = json.loads(grouped[0]["request"])["units"][0]
        self.assertEqual(first["context"], "Thời gian thử nghiệm do hai bên thỏa thuận và bảo đảm điều kiện sau đây:", "the Article lead-in, verbatim")
        self.assertEqual(first["text"], "1. Không quá 60 ngày đối với công việc cần trình độ cao đẳng.")
        self.assertEqual(first["norms"], [{"Tính quy phạm": "nghĩa vụ", "Định lượng": "60 ngày"}])
        self.assertEqual(head["prompt"]["sha256"], digest((ROOT / "prompts" / "kb-keys-v1.md").read_text(encoding="utf-8")))
        self.assertEqual(system, (ROOT / "prompts" / "kb-keys-v1.md").read_text(encoding="utf-8"))
        with self.assertRaisesRegex(ValueError, "batch size"):
            self.plan(batch_size=0)

    def test_pilot_scope_takes_the_articles_touched_by_gold_and_top_n(self):
        questions = self.root / "q.json"
        write_json(questions, {"questions": [{"question_id": "q1", "question": "?", "split": "dev", "relevant_unit_ids": [A1C2]},
                                             {"question_id": "q2", "question": "?", "split": "held_out", "relevant_unit_ids": [A3C1]}]})
        unit_ids, record = keys_run.scope(self.units, keys_run.claims_by_unit(self.units, self.claims), self.bundle, [questions], split="dev")
        self.assertEqual(unit_ids, [A1C1, A1C2], "the whole Article of a dev gold unit, not the held-out one")
        self.assertEqual((record["mode"], record["articles"], record["sources"][0]["kind"]), ("articles_touched", 1, "question_set"))
        retrieval = self.root / "r"
        condition = self.root / "dk2.json"
        write_json(condition, {"condition": "DK2", "representation": "structural_units", "max_tokens": 384})
        shared = self.root / "shared.json"
        write_json(shared, {"top_k": 1, "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75, "recall_k": [1]}})
        write_json(questions, {"questions": [{"question_id": "q1", "question": "Bên vi phạm phải bồi thường", "split": "dev",
                                              "expected_status": "answer", "relevant_unit_ids": [A3C1]}]})
        run(self.bundle, questions, condition, shared, retrieval)
        unit_ids, record = keys_run.scope(self.units, keys_run.claims_by_unit(self.units, self.claims), self.bundle, [retrieval], top_n=1)
        self.assertEqual(unit_ids, [A3C1])
        self.assertEqual(record["sources"][0]["kind"], "retrieval_run")
        write_json(questions, {"questions": [{"question_id": "q1", "question": "?", "relevant_unit_ids": ["syn/nowhere"]}]})
        with self.assertRaisesRegex(ValueError, "outside the bundle"):
            keys_run.scope(self.units, keys_run.claims_by_unit(self.units, self.claims), self.bundle, [questions])

    def test_dry_run_writes_plan_and_prompts_and_never_builds_a_provider(self):
        output = self.root / "dry"
        with mock.patch("legal_ai.providers.claude_code.ClaudeCodeProvider.__init__", side_effect=AssertionError("no provider in a dry run")), \
                mock.patch("subprocess.run", side_effect=AssertionError("no process in a dry run")):
            code, text = self.cli("kb-keys-gen", self.kb, "--bundle", self.bundle, "--output", output, "--all", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(text)["summary"]["batches"], 3)
        self.assertEqual(sorted(p.name for p in output.iterdir()), ["plan.json", "requests.jsonl", "system.md"], "no manifest, raw answers or ledger")
        plan = json.loads((output / "plan.json").read_text(encoding="utf-8"))
        self.assertTrue(plan["dry_run"])
        self.assertEqual(plan["kb_run"]["dk3_sha256"], digest((self.kb / "dk3.jsonl").read_bytes()))
        self.assertEqual(plan["bundle"]["units_sha256"], digest((self.bundle / "units.jsonl").read_bytes()))
        requests = read_jsonl(output / "requests.jsonl")
        self.assertEqual([r["key"] for r in requests], [b["key"] for b in plan["batches"]])
        self.assertEqual((output / "system.md").read_text(encoding="utf-8"), keys_run.system_prompt())
        with mock.patch("sys.stderr", io.StringIO()), self.assertRaises(SystemExit):
            self.cli("kb-keys-gen", self.kb, "--bundle", self.bundle, "--output", self.root / "real", "--all")  # No model, budget or approval.
        self.assertFalse((self.root / "real").exists())
        with mock.patch("sys.stderr", io.StringIO()) as error, self.assertRaises(SystemExit) as stop:
            self.cli("kb-keys-gen", self.kb, "--bundle", self.bundle, "--output", output, "--all", "--dry-run")
        self.assertEqual(stop.exception.code, 2)
        self.assertIn("new, empty directory", error.getvalue(), "a dry run needs a new directory")

    def test_keys_rows_carry_claims_model_and_prompt_and_drop_bad_keys(self):
        answers = {A1C1: ["Thử việc  tối đa bao lâu?", "Theo Điều 1 thì sao?", "thử việc tối đa bao lâu?", "Câu thứ tư?", "Câu thứ năm?"],
                   A1C2: ["Điều 1 khoản 2 nói gì?", "Khoản 2 quy định gì?"]}
        provider = StandIn(answers=answers)
        counts, usage = self.keys(self.root / "k", provider, batch_size=8)
        self.assertEqual((counts["called"], counts["failed"]), (3, 0))
        rows = {r["unit_id"]: r for r in read_jsonl(self.root / "k" / "keys.jsonl")}
        self.assertEqual(rows[A1C1]["keys"], ["Thử việc tối đa bao lâu?", "Câu thứ tư?", "Câu thứ năm?"])
        self.assertEqual([d["reason"] for d in rows[A1C1]["dropped"]], ["citation", "duplicate"])
        self.assertEqual(rows[A3C1]["claim_ids"], ["kb:3"])
        self.assertEqual(rows[A3C1]["model"], "stand-in")
        self.assertEqual(rows[A3C1]["prompt_sha256"], digest(keys_run.system_prompt()))
        self.assertEqual(read_jsonl(self.root / "k" / "gaps.jsonl"),
                         [{"unit_id": A1C2, "reason": "no_valid_key", "dropped": [{"key": "Điều 1 khoản 2 nói gì?", "reason": "citation"},
                                                                                  {"key": "Khoản 2 quy định gì?", "reason": "citation"}]}])
        self.assertNotIn(A1C2, rows, "a unit whose keys all fail the checks gets none")
        self.assertEqual(usage["dropped_keys"], {"citation": 3, "duplicate": 1})
        manifest = json.loads((self.root / "k" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["usage"]["cost_usd"], 0.03)
        self.assertEqual(manifest["usage"]["input_tokens"], 309)
        self.assertEqual(manifest["usage"]["keys_sha256"], digest((self.root / "k" / "keys.jsonl").read_bytes()))
        self.assertEqual(len(read_jsonl(self.root / "k" / "ledger.jsonl")), 3, "every call logged")

    def test_failures_are_recorded_and_the_budget_stops_the_session(self):
        output = self.root / "k"
        counts, usage = self.keys(output, StandIn(fail={"Điều 2": "timeout"}), batch_size=8)
        self.assertEqual((counts["called"], counts["failed"]), (2, 1), "a failed call does not stop the others")
        raw = read_jsonl(output / "raw.jsonl")
        self.assertEqual([r["status"] for r in raw], ["ok", "error", "ok"])
        self.assertEqual(raw[1]["code"], "timeout")
        self.assertIn({"unit_id": A2C1, "reason": "call_failed:timeout"}, read_jsonl(output / "gaps.jsonl"))
        self.assertEqual(usage["call_errors"], 1)

        budget = self.root / "b"
        counts, _ = self.keys(budget, StandIn(budget=1), batch_size=8)
        self.assertEqual((counts["called"], counts["failed"]), (1, 1), "stops at the first budget error")
        self.assertEqual(len(read_jsonl(budget / "raw.jsonl")), 2)
        self.assertEqual({g["reason"] for g in read_jsonl(budget / "gaps.jsonl")}, {"not_sent:budget_exhausted", "not_called"})
        provider = StandIn()
        counts, usage = self.keys(budget, provider, batch_size=8)
        self.assertEqual((counts["already_done"], counts["called"], provider.calls), (1, 2, 2), "the resumed run pays only for the rest")
        self.assertEqual(usage["units_with_keys"], 4)
        self.assertEqual(read_jsonl(budget / "gaps.jsonl"), [])
        with self.assertRaisesRegex(ValueError, "another"):
            self.keys(budget, StandIn(), batch_size=1)

    def test_reuse_copies_earlier_answers_and_checks_the_model(self):
        questions = self.root / "q.json"
        write_json(questions, {"questions": [{"question_id": "q1", "question": "?", "relevant_unit_ids": [A3C1]}]})
        self.keys(self.root / "pilot", sources=[questions])
        head, summary, planned, system = self.plan()
        keys_run.start(self.root / "full", head, "stand-in", "medium")
        keys_run.write_plan(self.root / "full", head, summary, planned, system)
        self.assertEqual(keys_run.reuse(planned, self.root / "full", [self.root / "pilot"]), 1)
        provider = StandIn()
        counts = keys_run.generate(planned, system, provider, self.root / "full")
        self.assertEqual((counts["already_done"], provider.calls), (1, 2))
        usage = keys_run.materialize(self.root / "full")
        self.assertEqual((usage["batches_reused"], usage["cost_usd"], usage["units_with_keys"]), (1, 0.02, 4))
        keys_run.start(self.root / "other", head, "another-model", "medium")
        with self.assertRaisesRegex(ValueError, "cannot be reused"):
            keys_run.reuse(planned, self.root / "other", [self.root / "pilot"])

    def test_calibrated_estimate_recovers_the_cost_model(self):
        law = "".join(f"Điều {n}. Quy định giả định {n}\n" + "".join(f"{k}. Bên {k} phải làm việc {'rất ' * (n * k)}kỹ.\n" for k in range(1, 3))
                      for n in range(1, 13))
        folder = self.root / "big"
        _, units, _ = bundle(folder, {"syn": law})
        calibration = self.root / "cal"
        write_json(calibration / "manifest.json", {"units_sha256": digest((folder / "units.jsonl").read_bytes()), "model": "m", "effort": "medium",
                                                   "prompt": "norm-llm-v1", "system_sha256": digest(EXTRACTION_SYSTEM)})
        fixed = len(EXTRACTION_SYSTEM) + len(canonical(EXTRACTION_SCHEMA))
        rows = []
        for n, (key, _, _, request) in enumerate(kb_run.batches(units)):
            chars, out = len(request) + fixed, 50 + 7 * n
            rows.append({"key": key, "status": "ok", "output": {"results": ["x" * (2 * out)]}, "cost_usd": 0.002 + 3e-6 * chars + 1.5e-5 * out,
                         "usage": {"input_tokens": 2, "cache_creation_input_tokens": int(900 + 0.5 * chars), "cache_read_input_tokens": 0,
                                   "output_tokens": out}})
        write_jsonl(calibration / "raw.jsonl", rows + [{"key": "x", "status": "error", "code": "timeout"}])
        fit = keys_run.calibrate(calibration, folder)
        self.assertEqual(fit["calls"], 12)
        self.assertAlmostEqual(fit["cost_per_call"]["intercept_usd"], 0.002, places=6)
        self.assertAlmostEqual(fit["cost_per_call"]["per_prompt_char_usd"], 3e-6, places=9)
        self.assertAlmostEqual(fit["cost_per_call"]["per_output_token_usd"], 1.5e-5, places=9)
        self.assertAlmostEqual(fit["input_tokens_per_call"]["per_prompt_char"], 0.5, places=3)
        head, summary, planned, system = self.plan()
        estimate = keys_run.estimate(planned, system, summary["chars_per_word"], fit)
        self.assertEqual(estimate["calls"], 3)
        self.assertLess(estimate["scenarios"]["low"]["usd"], estimate["scenarios"]["high"]["usd"])
        prompt_chars = sum(len(b["request"]) + len(system) + len(canonical(b["schema"])) for b in planned)
        self.assertEqual(estimate["prompt_characters"], prompt_chars)
        with self.assertRaisesRegex(ValueError, "another corpus bundle"):
            keys_run.calibrate(calibration, self.bundle)


class ModelKeysRetrievalTests(Fixture):
    """`kb-keys-v2` in a retrieval run: the questions sit in the index text only, DK4 drops the questions of units
    whose claims were all rejected, and kb-keys-v1 runs stay as before."""

    def setUp(self):
        super().setUp()
        self.keys(self.root / "keys", batch_size=8)
        self.questions = self.root / "q.json"
        write_json(self.questions, {"questions": [{"question_id": "q1", "question": QUESTION, "split": "dev", "expected_status": "answer",
                                                   "relevant_unit_ids": [A3C1]}]})
        self.shared = self.root / "shared.json"
        write_json(self.shared, {"top_k": 1, "token_budgets": [400],
                                 "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75, "recall_k": [1]}})

    def condition(self, name, condition, **extra):
        path = self.root / f"{name}.json"
        write_json(path, {"condition": condition, "representation": {"DK3": "llm_kb_raw", "DK4": "llm_kb_validated"}[condition], "max_tokens": 384,
                          "record": "unit_with_claims", "kb_run": self.kb.as_posix()} | extra)
        return path

    def v2(self):
        return {"version": "kb-keys-v2", "aliases": self.aliases.as_posix(), "model_keys": (self.root / "keys").as_posix()}

    def test_model_keys_are_in_the_index_text_only(self):
        v1 = run(self.bundle, self.questions, self.condition("v1", "DK3", index_keys={"version": "kb-keys-v1", "aliases": self.aliases.as_posix()}),
                 self.shared, self.root / "r1")
        v2 = run(self.bundle, self.questions, self.condition("v2", "DK3", claims_view="thin", index_keys=self.v2()), self.shared, self.root / "r2")
        self.assertEqual(v1["mean_recall"]["1"], 0.0, "the everyday wording is not in the statute")
        self.assertEqual(v2["mean_recall"]["1"], 1.0, "the model question finds it")
        thin = run(self.bundle, self.questions, self.condition("t", "DK3", claims_view="thin"), self.shared, self.root / "rt")
        self.assertEqual(thin["mean_recall"]["1"], 0.0)
        plain = {r["unit_ids"][0]: r for r in read_jsonl(self.root / "rt" / "records.jsonl")}
        for row in read_jsonl(self.root / "r2" / "records.jsonl"):
            unit_id = row["unit_ids"][0]
            self.assertEqual(row["generator_text"], plain[unit_id]["generator_text"], "the generator reads the same text with or without keys")
            self.assertEqual(row["token_count"], plain[unit_id]["token_count"])
            self.assertEqual(row["text"], plain[unit_id]["text"])
            if unit_id == A3C1:
                self.assertIn(QUESTION, row["index_text"])
                self.assertNotIn(QUESTION, row["generator_text"])
                self.assertIn(QUESTION, row["index_keys"])
        manifest = json.loads((self.root / "r2" / "manifest.json").read_text(encoding="utf-8"))
        record = manifest["index_keys"]["model_keys"]
        self.assertEqual(manifest["index_keys"]["version"], "kb-keys-v2")
        self.assertEqual(record["keys_sha256"], digest((self.root / "keys" / "keys.jsonl").read_bytes()))
        self.assertEqual(record["manifest_sha256"], digest((self.root / "keys" / "manifest.json").read_bytes()))
        self.assertEqual((record["units_with_keys"], record["records_with_model_keys"]), (4, 4))
        old = json.loads((self.root / "r1" / "manifest.json").read_text(encoding="utf-8"))["index_keys"]
        self.assertEqual(list(old), ["version", "aliases", "aliases_sha256", "records_with_keys"], "kb-keys-v1 manifests keep their shape")

    def test_dk4_drops_the_keys_of_units_whose_claims_were_all_rejected(self):
        run(self.bundle, self.questions, self.condition("d3", "DK3", index_keys=self.v2()), self.shared, self.root / "r3")
        run(self.bundle, self.questions, self.condition("d4", "DK4", index_keys=self.v2()), self.shared, self.root / "r4")
        dk3 = {r["unit_ids"][0]: r for r in read_jsonl(self.root / "r3" / "records.jsonl")}
        dk4 = {r["unit_ids"][0]: r for r in read_jsonl(self.root / "r4" / "records.jsonl")}
        model = {r["unit_id"]: r["keys"] for r in read_jsonl(self.root / "keys" / "keys.jsonl")}
        self.assertTrue(set(model[A2C1]) <= set(dk3[A2C1]["index_keys"]))
        self.assertNotIn("index_keys", dk4[A2C1], "kb:2 was rejected: no v1 phrase and no model question in DK4")
        for key in model[A2C1]:
            self.assertNotIn(key, dk4[A2C1]["index_text"])
        self.assertEqual(dk4[A3C1]["index_keys"], dk3[A3C1]["index_keys"])
        builder = KbKeys(self.aliases, {A3C1: {"claim_ids": {"kb:3", "kb:9"}, "keys": ["Hỏi?"]}})
        self.assertEqual(builder.unit_model_keys(A3C1, ["kb:9"]), ["Hỏi?"], "one surviving claim keeps the unit's questions")
        self.assertEqual(builder.unit_model_keys(A3C1, ["kb:7"]), [])

    def test_keys_run_must_match_bundle_and_claims_and_v1_is_unchanged(self):
        for good in ({"version": "kb-keys-v1", "aliases": "a"}, {"version": "kb-keys-v2", "aliases": "a", "model_keys": "k"}):
            self.assertEqual(check_config(good), good)
        for bad in ({"version": "kb-keys-v1", "aliases": "a", "model_keys": "k"}, {"version": "kb-keys-v2", "aliases": "a"},
                    {"version": "kb-keys-v2", "aliases": "a", "model_keys": 3}):
            with self.assertRaisesRegex(ValueError, "index_keys"):
                check_config(bad)
        with self.assertRaisesRegex(ValueError, "other DK3 claims"):
            load_model_keys(self.root / "keys", digest((self.bundle / "units.jsonl").read_bytes()), "0" * 64)
        with self.assertRaisesRegex(ValueError, "another corpus bundle"):
            load_model_keys(self.root / "keys", "0" * 64, digest((self.kb / "dk3.jsonl").read_bytes()))
        v1 = {"version": "kb-keys-v1", "aliases": self.aliases.as_posix()}
        run(self.bundle, self.questions, self.condition("a", "DK3", index_keys=v1), self.shared, self.root / "ra")
        builder = KbKeys(self.aliases)
        from legal_ai.indexing.records import kb_unit_records
        self.assertEqual(read_jsonl(self.root / "ra" / "records.jsonl"),
                         kb_unit_records("DK3", self.documents, self.units, self.texts, self.claims, index_keys=builder))
        self.assertFalse(any(q in json.dumps(read_jsonl(self.root / "ra" / "records.jsonl"), ensure_ascii=False) for q in [QUESTION]))


if __name__ == "__main__":
    unittest.main()
