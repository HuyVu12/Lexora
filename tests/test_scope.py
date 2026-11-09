"""Experiment scope: a corpus of chosen articles from pinned local snapshots. Synthetic text, not real law."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_corpus import vbpl_snapshot
from legal_ai.research.corpus import CorpusStore
from legal_ai.research.scope import article_numbers, build_scope

CONTENT = ("<p>Chương I</p><p>CHUNG</p><p>Điều 1. Phạm vi</p><p>Văn bản giả định.</p>"
           "<p>Chương II</p><p>HỢP ĐỒNG</p><p>Điều 2. Thử việc</p><p>1. Bên A phải báo trước 3 ngày.</p>"
           "<p>Điều 3. Tiền lương</p><p>Tiền lương ít nhất bằng 85%.</p>"
           "<p>Điều 4. Sửa đổi</p><p>1. Sửa đổi khoản 1 như sau:</p><p>“1. Nội dung mới.”</p>")


class ScopeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        manifest, raw = vbpl_snapshot(content=CONTENT)
        folder = self.root / "raw" / "139264" / manifest["source_sha256"]
        folder.mkdir(parents=True)
        (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (folder / "document.json").write_bytes(raw)
        self.sha = manifest["source_sha256"]
        self.store = CorpusStore(self.root / "workspace.sqlite")

    def scope(self, articles):
        path = self.root / "scope.json"
        path.write_text(json.dumps({"scope_version": "experiment-scope-v1", "name": "Phạm vi thử", "description": "Thử",
                                    "documents": [{"document_id": "luat-gia-dinh", "vbpl_id": "139264", "snapshot_sha256": self.sha,
                                                   "articles": articles}]}, ensure_ascii=False), encoding="utf-8")
        return path

    def test_scope_keeps_only_the_chosen_articles_verbatim_with_their_headings(self):
        corpus = build_scope(self.store, self.scope(["2-3"]), "phapche", raw_dir=self.root / "raw")
        row = corpus["documents"][0]
        self.assertEqual((row["document_id"], row["article_count"]), ("luat-gia-dinh", 2))
        self.assertEqual(row["metadata"]["excerpt"], {"article_ids": ["chapter-ii/article-2", "chapter-ii/article-3"], "count": 2})
        doc = self.store.document(row["id"])
        self.assertEqual([u["unit_id"] for u in doc["units"]],
                         ["luat-gia-dinh/chapter-ii", "luat-gia-dinh/chapter-ii/article-2", "luat-gia-dinh/chapter-ii/article-2/clause-1",
                          "luat-gia-dinh/chapter-ii/article-3"])
        self.assertNotIn("Phạm vi", "".join(u["text"] for u in doc["units"]))

    def test_all_articles_skip_only_those_with_quoted_amendments(self):
        corpus = build_scope(self.store, self.scope("all"), "phapche", raw_dir=self.root / "raw")
        row = corpus["documents"][0]
        self.assertEqual(row["metadata"]["excerpt"]["article_ids"], ["chapter-i/article-1", "chapter-ii/article-2", "chapter-ii/article-3"])

    def test_unknown_duplicate_and_quoted_articles_are_refused(self):
        self.assertEqual(article_numbers(["1", "3-5", "4a"]), ["1", "3", "4", "5", "4a"])
        with self.assertRaisesRegex(ValueError, "twice"):
            article_numbers(["2", "1-3"])
        with self.assertRaisesRegex(ValueError, "article 9: 0 matches"):
            build_scope(self.store, self.scope(["9"]), "phapche", raw_dir=self.root / "raw")
        with self.assertRaisesRegex(ValueError, "quoted amendment"):
            build_scope(self.store, self.scope(["4"]), "phapche", raw_dir=self.root / "raw")
        self.assertEqual(self.store.corpora(), [], "a refused scope leaves no corpus behind")


if __name__ == "__main__":
    unittest.main()
