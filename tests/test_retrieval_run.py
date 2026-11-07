"""DK1/DK2 index records and the retrieval run, on a synthetic statute (not real law)."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.common.io import write_json, write_jsonl
from legal_ai.evaluation.retrieval_run import run
from legal_ai.indexing.records import check_records, fixed_chunks, structural_records, token_spans
from legal_ai.ingestion.parser import parse
from legal_ai.normalization.text import normalize
from legal_ai.retrieval.bm25 import BM25, tokens
from legal_ai.schemas.contract import VERSION

SYNTHETIC = (
    "Chương I\nQUY ĐỊNH GIẢ ĐỊNH\n"
    "Điều 1. Thời hạn báo trước\n"
    "Bên A phải báo trước cho bên B như sau:\n"
    "1. Ít nhất 45 ngày đối với hợp đồng không xác định thời hạn.\n"
    "2. Ít nhất 30 ngày đối với hợp đồng xác định thời hạn.\n"
    "Điều 2. Tiền lương giả định\n"
    "1. Tiền lương trong thời gian thử nghiệm ít nhất bằng 85% mức lương chính thức.\n"
    "2. Tiền lương được trả bằng tiền mặt hoặc chuyển khoản, trừ trường hợp hai bên có thỏa thuận khác:\n"
    "a) Trả một lần mỗi tháng vào ngày cố định. Không được trả chậm quá 15 ngày. Nếu trả chậm thì phải bồi thường.\n"
    "b) Trả theo tuần khi làm việc theo giờ.\n"
    "Điều 3. Nghỉ hằng năm\n"
    "Người làm việc đủ 12 tháng được nghỉ 12 ngày.\n"
)
SECOND = "Chương I\nVĂN BẢN THỨ HAI\nĐiều 1. Phạm vi\nVăn bản giả định này quy định về hội đồng hòa giải.\n"


def bundle(folder, sources):
    documents, units, texts = [], [], {}
    for document_id, raw in sources.items():
        normalized = normalize(raw, f"{document_id}/source.txt")
        version = normalized["normalized_sha256"]
        parsed = parse(normalized, document_id, version)
        documents.append({"schema_version": VERSION, "document_id": document_id, "document_version_id": version, "snapshot_id": "synthetic",
                          "title": f"Văn bản giả định {document_id}", "source_url": "https://example.invalid/synthetic", "accessed_at": "2026-11-07T00:00:00+00:00",
                          "source_sha256": "0" * 64, "effective_from": None, "effective_to": None, "legal_status": "unknown", "synthetic": True})
        units.extend(parsed["units"])
        texts[document_id] = normalized["text"]
        if folder:
            write_json(Path(folder) / document_id / "normalized.json", normalized)
    if folder:
        for name, rows in (("documents", documents), ("units", units), ("evidence", []), ("claims", [])):
            write_jsonl(Path(folder) / f"{name}.jsonl", rows)
    return documents, units, texts


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.documents, self.units, self.texts = bundle(None, {"syn-a": SYNTHETIC, "syn-b": SECOND})

    def test_token_spans_match_the_bm25_tokenizer(self):
        text = self.texts["syn-a"]
        self.assertEqual([text[s:e].lower() for s, e in token_spans(text)], tokens(text))

    def test_fixed_chunks_are_exact_spans_with_the_configured_overlap(self):
        records = check_records(fixed_chunks(self.documents, self.units, self.texts, chunk_tokens=20, overlap_tokens=5), self.texts)
        by_doc = {}
        for row in records:
            by_doc.setdefault(row["document_id"], []).append(row)
            self.assertEqual(row["text"], self.texts[row["document_id"]][row["source_start"]:row["source_end"]])
            self.assertLessEqual(row["token_count"], 20)
            self.assertTrue(row["index_text"].startswith("Văn bản giả định "))
        first = by_doc["syn-a"]
        for previous, current in zip(first, first[1:]):
            shared = self.texts["syn-a"][current["source_start"]:previous["source_end"]]
            self.assertEqual(len(token_spans(shared)), 5)
        unit_spans = [(u["source_start"], u["source_end"]) for u in self.units if u["document_id"] == "syn-a"]
        self.assertEqual((first[0]["source_start"], first[-1]["source_end"]), (min(unit_spans)[0], max(e for _, e in unit_spans)),
                         "the first and last chunk reach the ends of the text, keeping its final punctuation")
        for row in records:
            self.assertTrue(all(unit.startswith(row["document_id"] + "/") for unit in row["unit_ids"]), "a chunk never crosses into another document")

    def test_fixed_chunks_map_to_every_overlapping_unit_and_stop_at_gaps(self):
        units = [u for u in self.units if "/article-2" not in u["unit_id"]]
        records = fixed_chunks(self.documents, units, self.texts, chunk_tokens=1000, overlap_tokens=0)
        syn_a = [r for r in records if r["document_id"] == "syn-a"]
        self.assertEqual(len(syn_a), 2, "the removed Article 2 splits the text into two runs")
        self.assertFalse(any("/article-3" in u for u in syn_a[0]["unit_ids"]))
        self.assertIn("syn-a/chapter-i/article-3", syn_a[1]["unit_ids"])
        whole = fixed_chunks(self.documents, self.units, self.texts, chunk_tokens=1000, overlap_tokens=0)[0]
        self.assertEqual(whole["unit_ids"], [u["unit_id"] for u in sorted(self.units, key=lambda u: u["source_start"]) if u["document_id"] == "syn-a"])

    def test_structural_records_keep_leaves_whole_with_their_path_and_lead(self):
        records = check_records(structural_records(self.documents, self.units, self.texts), self.texts)
        parents = {u["parent_id"] for u in self.units}
        self.assertEqual(sorted(r["unit_ids"][0] for r in records), sorted(u["unit_id"] for u in self.units if u["unit_id"] not in parents))
        clause = next(r for r in records if r["unit_ids"] == ["syn-a/chapter-i/article-1/clause-2"])
        self.assertIn("Chương I > Điều 1 > Khoản 2", clause["index_text"])
        self.assertIn("Bên A phải báo trước cho bên B như sau:", clause["index_text"])
        self.assertEqual(clause["text"], "2. Ít nhất 30 ngày đối với hợp đồng xác định thời hạn.\n")

    def test_long_leaf_splits_at_sentence_ends_and_covers_the_leaf(self):
        point = next(u for u in self.units if u["unit_id"].endswith("article-2/clause-2/point-a"))
        records = structural_records(self.documents, self.units, self.texts, max_tokens=12)
        parts = [r for r in records if r["unit_ids"] == [point["unit_id"]]]
        self.assertGreater(len(parts), 1)
        self.assertEqual("".join(r["text"] for r in parts), point["text"])
        self.assertEqual((parts[0]["source_start"], parts[-1]["source_end"]), (point["source_start"], point["source_end"]))
        self.assertEqual([r["part"] for r in parts], [{"number": n, "of": len(parts)} for n in range(1, len(parts) + 1)])
        self.assertTrue(all(r["index_text"].count("2. Tiền lương được trả") == 1 for r in parts), "each part keeps its Clause lead")

    def test_records_reject_text_that_is_not_the_document(self):
        tampered = dict(self.texts, **{"syn-a": self.texts["syn-a"].replace("45", "46")})
        with self.assertRaises(ValueError):
            fixed_chunks(self.documents, self.units, tampered)
        records = structural_records(self.documents, self.units, self.texts)
        records[0] = dict(records[0], text=records[0]["text"] + " ")
        with self.assertRaises(ValueError):
            check_records(records, self.texts)
        with self.assertRaises(ValueError):
            fixed_chunks(self.documents, self.units, self.texts, chunk_tokens=10, overlap_tokens=10)


class BM25Tests(unittest.TestCase):
    def test_ties_break_by_document_order_and_parameters_are_checked(self):
        index = BM25([["a", "b"], ["c"], ["a", "b"]])
        self.assertEqual([i for i, _ in index.rank(["a"])], [0, 2])
        self.assertEqual(index.rank(["zzz"]), [])
        with self.assertRaises(ValueError):
            BM25([["a"]], b=1.5)


class RetrievalRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        bundle(self.root / "bundle", {"syn-a": SYNTHETIC, "syn-b": SECOND})
        self.questions = self.root / "questions.json"
        self.write_questions([
            {"question_id": "Q1", "question": "Tiền lương thử nghiệm ít nhất bao nhiêu phần trăm?", "relevant_unit_ids": ["syn-a/chapter-i/article-2/clause-1"]},
            {"question_id": "Q2", "question": "Báo trước bao nhiêu ngày?", "relevant_unit_ids": ["syn-a/chapter-i/article-1"]},
            {"question_id": "Q3", "question": "Câu hỏi ngoài phạm vi", "relevant_unit_ids": []},
        ])
        self.shared = self.root / "shared.json"
        write_json(self.shared, {"status": "draft", "top_k": 2, "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75, "recall_k": [1, 3]}})
        self.dk1, self.dk2 = self.root / "dk1.json", self.root / "dk2.json"
        write_json(self.dk1, {"condition": "DK1", "representation": "fixed_chunks", "chunk_tokens": 30, "overlap_tokens": 5, "status": "draft"})
        write_json(self.dk2, {"condition": "DK2", "representation": "structural_units", "max_tokens": 384, "status": "draft"})

    def write_questions(self, questions):
        write_json(self.questions, {"description": "synthetic", "questions": questions})

    def go(self, condition, name):
        return run(self.root / "bundle", self.questions, condition, self.shared, self.root / name)

    def test_run_writes_artifacts_and_scores_recall_on_canonical_units(self):
        metrics = self.go(self.dk2, "dk2")
        out = self.root / "dk2"
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["errors.jsonl", "manifest.json", "metrics.json", "predictions.jsonl", "records.jsonl"])
        self.assertEqual((metrics["scored_questions"], metrics["excluded_without_gold"]), (2, 1))
        self.assertEqual(sorted(metrics["mean_recall"]), ["1", "2", "3"])
        predictions = {json.loads(line)["question_id"]: json.loads(line) for line in (out / "predictions.jsonl").read_text(encoding="utf-8").splitlines()}
        self.assertEqual(predictions["Q1"]["recall"]["1"], 1.0)
        self.assertEqual(predictions["Q2"]["ranked"][0]["unit_ids"][0].rsplit("/", 1)[0], "syn-a/chapter-i/article-1", "a Clause covers its gold Article")
        self.assertEqual(predictions["Q2"]["recall"]["1"], 1.0)
        self.assertIsNone(predictions["Q3"]["recall"]["1"])
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual((manifest["status"], manifest["network"], manifest["model_calls"]), ("exploratory", False, 0))
        self.assertEqual(set(manifest["inputs"]), {"units", "documents", "questions", "condition", "shared"})

    def test_dk1_reports_context_cost_and_runs_are_deterministic(self):
        first, second = self.go(self.dk1, "a"), self.go(self.dk1, "b")
        self.assertEqual(first, second)
        read = lambda name: json.loads((self.root / name / "manifest.json").read_text(encoding="utf-8"))["records_sha256"]
        self.assertEqual(read("a"), read("b"))
        self.assertGreater(first["mean_context_tokens"]["1"], self.go(self.dk2, "c")["mean_context_tokens"]["1"])

    def test_run_refuses_reused_output_unknown_gold_and_mismatched_configs(self):
        self.go(self.dk2, "used")
        with self.assertRaises(ValueError):
            self.go(self.dk2, "used")
        self.write_questions([{"question_id": "Q1", "question": "x", "relevant_unit_ids": ["syn-a/chapter-i/article-9"]}])
        with self.assertRaises(ValueError):
            self.go(self.dk2, "missing-gold")
        write_json(self.dk1, {"condition": "DK2", "representation": "fixed_chunks", "chunk_tokens": 30, "overlap_tokens": 5})
        with self.assertRaises(ValueError):
            self.go(self.dk1, "mismatch")


if __name__ == "__main__":
    unittest.main()
