"""The Claude Code provider builds an isolated `claude -p` call and keeps a ledger; a stand-in script plays the CLI."""

import json
import os
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.providers.claude_code import ClaudeCodeProvider, ProviderError

FAKE = textwrap.dedent('''
    import json, os, sys
    sys.stdin.reconfigure(encoding='utf-8'); sys.stdout.reconfigure(encoding='utf-8')
    args = sys.argv[1:]
    log = os.environ["FAKE_LOG"]
    system = open(args[args.index("--system-prompt-file") + 1], encoding="utf-8").read()
    record = {"args": args, "stdin": sys.stdin.read(), "system": system, "cwd_files": os.listdir(os.getcwd())}
    open(log, "w", encoding="utf-8").write(json.dumps(record, ensure_ascii=False))
    mode = os.environ.get("FAKE_MODE", "ok")
    if mode == "garbage":
        print("not json"); sys.exit(1)
    if mode == "error":
        print(json.dumps({"is_error": True, "subtype": "error_during_execution", "result": "overloaded"})); sys.exit(1)
    print(json.dumps({"is_error": False, "subtype": "success", "structured_output": {"days": 30} if mode == "ok" else None,
                      "usage": {"input_tokens": 3, "output_tokens": 5}, "total_cost_usd": 0.01, "modelUsage": {"claude-opus-5-5": {}}, "duration_ms": 12}))
''')


class ClaudeCodeProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.script = Path(self.temp.name) / "fake_claude.py"
        self.script.write_text(FAKE, encoding="utf-8")
        self.log = Path(self.temp.name) / "call.json"
        patch = mock.patch.dict(os.environ, {"FAKE_LOG": str(self.log)})
        patch.start()
        self.addCleanup(patch.stop)

    def provider(self, **kwargs):
        return ClaudeCodeProvider(executable=[sys.executable, str(self.script)], approved=True, **kwargs)

    def test_call_is_isolated_validated_and_recorded(self):
        provider = self.provider(effort="low")
        schema = {"type": "object", "properties": {"days": {"type": "integer"}}, "required": ["days"]}
        answer = provider.structured("Lexora system prompt", "Văn bản giả định: báo trước 30 ngày.", schema, purpose="test")
        self.assertEqual((answer["output"], answer["model"], answer["cost_usd"]), ({"days": 30}, "claude-opus-5-5", 0.01))
        call = json.loads(self.log.read_text(encoding="utf-8"))
        args = call["args"]
        for flag in ("-p", "--safe-mode", "--no-session-persistence"):
            self.assertIn(flag, args)
        self.assertEqual(args[args.index("--tools") + 1], "", "no tools")
        self.assertEqual((args[args.index("--model") + 1], args[args.index("--effort") + 1]), ("claude-opus-5-5", "low"))
        self.assertEqual(json.loads(args[args.index("--json-schema") + 1]), schema)
        self.assertEqual((call["system"], call["stdin"]), ("Lexora system prompt", "Văn bản giả định: báo trước 30 ngày."))
        self.assertEqual(call["cwd_files"], ["system.txt"], "runs in an empty folder")
        self.assertEqual(provider.ledger[0]["status"], "ok")
        self.assertEqual(provider.ledger[0]["purpose"], "test")

    def test_budget_failures_and_approval(self):
        provider = self.provider(max_calls=2)
        with mock.patch.dict(os.environ, {"FAKE_MODE": "error"}):
            with self.assertRaises(ProviderError) as error:
                provider.structured("s", "p", {"type": "object"})
            self.assertEqual(error.exception.code, "model_error")
        with mock.patch.dict(os.environ, {"FAKE_MODE": "garbage"}):
            with self.assertRaises(ProviderError) as error:
                provider.structured("s", "p", {"type": "object"})
            self.assertEqual(error.exception.code, "invalid_output")
        with self.assertRaises(ProviderError) as error:
            provider.structured("s", "p", {"type": "object"})
        self.assertEqual(error.exception.code, "budget_exhausted")
        self.assertEqual([r["status"] for r in provider.ledger], ["error", "error"])
        with self.assertRaises(ProviderError):
            ClaudeCodeProvider(executable=[sys.executable, str(self.script)])
        with self.assertRaises(ValueError):
            self.provider(effort="turbo")


if __name__ == "__main__":
    unittest.main()
