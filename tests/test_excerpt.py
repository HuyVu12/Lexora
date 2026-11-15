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

    def test_a_repeated_chapter_heading_blocks_the_article_before_it_unless_stray_headings_are_cut(self):
        law = ("Chương I\nQUY ĐỊNH CHUNG\nĐiều 1. Phạm vi\n1. Khoản một.\n2. Khoản hai.\n"
               "Chương I\nĐIỀU KHOẢN THI HÀNH\nĐiều 2. Hiệu lực\nVăn bản có hiệu lực từ ngày ký.\n")
        default = {a["id"]: a for a in outline(law)}
        self.assertEqual((default["chapter-i/article-1"]["blocked"], default["chapter-i/article-1"]["reason"]), (True, "duplicate_heading"),
                         "the default stays as frozen corpus versions were built")
        relaxed = {a["id"]: a for a in outline(law, cut_stray_headings=True)}
        self.assertFalse(relaxed["chapter-i/article-1"]["blocked"])
        text = excerpt(law, ["chapter-i/article-1"], cut_stray_headings=True)
        self.assertTrue(text.endswith("2. Khoản hai.\n"), "the excerpt stops before the stray heading")
        self.assertNotIn("ĐIỀU KHOẢN THI HÀNH", text)
        with self.assertRaisesRegex(ValueError, "lồng nhau"):
            excerpt(law, ["chapter-i/article-1"])
        points = "Chương I\nA\nĐiều 1. Trách nhiệm\n1. Bộ:\nd) Việc một;\nd) Việc hai.\n"
        self.assertTrue(outline(points, cut_stray_headings=True)[0]["blocked"], "a repeated point label still blocks: which unit is meant would be a guess")

    def test_excerpt_refuses_empty_unknown_and_blocked_choices(self):
        ids = {a["heading"][:7]: a["id"] for a in outline(LAW)}
        for chosen, reason in (([], "ít nhất một"), (["chapter-ix/article-9"], "Không có Điều"), ([ids["Điều 4."]], "lồng nhau")):
            with self.assertRaisesRegex(ValueError, reason):
                excerpt(LAW, chosen)


if __name__ == "__main__":
    unittest.main()
