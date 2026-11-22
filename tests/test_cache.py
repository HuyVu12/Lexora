"""The bounded cache behind the web layer's caches of immutable data."""

from pathlib import Path
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from legal_ai.common.cache import BoundedCache


class BoundedCacheTests(unittest.TestCase):
    def test_computes_once_evicts_least_recently_used_and_never_stores_failures(self):
        cache, calls = BoundedCache(2), []

        def compute(key):
            calls.append(key)
            return key.upper()

        self.assertEqual(cache.get("a", lambda: compute("a")), "A")
        self.assertEqual(cache.get("a", lambda: compute("a")), "A")
        cache.get("b", lambda: compute("b"))
        cache.get("a", lambda: compute("a"))  # "a" is now the most recently used.
        cache.get("c", lambda: compute("c"))
        self.assertEqual((len(cache), "a" in cache, "b" in cache, "c" in cache), (2, True, False, True))
        self.assertEqual(calls, ["a", "b", "c"])

        def fail():
            raise ValueError("missing")

        with self.assertRaises(ValueError):
            cache.get("d", fail)
        self.assertNotIn("d", cache)
        cache.clear()
        self.assertEqual(len(cache), 0)
        with self.assertRaises(ValueError):
            BoundedCache(0)

    def test_concurrent_readers_get_equal_values(self):
        cache, results = BoundedCache(4), []
        threads = [threading.Thread(target=lambda: results.append(cache.get("k", lambda: ["value"]))) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(results, [["value"]] * 8)
        self.assertEqual(len(cache), 1)


if __name__ == "__main__":
    unittest.main()
