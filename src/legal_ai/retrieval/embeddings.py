"""Dense and hybrid ranking for the retrieval runs (`dense-v1`), the same for DK1-DK4.

`LocalEmbedder` runs one pinned sentence-transformers model from a local folder (BAAI/bge-m3 under `models/`),
on CPU, with L2-normalized vectors, so cosine similarity is a dot product and runs are reproducible from the
weights. It needs the `embeddings` extra (numpy comes with it); the rest of Lexora stays standard-library.

`hybrid` fuses the BM25 and dense rankings with Reciprocal Rank Fusion over the first `candidates` of each list:
score(d) = sum over lists containing d of 1 / (c + rank), ranks from 1, ties broken by record order.
"""

from pathlib import Path

from legal_ai.common.io import digest

DENSE_VERSION = "dense-v1"


class LocalEmbedder:
    def __init__(self, path, name, revision, max_seq_length=1024, batch_size=16):
        from sentence_transformers import SentenceTransformer  # Optional extra; imported only for dense runs.
        folder = Path(path)
        if not (folder / "config.json").exists():
            raise ValueError(f"embedding model not found in {folder}; download {name}@{revision} first")
        self.model = SentenceTransformer(str(folder), device="cpu")
        self.model.max_seq_length = max_seq_length
        self.name, self.revision, self.batch_size = name, revision, batch_size
        weights = sorted(folder.glob("*.bin")) + sorted(folder.glob("*.safetensors"))
        self.weights_sha256 = {w.name: _file_digest(w) for w in weights}

    def describe(self):
        return {"dense_version": DENSE_VERSION, "model": self.name, "revision": self.revision, "device": "cpu",
                "max_seq_length": self.model.max_seq_length, "normalized": True, "weights_sha256": self.weights_sha256}

    def encode(self, texts):
        return self.model.encode(list(texts), batch_size=self.batch_size, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)


def _file_digest(path):
    import hashlib
    sha = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            sha.update(block)
    return sha.hexdigest()


class DenseIndex:
    """Exact dot-product search over normalized record vectors."""

    def __init__(self, embedder, texts):
        import numpy
        self.embedder, self.numpy = embedder, numpy
        self.matrix = numpy.asarray(embedder.encode(texts), dtype="float32")
        self.texts_sha256 = digest("\n".join(digest(t) for t in texts))

    def rank(self, query):
        vector = self.numpy.asarray(self.embedder.encode([query]), dtype="float32")[0]
        scores = self.matrix @ vector
        order = sorted(range(len(scores)), key=lambda i: (-float(scores[i]), i))
        return [(i, float(scores[i])) for i in order]


def rrf(rankings, c=60, candidates=30):
    """Fused [(index, score)] from several [(index, score)] rankings, best first."""
    fused = {}
    for ranking in rankings:
        for rank, (index, _score) in enumerate(ranking[:candidates], 1):
            fused[index] = fused.get(index, 0.0) + 1.0 / (c + rank)
    return sorted(fused.items(), key=lambda item: (-item[1], item[0]))
