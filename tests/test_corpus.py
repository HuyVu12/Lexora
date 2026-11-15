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
        manifest, raw = vbpl_snapshot(vbpl_id="27614", content="<p>LỆNH</p><p>Nay công bố Bộ luật giả định.</p>")
        manifest["metadata"] |= {"doc_type": "Lệnh", "doc_num": "08/2012/L-GD"}
        with self.assertRaisesRegex(ValueError, r"lệnh 08/2012/L-GD\) không chia thành Điều"):
            self.store.add_vbpl(cid, manifest, raw, "phapche")
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

    def test_version_file_moves_a_frozen_version_to_another_store_by_command_line(self):
        import io
        from contextlib import redirect_stderr, redirect_stdout
        from unittest.mock import patch
        from legal_ai import cli

        def run(*argv):
            out = io.StringIO()
            with patch.object(sys, "argv", ["cli", *argv]), redirect_stdout(out):
                cli.main()
            return json.loads(out.getvalue())

        def refused(message, *argv):
            err = io.StringIO()
            with patch.object(sys, "argv", ["cli", *argv]), redirect_stdout(io.StringIO()), redirect_stderr(err), self.assertRaises(SystemExit) as stop:
                cli.main()
            self.assertEqual(stop.exception.code, 2)
            self.assertIn(message, err.getvalue())

        cid = self.corpus["id"]
        self.store.add_file(cid, "a.txt", LAW.encode("utf-8"), "phapche")
        manifest, raw = vbpl_snapshot()
        self.store.add_vbpl(cid, manifest, raw, "phapche")
        version = self.store.freeze(cid, "Bản đầu", "phapche")
        source, target = Path(self.temp.name) / "workspace.sqlite", Path(self.temp.name) / "server.sqlite"
        CorpusStore(target).create("Lao động", "Corpus đã có trên máy chủ, cùng tên", "admin")
        path = Path(self.temp.name) / "out" / "corpus-version.json"
        exported = run("corpus-version-export", "--store", str(source), "--version", version["id"], "--output", str(path))
        self.assertEqual((exported["version_id"], exported["bundle_sha256"], exported["documents"], exported["units"]),
                         (version["id"], version["bundle_sha256"], 2, version["unit_count"]))
        refused("exists", "corpus-version-export", "--store", str(source), "--version", version["id"], "--output", str(path))
        refused("không phải v000000000000", "corpus-version-import", str(path), "--store", str(target), "--actor", "admin", "--expect-version", "v000000000000")
        self.assertEqual(CorpusStore(target).corpora()[0]["latest_version"], None, "a refused import writes nothing")
        imported = run("corpus-version-import", str(path), "--store", str(target), "--actor", "admin", "--expect-version", version["id"])
        self.assertEqual((imported["version_id"], imported["bundle_sha256"], imported["documents"], imported["created"]),
                         (version["id"], version["bundle_sha256"], 2, True))
        server = CorpusStore(target)
        self.assertEqual(server.bundle(version["id"])[2]["a"], LAW)
        self.assertEqual(len(server.corpora()), 2, "a name clash keeps the existing corpus and imports under a new name")
        self.assertFalse(run("corpus-version-import", str(path), "--store", str(target), "--actor", "admin")["created"], "a second import changes nothing")
        body = json.loads(path.read_text(encoding="utf-8"))
        body["payload"]["documents"][0]["normalized"] = body["payload"]["documents"][0]["normalized"].replace("30 ngày", "45 ngày")
        with self.assertRaisesRegex(ValueError, "không khớp mã băm"):
            server.import_version_file(body, "admin")
        with self.assertRaisesRegex(ValueError, "không phải phiên bản corpus"):
            server.import_version_file({"format": "other"}, "admin")


if __name__ == "__main__":
    unittest.main()
