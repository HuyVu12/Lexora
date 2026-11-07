"""Document sources: vbpl.vn references and snapshots, the local catalog and uploaded files. Offline only;
the gateway call is replaced by a stub, and every document here is synthetic, not real law."""

from contextlib import closing
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.ingestion import vbpl_api
from legal_ai.ingestion.catalog import Catalog, build_catalog, fold
from legal_ai.ingestion.files import extract_text

try:
    import pyarrow
    import pyarrow.parquet as pq
except ImportError:  # pragma: no cover - stdlib-only environment
    pyarrow = None
try:
    import pypdf
except ImportError:  # pragma: no cover
    pypdf = None

CONTENT = "<html><body><p>Điều 1. Phạm vi giả định</p><p>1. Bên A phải báo trước 30 ngày.</p><p>Điều 2. Hiệu lực</p><p>Văn bản giả định có hiệu lực ngay.</p></body></html>"


def gateway_document(vbpl_id="139264", content=CONTENT):
    return {"success": True, "data": {"id": vbpl_id, "docNum": "1/2026/GD", "title": "Văn bản giả định", "docType": {"name": "Luật"},
                                      "issueDate": "2026-01-02T00:00:00", "effFrom": "2026-02-01T00:00:00", "effTo": None,
                                      "effStatus": {"code": "CHL", "name": "Còn hiệu lực"}, "agencyName": "Cơ quan giả định",
                                      "isTranslationDoc": False, "hasOriginalPdf": False, "documentContent": {"content": content}}}


class VbplReferenceTests(unittest.TestCase):
    def test_links_and_ids_resolve_to_the_document_id(self):
        for text in ("139264", "https://vbpl.vn/van-ban/chi-tiet/139264", "https://vbpl.vn/van-ban/chi-tiet/bo-luat-lao-ong-so-45-2019-qh14--139264?tabs=toan-van",
                     " https://www.vbpl.vn/van-ban/chi-tiet/139264#top "):
            self.assertEqual(vbpl_api.parse_reference(text), "139264", text)
        self.assertEqual(vbpl_api.parse_reference("https://vbpl.vn/van-ban/chi-tiet/x--2056a200-7691-11f1-8e36-d556180f97e7"), "2056a200-7691-11f1-8e36-d556180f97e7")

    def test_other_hosts_and_pages_are_refused(self):
        for text in ("https://thuvienphapluat.vn/van-ban/chi-tiet/139264", "https://vbpl.vn/gioi-thieu", "", "../../etc/passwd", "https://vbpl.vn.evil.example/van-ban/chi-tiet/1"):
            with self.assertRaises(ValueError, msg=text):
                vbpl_api.parse_reference(text)


class VbplSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def fetch(self, body):
        with mock.patch.object(vbpl_api, "_get", return_value=json.dumps(body, ensure_ascii=False).encode("utf-8")):
            return vbpl_api.fetch_document("https://vbpl.vn/van-ban/chi-tiet/139264", self.temp.name)

    def test_snapshot_is_immutable_and_keeps_official_metadata(self):
        manifest = self.fetch(gateway_document())
        self.assertEqual(manifest["metadata"]["effect_status"], {"code": "CHL", "name": "Còn hiệu lực"})
        self.assertEqual((manifest["metadata"]["issue_date"], manifest["metadata"]["effective_from"]), ("2026-01-02", "2026-02-01"))
        stored = Path(manifest["local_path"]).read_bytes()
        self.assertEqual(vbpl_api.digest(stored), manifest["source_sha256"])
        self.assertEqual(self.fetch(gateway_document())["accessed_at"], manifest["accessed_at"], "an identical body reuses the snapshot")
        changed = self.fetch(gateway_document(content=CONTENT.replace("30", "45")))
        self.assertNotEqual(changed["source_sha256"], manifest["source_sha256"], "a changed body becomes a new snapshot")
        text = vbpl_api.document_text(vbpl_api.unwrap(stored))["text"]
        self.assertEqual(text, "Điều 1. Phạm vi giả định\n1. Bên A phải báo trước 30 ngày.\nĐiều 2. Hiệu lực\nVăn bản giả định có hiệu lực ngay.\n")

    def test_failed_or_mismatched_answers_store_nothing(self):
        with self.assertRaisesRegex(ValueError, "không tồn tại"):
            self.fetch({"success": "false", "message": "Văn bản không tồn tại."})
        with self.assertRaisesRegex(ValueError, "văn bản khác"):
            self.fetch(gateway_document(vbpl_id="999"))
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])
        with self.assertRaisesRegex(ValueError, "không có nội dung chữ"):
            vbpl_api.document_text(gateway_document(content="")["data"])


