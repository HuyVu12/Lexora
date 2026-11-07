"""Choosing articles of a statute and cutting them out verbatim. Synthetic text, not real law."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.ingestion.excerpt import excerpt, outline
from legal_ai.normalization.text import normalize

LAW = ("Chương I\nQUY ĐỊNH CHUNG\n"
       "Điều 1. Phạm vi\nVăn bản giả định này quy định về hợp đồng.\n"
       "Chương II\nHỢP ĐỒNG\nMục 1. GIAO KẾT\n"
       "Điều 2. Thử nghiệm\n1. Bên A phải báo trước 30 ngày.\n2. Bên B có quyền từ chối.\na) Trong 3 ngày.\n"
       "Điều 3. Tiền lương\nTiền lương ít nhất bằng 85% mức chính thức.\n"
       "Chương III\nSỬA ĐỔI LUẬT KHÁC\n"
       "Điều 4. Sửa đổi luật giả định\n1. Sửa đổi khoản 1 như sau:\n1. Nội dung mới.\n1. Nội dung khác.\n")


class ExcerptTests(unittest.TestCase):
    def test_outline_lists_articles_with_their_chapter_and_blocks_nested_quotes(self):
        articles = outline(LAW)
        self.assertEqual([a["heading"] for a in articles], ["Điều 1. Phạm vi", "Điều 2. Thử nghiệm", "Điều 3. Tiền lương", "Điều 4. Sửa đổi luật giả định"])
        self.assertEqual((articles[1]["chapter"], articles[1]["section"]), ("Chương II HỢP ĐỒNG", "Mục 1. GIAO KẾT"))
        self.assertEqual([(a["blocked"], a["reason"]) for a in articles], [(False, None), (False, None), (False, None), (True, "duplicate_heading")])

    def test_excerpt_is_verbatim_with_its_headings_in_document_order(self):
        ids = {a["heading"][:7]: a["id"] for a in outline(LAW)}
        text = excerpt(LAW, [ids["Điều 3."], ids["Điều 2."]])
        self.assertEqual(text, "Chương II\nHỢP ĐỒNG\nMục 1. GIAO KẾT\nĐiều 2. Thử nghiệm\n1. Bên A phải báo trước 30 ngày.\n2. Bên B có quyền từ chối.\n"
                               "a) Trong 3 ngày.\nĐiều 3. Tiền lương\nTiền lương ít nhất bằng 85% mức chính thức.\n")
        source = normalize(LAW, "x")["text"]
        for line in text.splitlines(keepends=True):
            self.assertIn(line, source, "every line is copied from the source")
        self.assertEqual([a["id"] for a in outline(text)], [ids["Điều 2."], ids["Điều 3."]], "the excerpt keeps the same article IDs")

    def test_excerpt_refuses_empty_unknown_and_blocked_choices(self):
        ids = {a["heading"][:7]: a["id"] for a in outline(LAW)}
        for chosen, reason in (([], "ít nhất một"), (["chapter-ix/article-9"], "Không có Điều"), ([ids["Điều 4."]], "lồng nhau")):
            with self.assertRaisesRegex(ValueError, reason):
                excerpt(LAW, chosen)


if __name__ == "__main__":
    unittest.main()
