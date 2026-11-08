"""Operational monitoring of the web app (`ops-store-v1`): model calls, usage counters, limits and a kill switch.

Every model provider the web app builds is wrapped in a `MeteredProvider`. Before each call it checks the feature's
switch and daily limit set by a `dev` account; after it, it writes one row to `model_calls` with metadata only:
time, feature, purpose, provider, model, who triggered it, status, error code, tokens, cost and duration. Prompts,
answers, questions and source text are never stored here.

`usage_events` keeps counters of logins and chat questions (result, mode, status, number of citations, duration),
again without content. Days are the server's local calendar days.
"""

import contextvars
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
import sqlite3
import threading
import time

from legal_ai.providers import pilot
from legal_ai.providers.claude_code import ProviderError  # Raised for blocked calls; a subclass of the shared pilot error.

OPS_VERSION = "ops-store-v1"
FEATURES = ("chat", "extraction", "proposal", "embedding")
CALL_METHODS = ("structured", "complete", "generate", "embed")
actor = contextvars.ContextVar("lexora_actor", default=None)


def _now():
    return datetime.now(timezone.utc)


def _day(moment=None):
    return (moment or _now()).astimezone().date().isoformat()


def _percentile(values, share):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    index = min(len(values) - 1, max(0, round(share * (len(values) - 1))))
    return values[index]


def tokens(usage):
    """(prompt, completion, reasoning) tokens from a Claude Code or OpenAI-style usage block."""
    usage = usage if isinstance(usage, dict) else {}
    number = lambda *names: sum(usage.get(n) or 0 for n in names if isinstance(usage.get(n), (int, float)))
    details = usage.get("completion_tokens_details") or usage.get("output_tokens_details") or {}
    reasoning = details.get("reasoning_tokens") if isinstance(details, dict) else None
    return (number("prompt_tokens", "input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"),
            number("completion_tokens", "output_tokens"), reasoning if isinstance(reasoning, (int, float)) else 0)


