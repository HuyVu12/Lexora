"""The local embedder's vector cache: only texts not seen before are encoded. Stand-in encoder, needs numpy."""

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

try:
    import numpy
except ImportError:  # The embeddings extra is optional.
    numpy = None

from legal_ai.retrieval.embeddings import LocalEmbedder


@unittest.skipIf(numpy is None, "numpy (embeddings extra) not installed")
class EmbeddingCacheTests(unittest.TestCase):
    def embedder(self, cache, key="k"):
        # Skip loading a real model: set what __init__ would set, with a counting stand-in encoder.
        embedder = LocalEmbedder.__new__(LocalEmbedder)
        embedder.cache, embedder.cache_key, embedder.seen = Path(cache), key, []
        embedder._encode = lambda texts: (embedder.seen.append(list(texts)) or numpy.asarray([[float(len(t)), 1.0] for t in texts], dtype="float32"))
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(cache)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS vectors (model_key TEXT NOT NULL, text_sha TEXT NOT NULL, vector BLOB NOT NULL, PRIMARY KEY (model_key, text_sha))")
        return embedder

    def test_only_new_texts_are_encoded_and_order_is_kept(self):
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp) / "vectors.sqlite"
            first = self.embedder(cache)
            self.assertEqual(first.encode(["ab", "abcd"]).tolist(), [[2.0, 1.0], [4.0, 1.0]])
            second = self.embedder(cache)
            vectors = second.encode(["abcd", "x", "ab", "x"])
            self.assertEqual(vectors[:, 0].tolist(), [4.0, 1.0, 2.0, 1.0])
            self.assertEqual(second.seen, [["x"]], "cached texts are not encoded again, a repeated new text once")
            other_model = self.embedder(cache, key="other")
            other_model.encode(["ab"])
            self.assertEqual(other_model.seen, [["ab"]], "vectors of another model, revision or length are never reused")


if __name__ == "__main__":
    unittest.main()
