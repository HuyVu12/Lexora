"""Dense and hybrid ranking for the retrieval runs (`dense-v1`), the same for DK1-DK4.

`LocalEmbedder` runs one pinned sentence-transformers model from a local folder (BAAI/bge-m3 under `models/`),
on CPU, with L2-normalized vectors, so cosine similarity is a dot product and runs are reproducible from the
weights. It needs the `embeddings` extra (numpy comes with it); the rest of Lexora stays standard-library.

`device` picks where the same weights run: "cpu" (sentence-transformers on PyTorch, the default) or "openvino-gpu" /
"openvino-cpu" (the same pytorch_model.bin converted once to an OpenVINO model next to the folder, run in FP32, CLS
pooling and L2 normalization as the model's sentence-transformers config says). The OpenVINO path needs the optional
`openvino` package (approved 23/11/2026 to use the laptop's Intel Iris Xe GPU); on a 64-text sample its vectors matched
the PyTorch CPU vectors to cosine 1.000000, so the device is recorded in the run manifest but is not part of the cache key.

With a `cache` file (SQLite under the git-ignored `models/`), vectors are stored per model, revision, weights,
sequence length and SHA-256 of the exact text, so a record shared by several runs (another question set, a
decomposition variant) is encoded once. Only missing texts are sent to the model.

`hybrid` fuses the BM25 and dense rankings with Reciprocal Rank Fusion over the first `candidates` of each list:
score(d) = sum over lists containing d of 1 / (c + rank), ranks from 1, ties broken by record order.
"""

from contextlib import closing
from pathlib import Path
import sqlite3

from legal_ai.common.io import canonical, digest

DENSE_VERSION = "dense-v1"
DEVICES = ("cpu", "openvino-gpu", "openvino-cpu")


class LocalEmbedder:
    def __init__(self, path, name, revision, max_seq_length=1024, batch_size=16, cache=None, device="cpu"):
        if device not in DEVICES:
            raise ValueError(f"embedding device must be one of {DEVICES}")
        folder = Path(path)
        if not (folder / "config.json").exists():
            raise ValueError(f"embedding model not found in {folder}; download {name}@{revision} first")
        self.name, self.revision, self.batch_size, self.device = name, revision, batch_size, device
        self.max_seq_length = max_seq_length
        weights = sorted(folder.glob("*.bin")) + sorted(folder.glob("*.safetensors"))
        self.weights_sha256 = {w.name: _file_digest(w) for w in weights}
        if device == "cpu":
            from sentence_transformers import SentenceTransformer  # Optional extra; imported only for dense runs.
            self.model = SentenceTransformer(str(folder), device="cpu")
            self.model.max_seq_length = max_seq_length
            self.openvino = None
        else:
            self.model = None
            self.openvino = OpenVinoEncoder(folder, self.weights_sha256, max_seq_length, device.split("-", 1)[1].upper())
        self.cache = Path(cache) if cache else None
        self.cache_key = digest(canonical([name, revision, self.weights_sha256, max_seq_length]))
        if self.cache:
            self.cache.parent.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(self.cache)) as db, db:
                db.execute("CREATE TABLE IF NOT EXISTS vectors (model_key TEXT NOT NULL, text_sha TEXT NOT NULL, vector BLOB NOT NULL, "
                           "PRIMARY KEY (model_key, text_sha))")

    def describe(self):
        return {"dense_version": DENSE_VERSION, "model": self.name, "revision": self.revision, "device": self.device,
                "max_seq_length": self.max_seq_length, "normalized": True, "weights_sha256": self.weights_sha256,
                **({"openvino": self.openvino.describe()} if self.openvino else {})}

    def _encode(self, texts):
        if self.openvino:
            return self.openvino.encode(list(texts), self.batch_size)
        return self.model.encode(list(texts), batch_size=self.batch_size, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)

    def encode(self, texts):
        texts = list(texts)
        if not self.cache:
            return self._encode(texts)
        import numpy
        keys = [digest(t) for t in texts]
        found = {}
        with closing(sqlite3.connect(self.cache)) as db:
            for at in range(0, len(keys), 500):
                chunk = keys[at:at + 500]
                rows = db.execute(f"SELECT text_sha, vector FROM vectors WHERE model_key=? AND text_sha IN ({','.join('?' * len(chunk))})",
                                  (self.cache_key, *chunk))
                found.update((sha, numpy.frombuffer(blob, dtype="float32")) for sha, blob in rows)
        missing = list(dict.fromkeys(k for k in keys if k not in found))
        if missing:
            text_of = dict(zip(keys, texts))
            fresh = self._encode([text_of[k] for k in missing])
            with closing(sqlite3.connect(self.cache)) as db, db:
                db.executemany("INSERT OR REPLACE INTO vectors VALUES (?, ?, ?)",
                               [(self.cache_key, k, numpy.asarray(v, dtype="float32").tobytes()) for k, v in zip(missing, fresh)])
            found.update((k, numpy.asarray(v, dtype="float32")) for k, v in zip(missing, fresh))
        return numpy.stack([found[k] for k in keys])


