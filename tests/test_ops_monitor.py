"""Model-call log, dev controls (switch and daily limit) and usage counters. Stand-in providers, no network."""

from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.ops.monitor import MeteredProvider, OpsStore, actor, tokens
from legal_ai.providers.pilot import ProviderError


class ClaudeCodeProvider:  # Named like the real class so the log says claude-code.
    model, max_calls = "claude-stand-in", 10

    def __init__(self, fail=None):
        self.calls, self.fail = 0, fail

    def structured(self, system, prompt, schema, purpose="structured"):
        self.calls += 1
        if self.fail:
            raise ProviderError(self.fail)
        return {"output": {}, "usage": {"input_tokens": 10, "cache_read_input_tokens": 5, "output_tokens": 7}, "cost_usd": 0.02}


class RouterProvider:
    model = "ollama/stand-in"

    def __init__(self):
        self.calls = 0

    def complete(self, system, user, max_tokens=900):
        self.calls += 1
        return {"content": "{}", "usage": {"prompt_tokens": 3, "completion_tokens": 4, "completion_tokens_details": {"reasoning_tokens": 2}}}

    def generate(self, question, citations):
        return self.complete("s", question)


class OpsMonitorTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "ops.sqlite"
        self.ops = OpsStore(self.path)

    def test_calls_are_logged_with_tokens_cost_actor_and_no_content(self):
        claude = MeteredProvider(ClaudeCodeProvider(), self.ops, "proposal")
        router = MeteredProvider(RouterProvider(), self.ops, "chat")
        token = actor.set("phapche")
        self.addCleanup(actor.reset, token)
        claude.structured("system text", "SECRET PROMPT", {}, purpose="question-label")
        router.generate("SECRET QUESTION", [])
        self.assertEqual((claude.model, claude.calls, router.calls), ("claude-stand-in", 1, 1), "attributes pass through")
        with self.assertRaises(ProviderError):
            MeteredProvider(ClaudeCodeProvider(fail="timeout"), self.ops, "proposal").structured("s", "p", {})
        calls = self.ops.calls(days=1)
        by_model = {m["model"]: m for m in calls["models"]}
        self.assertEqual((by_model["claude-stand-in"]["calls"], by_model["claude-stand-in"]["errors"], by_model["claude-stand-in"]["prompt_tokens"]), (2, 1, 15))
        self.assertEqual((by_model["ollama/stand-in"]["provider"], by_model["ollama/stand-in"]["reasoning_tokens"], by_model["ollama/stand-in"]["requests"]),
                         ("9router", 2, 1), "generate is one call even though it calls complete inside")
        self.assertEqual(calls["codes"], {"timeout": 1})
        self.assertEqual({r["actor"] for r in calls["recent"]}, {"phapche"})
        self.assertEqual(self.ops.today()["cost_usd"], 0.02)
        with closing(sqlite3.connect(self.path)) as db:
            dump = "\n".join(db.iterdump())
        self.assertNotIn("SECRET", dump, "prompts and questions are never stored")

    def test_switch_and_daily_limit_block_calls_before_they_are_sent(self):
        inner = ClaudeCodeProvider()
        metered = MeteredProvider(inner, self.ops, "extraction")
        self.ops.set_control("extraction", enabled=True, daily_limit=1, by="dev")
        metered.structured("s", "p", {})
        with self.assertRaises(ProviderError) as refused:
            metered.structured("s", "p", {})
        self.assertEqual((refused.exception.code, inner.calls), ("daily_limit_reached", 1))
        self.ops.set_control("extraction", enabled=False, daily_limit=None, by="dev")
        with self.assertRaises(ProviderError) as refused:
            metered.structured("s", "p", {})
        self.assertEqual((refused.exception.code, inner.calls), ("disabled_by_dev", 1))
        today = self.ops.today()
        self.assertEqual((today["calls"], today["blocked"]), (1, 2), "blocked attempts do not count against the limit")
        self.assertEqual([c["actor"] for c in self.ops.changes()], ["dev", "dev"])
        with self.assertRaisesRegex(ValueError, "Hạn mức"):
            self.ops.set_control("extraction", enabled=True, daily_limit=-1, by="dev")
        with self.assertRaisesRegex(ValueError, "Tính năng"):
            self.ops.set_control("unknown", enabled=True, daily_limit=None, by="dev")

    def test_usage_counts_logins_and_questions_without_content(self):
        self.ops.record_event("login", result="ok", role="reader")
        self.ops.record_event("login", result="refused")
        self.ops.record_event("chat_ask", mode="extractive", semantic=False, status="sources_found", citations=3, kbs=1, ms=40)
        self.ops.record_event("chat_ask", mode="llm", semantic=True, status="insufficient_evidence", citations=0, kbs=1, ms=120)
        usage = self.ops.usage(days=2)
        today = usage["daily"][-1]
        self.assertEqual((today["login_ok"], today["login_refused"], today["questions"]), (1, 1, 2))
        self.assertEqual((usage["by_mode"], usage["semantic"], usage["no_evidence_rate"], usage["citations_mean"]),
                         ({"extractive": 1, "llm": 1}, 1, 0.5, 1.5))

    def test_tokens_read_both_usage_shapes(self):
        self.assertEqual(tokens({"input_tokens": 1, "cache_creation_input_tokens": 2, "output_tokens": 3}), (3, 3, 0))
        self.assertEqual(tokens({"prompt_tokens": 4, "completion_tokens": 5, "completion_tokens_details": {"reasoning_tokens": 1}}), (4, 5, 1))
        self.assertEqual(tokens(None), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
