"""Research corpora: immutable documents, frozen versions and exported bundles. Synthetic text, not real law."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.common.io import digest
from legal_ai.evaluation.retrieval_run import load_bundle
from legal_ai.research.corpus import CorpusStore, slug

LAW = "Điều 1. Phạm vi giả định\n1. Bên A phải báo trước 30 ngày.\n2. Bên B có quyền từ chối.\nĐiều 2. Hiệu lực\nVăn bản giả định có hiệu lực ngay.\n"
OTHER = "Điều 1. Văn bản thứ hai\nHội đồng giả định họp mỗi quý.\n"


def vbpl_snapshot(vbpl_id="139264", content="<p>Điều 1. Phạm vi giả định</p><p>1. Bên A phải báo trước 30 ngày.</p>", translation=False):
    raw = json.dumps({"success": True, "data": {"id": vbpl_id, "documentContent": {"content": content}}}, ensure_ascii=False).encode("utf-8")
    manifest = {"source_sha256": digest(raw), "site_url": f"https://vbpl.vn/van-ban/chi-tiet/{vbpl_id}", "accessed_at": "2026-11-07T00:00:00+00:00",
                "metadata": {"vbpl_id": vbpl_id, "doc_num": "45/2019/GD", "title": "Bộ luật Giả định", "effective_from": "2021-01-01", "effective_to": None,
                             "effect_status": {"code": "HHL1P", "name": "Hết hiệu lực một phần"}, "is_translation": translation}}
    return manifest, raw


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = CorpusStore(Path(self.temp.name) / "workspace.sqlite")
        self.corpus = self.store.create("Lao động", "Corpus thử", "phapche")

    def test_documents_from_files_and_vbpl_snapshots_are_parsed_and_kept(self):
        doc = self.store.add_file(self.corpus["id"], "luat-gia-dinh.txt", LAW.encode("utf-8"), "phapche")
        self.assertEqual((doc["document_id"], doc["article_count"], doc["leaf_count"]), ("luat-gia-dinh", 2, 3))
        self.assertEqual([u["unit_id"] for u in doc["units"]][:2], ["luat-gia-dinh/article-1", "luat-gia-dinh/article-1/clause-1"])
        manifest, raw = vbpl_snapshot()
        official = self.store.add_vbpl(self.corpus["id"], manifest, raw, "phapche")
        self.assertEqual((official["document_id"], official["source_kind"], official["source_ref"]), ("45-2019-gd", "vbpl", "139264"))
        self.assertEqual(official["metadata"]["effect_status"]["name"], "Hết hiệu lực một phần")
        self.assertEqual(slug("Nghị định 145/2020/NĐ-CP"), "nghi-dinh-145-2020-nd-cp")

    def test_duplicates_bad_ids_translations_and_tampered_snapshots_are_refused(self):
        cid = self.corpus["id"]
        self.store.add_file(cid, "a.txt", LAW.encode("utf-8"), "phapche")
        with self.assertRaisesRegex(ValueError, "đã có trong corpus"):
            self.store.add_file(cid, "a.txt", OTHER.encode("utf-8"), "phapche")
        with self.assertRaisesRegex(ValueError, "cùng nội dung"):
            self.store.add_file(cid, "b.txt", LAW.encode("utf-8"), "phapche")
        with self.assertRaisesRegex(ValueError, "Mã văn bản"):
            self.store.add_file(cid, "c.txt", OTHER.encode("utf-8"), "phapche", document_id="Có dấu/../x")
        with self.assertRaisesRegex(ValueError, "Không tìm thấy Điều"):
            self.store.add_file(cid, "d.txt", "Chỉ là ghi chú, không có điều khoản.".encode("utf-8"), "phapche")
        manifest, raw = vbpl_snapshot(translation=True)
        with self.assertRaisesRegex(ValueError, "bản dịch"):
            self.store.add_vbpl(cid, manifest, raw, "phapche")
        manifest, raw = vbpl_snapshot()
        with self.assertRaisesRegex(ValueError, "không khớp"):
            self.store.add_vbpl(cid, manifest, raw + b" ", "phapche")
        with self.assertRaisesRegex(ValueError, "cùng tên"):
            self.store.create("Lao động", "", "phapche")

    def test_versions_pin_documents_and_later_removal_keeps_them(self):
        cid = self.corpus["id"]
        with self.assertRaisesRegex(ValueError, "ít nhất một"):
            self.store.freeze(cid, "", "phapche")
        first = self.store.add_file(cid, "a.txt", LAW.encode("utf-8"), "phapche")
        v1 = self.store.freeze(cid, "Bản đầu", "phapche")
        self.assertEqual((v1["number"], v1["document_rows"], v1["unit_count"]), (1, [first["id"]], 4))
        with self.assertRaisesRegex(ValueError, "Không có thay đổi"):
            self.store.freeze(cid, "", "phapche")
        self.store.add_file(cid, "b.txt", OTHER.encode("utf-8"), "phapche")
        self.assertTrue(self.store.corpus(cid)["changed_since_version"])
        self.store.remove(cid, first["id"])
        v2 = self.store.freeze(cid, "", "phapche")
        self.assertEqual(v2["number"], 2)
        documents, units, texts = self.store.bundle(v1["id"])
        self.assertEqual([d["document_id"] for d in documents], ["a"], "version 1 still holds the removed document")
        self.assertEqual(texts["a"], LAW)
        self.assertEqual(self.store.document(first["id"])["removed_at"] is not None, True)

    def test_export_writes_a_bundle_that_retrieval_runs_read(self):
        cid = self.corpus["id"]
        self.store.add_file(cid, "a.txt", LAW.encode("utf-8"), "phapche")
        manifest, raw = vbpl_snapshot()
        self.store.add_vbpl(cid, manifest, raw, "phapche")
        version = self.store.freeze(cid, "", "phapche")
        out = Path(self.temp.name) / "bundle"
        self.store.export_version(version["id"], out)
        documents, units, texts = load_bundle(out)
        self.assertEqual(sorted(d["document_id"] for d in documents), ["45-2019-gd", "a"])
        self.assertEqual((out / "45-2019-gd" / "source.json").read_bytes(), raw)
        self.assertEqual(json.loads((out / "manifest.json").read_text(encoding="utf-8"))["bundle_sha256"], version["bundle_sha256"])
        with self.assertRaisesRegex(ValueError, "trống"):
            self.store.export_version(version["id"], out)


if __name__ == "__main__":
    unittest.main()