class OpenVinoEncoder:
    """The model's Transformer + CLS pooling + L2 normalization on OpenVINO, converted from the same weights.

    The converted model lives in `<folder>-openvino/` with `source.json` recording the weights it came from; a
    mismatch converts again, so a stale conversion is never used. Inference precision is FP32 on every device.
    """

    def __init__(self, folder, weights_sha256, max_seq_length, ov_device):
        import json
        import openvino
        from transformers import AutoTokenizer
        pooling = json.loads((folder / "1_Pooling" / "config.json").read_text(encoding="utf-8"))
        modes = {k: v for k, v in pooling.items() if k.startswith("pooling_mode_")}
        if not modes.get("pooling_mode_cls_token") or any(v for k, v in modes.items() if k != "pooling_mode_cls_token"):
            raise ValueError("the OpenVINO path implements CLS pooling only")
        self.tokenizer = AutoTokenizer.from_pretrained(str(folder))
        self.max_seq_length, self.ov_device = max_seq_length, ov_device
        target = folder.parent / f"{folder.name}-openvino"
        xml, source = target / "model.xml", target / "source.json"
        if not xml.exists() or not source.exists() or json.loads(source.read_text(encoding="utf-8")).get("weights_sha256") != weights_sha256:
            import torch
            from transformers import AutoModel
            model = AutoModel.from_pretrained(str(folder)).eval()
            example = self.tokenizer(["xin chao", "xin chao ban"], padding=True, return_tensors="pt")
            with torch.no_grad():
                converted = openvino.convert_model(model, example_input={"input_ids": example["input_ids"], "attention_mask": example["attention_mask"]})
            target.mkdir(parents=True, exist_ok=True)
            openvino.save_model(converted, str(xml), compress_to_fp16=False)
            source.write_text(json.dumps({"weights_sha256": weights_sha256, "openvino": openvino.__version__}, indent=1), encoding="utf-8")
        self.xml_sha256 = _file_digest(xml)
        self.version = openvino.__version__
        self.compiled = openvino.Core().compile_model(str(xml), ov_device, {"INFERENCE_PRECISION_HINT": "f32"})

    def describe(self):
        return {"version": self.version, "device": self.ov_device, "precision": "f32", "model_xml_sha256": self.xml_sha256}

    def encode(self, texts, batch_size):
        import numpy
        if not texts:
            return numpy.zeros((0, 0), dtype="float32")
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        out = [None] * len(texts)
        for at in range(0, len(order), batch_size):
            batch = order[at:at + batch_size]
            tokens = self.tokenizer([texts[i] for i in batch], padding=True, truncation=True, max_length=self.max_seq_length, return_tensors="np")
            hidden = self.compiled({"input_ids": tokens["input_ids"], "attention_mask": tokens["attention_mask"]})[self.compiled.outputs[0]]
            cls = numpy.asarray(hidden[:, 0], dtype="float32")
            cls /= numpy.linalg.norm(cls, axis=1, keepdims=True)
            for row, i in enumerate(batch):
                out[i] = cls[row]
        return numpy.stack(out)


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
