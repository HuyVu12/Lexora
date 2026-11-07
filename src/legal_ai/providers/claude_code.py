"""Structured model calls through the local Claude Code CLI (`claude -p`), on the user's own Claude login.

Each call runs one non-interactive `claude -p` with Lexora's own system prompt (never Claude Code's), no tools,
a JSON schema for the answer, no saved session and `--safe-mode`, which leaves out the user's CLAUDE.md,
hooks, plugins, MCP servers and other customizations while keeping the login. It runs in an empty temporary
directory so no project files are visible. One exact model and effort per provider, a call budget, no retry
and no fallback model. Opus 5.5 takes no temperature or seed, so answers are not reproducible by re-running:
keep every returned answer (the `ledger`) and replay from it.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading

from legal_ai.common.io import digest
from legal_ai.providers import pilot

EFFORTS = {"low", "medium", "high", "xhigh", "max"}


class ProviderError(pilot.ProviderError):
    """The shared provider error (a `code` callers branch on) with a short `detail` for logs."""

    def __init__(self, code, detail=""):
        super().__init__(code)
        self.detail = detail


class ClaudeCodeProvider:
    def __init__(self, model="claude-opus-5-5", effort="medium", max_calls=20, timeout=600, executable=None, approved=False):
        if not approved:
            raise ProviderError("not_approved", "model calls through Claude Code need an explicit approval")
        if effort not in EFFORTS or type(max_calls) is not int or max_calls < 1:
            raise ValueError("effort must be low..max and max_calls a positive integer")
        # `executable` may be a command prefix list (tests run a stand-in script through Python).
        found = executable or shutil.which("claude")
        if not found:
            raise ProviderError("cli_missing", "the claude command is not on PATH")
        self.prefix = list(found) if isinstance(found, (list, tuple)) else [found]
        self.model, self.effort, self.max_calls, self.timeout = model, effort, max_calls, timeout
        self.calls, self.ledger = 0, []
        self._lock = threading.Lock()

    def version(self):
        result = subprocess.run(self.prefix + ["--version"], capture_output=True, text=True, encoding="utf-8", timeout=60)
        return result.stdout.strip()

    def structured(self, system, prompt, schema, purpose="structured"):
        """The model's JSON answer for `prompt` under `system`, validated by the CLI against `schema`.
        Returns {"output", "usage", "cost_usd", "model", "duration_ms"}; raises ProviderError otherwise."""
        with self._lock:
            if self.calls >= self.max_calls:
                raise ProviderError("budget_exhausted", f"{self.max_calls} calls used")
            self.calls += 1
        schema_text = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
        record = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "purpose": purpose, "model": self.model, "effort": self.effort,
                  "system_sha256": digest(system), "prompt_sha256": digest(prompt), "schema_sha256": digest(schema_text)}
        with tempfile.TemporaryDirectory(prefix="lexora-claude-") as folder:
            system_file = Path(folder) / "system.txt"
            system_file.write_text(system, encoding="utf-8")
            command = self.prefix + ["-p", "--safe-mode", "--model", self.model, "--effort", self.effort, "--system-prompt-file", str(system_file),
                       "--tools", "", "--json-schema", schema_text, "--output-format", "json", "--no-session-persistence"]
            env = {key: value for key, value in os.environ.items() if not key.startswith("CLAUDE_CODE_SSE")}
            try:
                result = subprocess.run(command, input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=self.timeout,
                                        cwd=folder, env=env)
            except subprocess.TimeoutExpired as exc:
                self._fail(record, "timeout")
                raise ProviderError("timeout", f"{self.timeout} s") from exc
        try:
            payload = json.loads(result.stdout)
        except ValueError as exc:
            self._fail(record, "invalid_output", result.stderr[-300:])
            raise ProviderError("invalid_output", (result.stderr or result.stdout)[-300:]) from exc
        if result.returncode != 0 or payload.get("is_error") or payload.get("subtype") != "success":
            self._fail(record, "model_error", str(payload.get("result"))[:300])
            raise ProviderError("model_error", str(payload.get("result") or payload.get("subtype"))[:300])
        output = payload.get("structured_output")
        if not isinstance(output, dict):
            self._fail(record, "no_structured_output")
            raise ProviderError("no_structured_output")
        answer = {"output": output, "usage": payload.get("usage", {}), "cost_usd": payload.get("total_cost_usd"),
                  "model": next(iter(payload.get("modelUsage") or {self.model: None})), "duration_ms": payload.get("duration_ms")}
        self.ledger.append(record | {"status": "ok", "output": output, "usage": answer["usage"], "cost_usd": answer["cost_usd"], "served_by": answer["model"]})
        return answer

    def _fail(self, record, code, detail=""):
        self.ledger.append(record | {"status": "error", "code": code, "detail": detail})
