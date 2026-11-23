"""Embedding device choice: OpenVINO runs the same weights as the PyTorch CPU path.

The fast tests use stand-ins and need numpy only. The equivalence test loads the real model on both paths and is
opt-in (LEXORA_TEST_OPENVINO=1, models/bge-m3 present, openvino installed) because it takes minutes on a laptop.
"""

import os
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

from legal_ai.retrieval import embeddings
from legal_ai.retrieval.embeddings import DEVICES, LocalEmbedder, OpenVinoEncoder


class DeviceChoiceTests(unittest.TestCase):
    def test_unknown_device_is_refused_before_loading_anything(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "embedding device"):
                LocalEmbedder(temp, "m", "r", device="cuda")
        self.assertEqual(DEVICES, ("cpu", "openvino-gpu", "openvino-cpu"))


@unittest.skipIf(numpy is None, "numpy (embeddings extra) not installed")
class OpenVinoEncodeTests(unittest.TestCase):
    def encoder(self):
        # Skip conversion and compilation: a stand-in tokenizer and model whose CLS vector is (length, 1, 0).
        encoder = OpenVinoEncoder.__new__(OpenVinoEncoder)
        encoder.max_seq_length, encoder.batches = 8, []

        def tokenizer(texts, **kwargs):
            encoder.batches.append(list(texts))
            width = max(len(t) for t in texts)
            ids = numpy.asarray([[len(t)] + [0] * (width - 1) for t in texts])
            return {"input_ids": ids, "attention_mask": numpy.ones_like(ids)}

        class Compiled:
            outputs = ["hidden"]

            def __call__(self, feed):
                lengths = feed["input_ids"][:, 0].astype("float32")
                hidden = numpy.zeros((len(lengths), 3, 3), dtype="float32")
                hidden[:, 0, 0], hidden[:, 0, 1] = lengths, 1.0
                return {"hidden": hidden}

        encoder.tokenizer, encoder.compiled = tokenizer, Compiled()
        return encoder

    def test_order_is_kept_vectors_normalized_and_batches_sorted_by_length(self):
        encoder = self.encoder()
        vectors = encoder.encode(["abc", "a", "abcdefg", "ab"], 2)
        self.assertEqual(encoder.batches, [["a", "ab"], ["abc", "abcdefg"]])
        expected = [numpy.asarray([n, 1.0, 0.0]) / numpy.hypot(n, 1.0) for n in (3, 1, 7, 2)]
        numpy.testing.assert_allclose(vectors, numpy.stack(expected), rtol=1e-6)

    def test_describe_records_the_device_and_converted_model(self):
        embedder = LocalEmbedder.__new__(LocalEmbedder)
        embedder.name, embedder.revision, embedder.device, embedder.max_seq_length = "m", "r", "openvino-gpu", 1024
        embedder.weights_sha256 = {"pytorch_model.bin": "w"}
        embedder.openvino = OpenVinoEncoder.__new__(OpenVinoEncoder)
        embedder.openvino.version, embedder.openvino.ov_device, embedder.openvino.xml_sha256 = "2026.4.1", "GPU", "x"
        described = embedder.describe()
        self.assertEqual(described["device"], "openvino-gpu")
        self.assertEqual(described["openvino"], {"version": "2026.4.1", "device": "GPU", "precision": "f32", "model_xml_sha256": "x"})
        self.assertEqual(described["weights_sha256"], {"pytorch_model.bin": "w"}, "the cache key inputs do not depend on the device")


MODEL = ROOT / "models" / "bge-m3"


@unittest.skipUnless(os.environ.get("LEXORA_TEST_OPENVINO") == "1" and (MODEL / "config.json").exists(), "opt-in: LEXORA_TEST_OPENVINO=1 and models/bge-m3")
class OpenVinoEquivalenceTests(unittest.TestCase):
    def test_openvino_vectors_match_pytorch_cpu(self):
        texts = ["Người lao động có quyền đơn phương chấm dứt hợp đồng lao động.", "Thời gian thử việc không quá 180 ngày.",
                 "Hợp đồng lao động phải được giao kết bằng văn bản và được làm thành 02 bản."]
        cpu = LocalEmbedder(MODEL, "BAAI/bge-m3", "r", 1024).encode(texts)
        for device in ("openvino-cpu", "openvino-gpu"):
            if device == "openvino-gpu":
                import openvino
                if "GPU" not in openvino.Core().available_devices:
                    continue
            other = LocalEmbedder(MODEL, "BAAI/bge-m3", "r", 1024, device=device).encode(texts)
            self.assertGreater(float((numpy.asarray(other) * numpy.asarray(cpu)).sum(axis=1).min()), 0.9999, device)


if __name__ == "__main__":
    unittest.main()
