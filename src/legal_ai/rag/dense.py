"""Cached dense vectors for approved passages and hybrid (lexical + dense) ranking.

Vectors are keyed by model, dimensions and the SHA-256 of the exact embedded text, so a
passage is sent to the embedding service once. Dense similarity only reorders approved
passages; it never adds text that is not an approved, exact source quote.
"""

from array import array
import math

from legal_ai.common.io import digest

RRF_K = 60
SCOPE_CHARS = 600


def passage_text(passage):
    """What gets embedded: bounded parent context, then the approved quote itself."""
    scope = " ".join(s["quote"].strip() for s in passage["scope"])[:SCOPE_CHARS]
    return (scope + "\n" if scope else "") + passage["evidence"]["quote"]


class DenseIndex:
    def __init__(self, store, embedder):
        self.store, self.embedder = store, embedder
        with store.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS embeddings (model TEXT NOT NULL, dims INTEGER NOT NULL, text_sha TEXT NOT NULL, "
                       "vector BLOB NOT NULL, PRIMARY KEY (model, dims, text_sha))")

    @property
    def model(self):
        return self.embedder.model

    def _key(self):
        return self.embedder.model, self.embedder.dimensions or 0

    def vectors(self, texts):
        """Vectors for texts in order; only uncached texts are sent, in batches."""
        model, dims = self._key()
        keys = [digest(t) for t in texts]
        cached = {}
        with self.store.connect() as db:
            for at in range(0, len(keys), 500):
                chunk = keys[at:at + 500]
                marks = ",".join("?" * len(chunk))
                for sha, blob in db.execute(f"SELECT text_sha, vector FROM embeddings WHERE model=? AND dims=? AND text_sha IN ({marks})", (model, dims, *chunk)):
                    cached[sha] = array("f", blob).tolist()
        missing = list(dict.fromkeys(k for k in keys if k not in cached))
        if missing:
            text_of = dict(zip(keys, texts))
            fresh = self.embedder.embed([text_of[k] for k in missing])
            with self.store.connect() as db:
                db.executemany("INSERT OR REPLACE INTO embeddings VALUES (?, ?, ?, ?)",
                               [(model, dims, k, array("f", v).tobytes()) for k, v in zip(missing, fresh)])
            cached.update(zip(missing, fresh))
        return [cached[k] for k in keys]

    def similarities(self, passages, question):
        vectors = self.vectors([passage_text(p) for p in passages])
        query = self.embedder.embed([question])[0]
        return [sum(a * b for a, b in zip(query, v)) for v in vectors]


def fuse(lexical, dense, *, min_similarity):
    """Reciprocal-rank fusion of a lexical ranking and dense similarities.

    lexical: list of (score, index) already gated; dense: similarity per passage index.
    A passage enters through either list; dense-only passages must clear min_similarity.
    """
    fused = {}
    for rank, (_, index) in enumerate(sorted(lexical, key=lambda pair: -pair[0]), 1):
        fused.setdefault(index, {"score": 0.0, "lexical_rank": None, "dense_rank": None})
        fused[index]["score"] += 1 / (RRF_K + rank)
        fused[index]["lexical_rank"] = rank
    ranked = sorted((i for i, s in enumerate(dense) if math.isfinite(s)), key=lambda i: -dense[i])
    for rank, index in enumerate(ranked, 1):
        if dense[index] < min_similarity and index not in fused:
            continue
        fused.setdefault(index, {"score": 0.0, "lexical_rank": None, "dense_rank": None})
        fused[index]["score"] += 1 / (RRF_K + rank)
        fused[index]["dense_rank"] = rank
    for index, row in fused.items():
        row["similarity"] = round(dense[index], 4)
    return sorted(fused.items(), key=lambda pair: (-pair[1]["score"], pair[0]))