@unittest.skipIf(pyarrow is None, "pyarrow not installed; run in .venv with the catalog extra")
class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        raw = Path(self.temp.name) / "raw"
        raw.mkdir()
        fields = ["id", "title", "so_ky_hieu", "ngay_ban_hanh", "loai_van_ban", "ngay_co_hieu_luc", "ngay_het_hieu_luc", "nguon_thu_thap", "ngay_dang_cong_bao",
                  "nganh", "linh_vuc", "co_quan_ban_hanh", "chuc_danh", "nguoi_ky", "pham_vi", "thong_tin_ap_dung", "tinh_trang_hieu_luc"]
        docs = [("1", "Bộ luật Giả định số 10/2012/GD", "10/2012/GD", "18/06/2012", "Bộ luật", "Hết hiệu lực toàn bộ"),
                ("2", "Bộ luật Giả định số 45/2019/GD", "45/2019/GD", "20/11/2019", "Bộ luật", "Hết hiệu lực một phần"),
                ("3", "Nghị định số 145/2020/GD Hướng dẫn Bộ luật Giả định", "145/2020/GD", "14/12/2020", "Nghị định", "Còn hiệu lực"),
                ("4", "Quyết định số 7/QĐ Về thuế và việc thu phí", "7/QĐ", "01/01/2020", "Quyết định", "Còn hiệu lực"),
                ("5", "Quyết định số 8/QĐ Về thử việc giả định", "8/QĐ", "01/01/2010", "Quyết định", "Hết hiệu lực toàn bộ"),
                ("vbpqta_9", "Code 45/2019/GD", "45/2019/GD", "20/11/2019", "Bản dịch văn bản", "Còn hiệu lực")]
        rows = [{name: None for name in fields} | {"id": i, "title": t, "so_ky_hieu": n, "ngay_ban_hanh": d, "loai_van_ban": k, "tinh_trang_hieu_luc": s, "pham_vi": "Trung ương"}
                for i, t, n, d, k, s in docs]
        pq.write_table(pyarrow.Table.from_pylist(rows), raw / "th1nhng0-metadata.parquet")
        pq.write_table(pyarrow.Table.from_pylist([{"doc_id": "3", "other_doc_id": "2", "relationship": "Quy định chi tiết, hướng dẫn thi hành"}]), raw / "th1nhng0-relationships.parquet")
        with closing(sqlite3.connect(raw / "uts_vlc-vn_law.sqlite")) as db, db:
            db.execute("CREATE TABLE laws (id TEXT, doc_num TEXT, title TEXT, doc_type TEXT, issue_date TEXT, eff_from TEXT, eff_to TEXT, status_name TEXT, agency TEXT)")
            db.executemany("INSERT INTO laws VALUES (?,?,?,?,?,?,?,?,?)", [("2", "45/2019/GD", "Bộ luật Giả định", "Bộ luật", "2019-11-20", None, None, "Còn hiệu lực", "Quốc hội"),
                                                                           ("u-1", "1/2026/GD", "Luật Chỉ có ở UTS", "Luật", "2026-01-01", None, None, "Chưa có hiệu lực", "Quốc hội")])
        (raw / "revisions.json").write_text('{"th1nhng0/vietnamese-legal-documents": "r1", "undertheseanlp/UTS_VLC": "r2"}', encoding="utf-8")
        self.path = Path(self.temp.name) / "catalog.sqlite"
        self.meta = build_catalog(raw, self.path)
        self.catalog = Catalog(self.path)

    def ids(self, query, **kwargs):
        return [row["vbpl_id"] for row in self.catalog.search(query, **kwargs)]

    def test_build_merges_both_datasets_and_records_provenance(self):
        self.assertEqual((self.meta["documents"], self.meta["relationships"]), (7, 1))
        self.assertEqual(self.catalog.document("2")["sources"], ["th1nhng0/vietnamese-legal-documents", "undertheseanlp/UTS_VLC"])
        self.assertEqual(self.catalog.document("u-1")["sources"], ["undertheseanlp/UTS_VLC"])
        self.assertEqual(self.catalog.document("2")["issue_date"], "2019-11-20")
        self.assertEqual(self.catalog.info()["revisions"]["undertheseanlp/UTS_VLC"], "r2")
        with self.assertRaises(ValueError):
            build_catalog(Path(self.temp.name) / "raw", self.path)

    def test_search_ignores_accents_and_ranks_number_phrase_and_force(self):
        self.assertEqual(fold("Bộ LUẬT Đất đai"), "bo luat dat dai")
        self.assertEqual(self.ids("45/2019/GD"), ["2"], "exact number first; the English translation stays hidden")
        self.assertIn("vbpqta_9", self.ids("45/2019/GD", include_translations=True))
        ranked = self.ids("bo luat gia dinh")
        self.assertEqual(ranked[0], "2")
        self.assertLess(ranked.index("3"), ranked.index("1"), "in force before fully expired")
        self.assertEqual(self.ids("thu viec"), ["5", "4"], "the words as one phrase beat scattered matches (thuế ... việc)")
        self.assertEqual(self.ids("nghi dinh 145/20"), ["3"], "the last word may be a prefix")
        self.assertEqual(self.ids("   "), [])

    def test_relationships_name_both_ends(self):
        self.assertEqual(self.catalog.relationships("2"), [{"direction": "in", "relationship": "Quy định chi tiết, hướng dẫn thi hành", "other_id": "3",
                                                          "doc_num": "145/2020/GD", "title": "Nghị định số 145/2020/GD Hướng dẫn Bộ luật Giả định"}])


