"""Provider boundary for local tests; no model or paid service chosen implicitly."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
import json
import math

from legal_ai.common.io import canonical, digest


class ProviderError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class CachedProvider:
    """A callable transport must enforce its own network I/O timeout too.

    An overall timeout returns promptly but cannot cancel arbitrary Python code.
    Timed-out workers never write cache. One outstanding request per instance.
    Cache contains source/prompt content; use only approved public pilot data.
    """

    def __init__(self, transport, cache_dir, *, model, revision, prompt_hash, schema_version, timeout=10):
        if not all(isinstance(v, str) and v and v.lower() not in {"latest", "unknown"} for v in (model, revision, prompt_hash, schema_version)):
            raise ValueError("explicit model, revision, prompt hash and schema version required")
        if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive and finite")
        self.transport, self.cache_dir, self.timeout = transport, Path(cache_dir), timeout
        self.config = dict(model=model, revision=revision, prompt_hash=prompt_hash, schema_version=schema_version)
        self.pending = None

    def request(self, operation, payload):
        if operation not in {"generate", "embed"}:
            raise ValueError("unsupported operation")
        request = {"operation": operation, "payload": payload, "config": self.config}
        key = digest(canonical(request))
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            try:
                cached = json.loads(path.read_text(encoding="utf-8"))
                if cached["request_hash"] != key or cached["response_hash"] != digest(canonical(cached["response"])):
                    raise ValueError("cache mismatch")
                return cached["response"]
            except (KeyError, ValueError, TypeError) as exc:
                raise ProviderError("cache_corrupt") from exc
        if self.pending is not None and not self.pending.done():
            raise ProviderError("provider_busy")
        executor = ThreadPoolExecutor(max_workers=1)
        self.pending = executor.submit(self.transport, operation, payload, dict(self.config), self.timeout)
        try:
            result = self.pending.result(timeout=self.timeout)
            response_hash = digest(canonical(result))
        except TimeoutError as exc:
            raise ProviderError("timeout") from exc
        except Exception as exc:
            raise ProviderError("transport_error") from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # Exclusive creation avoids overwriting a concurrent request's artifact.
        try:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(canonical({"request_hash": key, "response_hash": response_hash, "response": result}) + "\n")
        except FileExistsError:
            pass
        return result