class OpsStore:
    def __init__(self, path):
        self.path = str(path)
        self.lock = threading.Lock()
        with closing(self._connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS model_calls (
                    id INTEGER PRIMARY KEY, at TEXT NOT NULL, day TEXT NOT NULL, feature TEXT NOT NULL, purpose TEXT,
                    provider TEXT, model TEXT, actor TEXT, status TEXT NOT NULL, code TEXT, requests INTEGER NOT NULL DEFAULT 1,
                    prompt_tokens INTEGER NOT NULL DEFAULT 0, completion_tokens INTEGER NOT NULL DEFAULT 0,
                    reasoning_tokens INTEGER NOT NULL DEFAULT 0, cost_usd REAL, duration_ms INTEGER);
                CREATE INDEX IF NOT EXISTS model_calls_day ON model_calls (day, feature);
                CREATE TABLE IF NOT EXISTS usage_events (id INTEGER PRIMARY KEY, at TEXT NOT NULL, day TEXT NOT NULL,
                    event TEXT NOT NULL, detail TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS usage_events_day ON usage_events (day, event);
                CREATE TABLE IF NOT EXISTS ops_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL, updated_by TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS ops_changes (id INTEGER PRIMARY KEY, at TEXT NOT NULL, actor TEXT NOT NULL, key TEXT NOT NULL,
                    before TEXT, after TEXT NOT NULL);
            """)

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    # Settings ----------------------------------------------------------------------

    def setting(self, key, default=None):
        with closing(self._connect()) as db:
            row = db.execute("SELECT value FROM ops_settings WHERE key = ?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def put_setting(self, key, value, by):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
        with self.lock, closing(self._connect()) as db, db:
            row = db.execute("SELECT value FROM ops_settings WHERE key = ?", (key,)).fetchone()
            if row and row["value"] == text:
                return value
            at = _now().isoformat(timespec="seconds")
            db.execute("INSERT INTO ops_settings (key, value, updated_at, updated_by) VALUES (?, ?, ?, ?) "
                       "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at, updated_by = excluded.updated_by",
                       (key, text, at, by))
            db.execute("INSERT INTO ops_changes (at, actor, key, before, after) VALUES (?, ?, ?, ?, ?)", (at, by, key, row["value"] if row else None, text))
        return value

    def controls(self):
        """{feature: {"enabled": bool, "daily_limit": int | None}} with defaults for features never set."""
        saved = self.setting("controls", {})
        return {f: {"enabled": bool((saved.get(f) or {}).get("enabled", True)), "daily_limit": (saved.get(f) or {}).get("daily_limit")} for f in FEATURES}

    def set_control(self, feature, *, enabled, daily_limit, by):
        if feature not in FEATURES:
            raise ValueError("Tính năng không hợp lệ")
        if type(enabled) is not bool:
            raise ValueError("enabled phải là true hoặc false")
        if daily_limit is not None and (type(daily_limit) is not int or not 0 <= daily_limit <= 100_000):
            raise ValueError("Hạn mức mỗi ngày là số nguyên từ 0 đến 100000, hoặc để trống")
        controls = self.controls()
        controls[feature] = {"enabled": enabled, "daily_limit": daily_limit}
        self.put_setting("controls", controls, by)
        return controls

    def changes(self, limit=30):
        with closing(self._connect()) as db:
            return [dict(r) for r in db.execute("SELECT at, actor, key, before, after FROM ops_changes ORDER BY id DESC LIMIT ?", (limit,))]

    # Recording ---------------------------------------------------------------------

    def used_today(self, feature):
        with closing(self._connect()) as db:
            return db.execute("SELECT COUNT(*) FROM model_calls WHERE day = ? AND feature = ? AND status != 'blocked'", (_day(), feature)).fetchone()[0]

    def check(self, feature):
        """The refusal code when a dev switched the feature off or its daily limit is used up, else None."""
        control = self.controls()[feature]
        if not control["enabled"]:
            return "disabled_by_dev"
        if control["daily_limit"] is not None and self.used_today(feature) >= control["daily_limit"]:
            return "daily_limit_reached"
        return None

    def record_call(self, *, feature, purpose, provider, model, status, code=None, requests=1, usage=None, cost_usd=None, duration_ms=None):
        prompt, completion, reasoning = tokens(usage)
        moment = _now()
        with closing(self._connect()) as db, db:
            db.execute("""INSERT INTO model_calls (at, day, feature, purpose, provider, model, actor, status, code, requests,
                          prompt_tokens, completion_tokens, reasoning_tokens, cost_usd, duration_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (moment.isoformat(timespec="seconds"), _day(moment), feature, purpose, provider, model, actor.get(), status, code,
                        requests, prompt, completion, reasoning, cost_usd, duration_ms))

    def record_event(self, event, **detail):
        moment = _now()
        with closing(self._connect()) as db, db:
            db.execute("INSERT INTO usage_events (at, day, event, detail) VALUES (?, ?, ?, ?)",
                       (moment.isoformat(timespec="seconds"), _day(moment), event, json.dumps(detail, ensure_ascii=False, sort_keys=True)))

    # Summaries ---------------------------------------------------------------------

    def _days(self, days):
        today = _now().astimezone().date()
        return [(today - timedelta(days=n)).isoformat() for n in range(days - 1, -1, -1)]

    def calls(self, days=14, recent=50):
        span = self._days(days)
        with closing(self._connect()) as db:
            rows = [dict(r) for r in db.execute("SELECT * FROM model_calls WHERE day >= ? ORDER BY id", (span[0],))]
            last = [dict(r) for r in db.execute("SELECT at, feature, purpose, provider, model, actor, status, code, prompt_tokens, completion_tokens, "
                                                "cost_usd, duration_ms FROM model_calls ORDER BY id DESC LIMIT ?", (recent,))]
        daily = {d: {f: {"ok": 0, "error": 0, "blocked": 0} for f in FEATURES} for d in span}
        groups, codes = {}, {}
        for row in rows:
            if row["day"] in daily and row["feature"] in FEATURES:
                daily[row["day"]][row["feature"]][row["status"] if row["status"] in ("ok", "error", "blocked") else "error"] += 1
            if row["status"] != "ok":
                codes[row["code"] or "unknown"] = codes.get(row["code"] or "unknown", 0) + 1
            if row["status"] == "blocked":
                continue
            group = groups.setdefault((row["feature"], row["provider"], row["model"]), {"feature": row["feature"], "provider": row["provider"],
                                      "model": row["model"], "calls": 0, "errors": 0, "requests": 0, "prompt_tokens": 0, "completion_tokens": 0,
                                      "reasoning_tokens": 0, "cost_usd": 0.0, "durations": []})
            group["calls"] += 1
            group["errors"] += row["status"] == "error"
            group["requests"] += row["requests"]
            for name in ("prompt_tokens", "completion_tokens", "reasoning_tokens"):
                group[name] += row[name]
            group["cost_usd"] += row["cost_usd"] or 0
            group["durations"].append(row["duration_ms"])
        models = []
        for group in groups.values():
            durations = group.pop("durations")
            models.append(group | {"error_rate": group["errors"] / group["calls"], "p50_ms": _percentile(durations, 0.5),
                                   "p95_ms": _percentile(durations, 0.95), "cost_usd": round(group["cost_usd"], 4)})
        return {"days": days, "daily": [{"day": d, "features": daily[d]} for d in span],
                "models": sorted(models, key=lambda m: -m["calls"]), "codes": dict(sorted(codes.items(), key=lambda kv: -kv[1])), "recent": last}

    def today(self):
        with closing(self._connect()) as db:
            rows = [dict(r) for r in db.execute("SELECT feature, status, prompt_tokens, completion_tokens, cost_usd FROM model_calls WHERE day = ?", (_day(),))]
        made = [r for r in rows if r["status"] != "blocked"]
        return {"calls": len(made), "errors": sum(r["status"] == "error" for r in made), "blocked": len(rows) - len(made),
                "prompt_tokens": sum(r["prompt_tokens"] for r in made), "completion_tokens": sum(r["completion_tokens"] for r in made),
                "cost_usd": round(sum(r["cost_usd"] or 0 for r in made), 4),
                "by_feature": {f: sum(1 for r in made if r["feature"] == f) for f in FEATURES}}

    def usage(self, days=14):
        span = self._days(days)
        with closing(self._connect()) as db:
            rows = [(r["day"], r["event"], json.loads(r["detail"])) for r in db.execute("SELECT day, event, detail FROM usage_events WHERE day >= ?", (span[0],))]
        daily = {d: {"login_ok": 0, "login_refused": 0, "login_locked": 0, "questions": 0} for d in span}
        asks = []
        for day, event, detail in rows:
            if day not in daily:
                continue
            if event == "login":
                daily[day][f"login_{detail.get('result', 'refused')}"] = daily[day].get(f"login_{detail.get('result', 'refused')}", 0) + 1
            elif event == "chat_ask":
                daily[day]["questions"] += 1
                asks.append(detail)
        status = {}
        for ask in asks:
            status[ask.get("status")] = status.get(ask.get("status"), 0) + 1
        found = [a for a in asks if (a.get("citations") or 0) > 0]
        return {"days": days, "daily": [{"day": d} | daily[d] for d in span], "questions": len(asks),
                "by_mode": {m: sum(1 for a in asks if a.get("mode") == m) for m in ("extractive", "llm")},
                "semantic": sum(1 for a in asks if a.get("semantic")), "status": status,
                "no_evidence_rate": (len(asks) - len(found)) / len(asks) if asks else None,
                "citations_mean": sum(a.get("citations") or 0 for a in asks) / len(asks) if asks else None,
                "p50_ms": _percentile([a.get("ms") for a in asks], 0.5), "p95_ms": _percentile([a.get("ms") for a in asks], 0.95)}


class MeteredProvider:
    """Wraps one provider instance: checks the dev controls, then records every call of its model methods."""

    def __init__(self, inner, ops, feature):
        if feature not in FEATURES:
            raise ValueError(f"unknown feature {feature}")
        self._inner, self._ops, self._feature = inner, ops, feature
        name = type(inner).__name__
        self._kind = "claude-code" if name == "ClaudeCodeProvider" else ("9router" if name.startswith("Router") else "local")

    def __getattr__(self, name):
        value = getattr(self._inner, name)
        if name in CALL_METHODS and callable(value):
            return lambda *args, **kwargs: self._call(name, value, args, kwargs)
        return value

    def __setattr__(self, name, value):
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            setattr(self._inner, name, value)

    def _call(self, name, method, args, kwargs):
        purpose = kwargs.get("purpose") if name == "structured" else name
        model = getattr(self._inner, "model", None)
        blocked = self._ops.check(self._feature)
        if blocked:
            self._ops.record_call(feature=self._feature, purpose=purpose, provider=self._kind, model=model, status="blocked", code=blocked, requests=0)
            raise ProviderError(blocked, "set on the dev monitoring page")
        before = getattr(self._inner, "calls", None)
        started = time.monotonic()
        try:
            result = method(*args, **kwargs)
        except pilot.ProviderError as exc:  # Claude Code and 9Router errors alike.
            self._finish(purpose, model, before, started, status="error", code=exc.code)
            raise
        except Exception:
            self._finish(purpose, model, before, started, status="error", code="internal_error")
            raise
        usage = result.get("usage") if isinstance(result, dict) else None
        cost = result.get("cost_usd") if isinstance(result, dict) else None
        self._finish(purpose, model, before, started, status="ok", usage=usage, cost=cost)
        return result

    def _finish(self, purpose, model, before, started, *, status, code=None, usage=None, cost=None):
        after = getattr(self._inner, "calls", None)
        requests = after - before if isinstance(before, int) and isinstance(after, int) else 1
        if code == "budget_exhausted":
            requests = 0  # Lexora's own per-run budget stopped the call before it was sent.
        self._ops.record_call(feature=self._feature, purpose=purpose, provider=self._kind, model=model, status=status, code=code,
                              requests=requests, usage=usage, cost_usd=cost,
                              duration_ms=round((time.monotonic() - started) * 1000))