def docx(paragraphs):
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    xml = f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{body}</w:body></w:document>'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", xml)
    return buffer.getvalue()


def pdf(lines):
    """A minimal one-page PDF with a Helvetica text layer (ASCII only)."""
    stream = "BT /F1 12 Tf 72 720 Td 14 TL " + " ".join(f"({line}) Tj T*" for line in lines) + " ET"
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
               f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream", "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = "%PDF-1.4\n", []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return out.encode("latin-1")


class FileTests(unittest.TestCase):
    def test_txt_html_and_docx_keep_headings_on_their_own_lines(self):
        expected = "Điều 1. Phạm vi giả định\n1. Bên A phải báo trước 30 ngày.\n"
        self.assertEqual(extract_text("a.txt", ("﻿" + expected.replace("\n", "\r\n")).encode("utf-8"))["text"], expected)
        self.assertEqual(extract_text("a.html", b"<div>\xc4\x90i\xe1\xbb\x81u 1. A</div><script>x()</script><div>1. B</div>")["text"], "Điều 1. A\n1. B\n")
        self.assertTrue(extract_text("a.htm", CONTENT.encode("utf-8"))["text"].startswith("Điều 1. Phạm vi giả định\n1. Bên A"))
        result = extract_text("a.DOCX", docx(["Điều 1. Phạm vi giả định", "", "1. Bên A phải báo trước 30 ngày."]))
        self.assertEqual((result["format"], result["text"], result["warnings"]), ("docx", expected, []))

    def test_unsupported_empty_and_non_utf8_files_are_refused(self):
        for name, data in (("a.doc", b"x"), ("a.txt", b""), ("a.txt", bytes([0xD0, 0x69, 0xEA, 0x75, 0x20, 0x31])), ("a.docx", b"not a zip")):
            with self.assertRaises(ValueError, msg=name):
                extract_text(name, data)
        self.assertEqual(extract_text("a.txt", b"Chi co van ban, khong co dieu")["warnings"], ["no_article_headings"])

    @unittest.skipIf(pypdf is None, "pypdf not installed; run in .venv with the web extra")
    def test_pdf_text_layer_is_read_and_scans_are_refused(self):
        result = extract_text("a.pdf", pdf(["Dieu 1. Pham vi gia dinh, khong phai luat that", "1. Ben A phai bao truoc 30 ngay cho ben B."]))
        self.assertEqual(result["format"], "pdf")
        self.assertIn("1. Ben A phai bao truoc 30 ngay", result["text"])
        self.assertIn("pdf_line_breaks", result["warnings"])
        with self.assertRaisesRegex(ValueError, "scan"):
            extract_text("scan.pdf", pdf([]))


if __name__ == "__main__":
    unittest.main()
