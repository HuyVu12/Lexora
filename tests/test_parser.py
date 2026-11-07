"""Parser rules of lexora-parser-v2: heading typos, quoted amendments, appendices. Synthetic text, not real law."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.ingestion.excerpt import outline
from legal_ai.ingestion.parser import PARSER_VERSION, parse
from legal_ai.normalization.text import normalize


def parsed(text):
    normalized = normalize(text, "doc/source.txt")
    return normalized["text"], parse(normalized, "doc", normalized["normalized_sha256"])


def ids(result):
    return [u["unit_id"].removeprefix("doc/") for u in result["units"]]


def codes(result):
    return [a["code"] for a in result["audit"]]


AMENDING = ("Điều 1. Sửa đổi nghị định giả định\n"
            "1. Sửa đổi, bổ sung khoản 2 Điều 3 như sau:\n"
            "“2. Người sử dụng lao động phải báo trước:\n"
            "a) Ít nhất 30 ngày;\n"
            "b) Ít nhất 3 ngày.”.\n"
            "2. Sửa đổi điểm a khoản 6 Điều 3 như sau:\n"
            "\"a) Được đào tạo ít nhất 1 năm.\".\n"
            "3. Bổ sung Điều 4a như sau:\n"
            "“Điều 4a. Điều mới\n"
            "1. Nội dung có thuật ngữ “người lao động” giữa câu.\n"
            "2. Nội dung khác.”\n"
            "Điều 2. Hiệu lực\n"
            "Nghị định giả định này có hiệu lực từ ngày ký.\n")


class ParserTests(unittest.TestCase):
    def test_quoted_amendment_stays_in_the_clause_that_quotes_it(self):
        text, result = parsed(AMENDING)
        self.assertEqual(result["parser_version"], PARSER_VERSION)
        self.assertEqual(ids(result), ["article-1", "article-1/clause-1", "article-1/clause-2", "article-1/clause-3", "article-2"])
        clause = next(u for u in result["units"] if u["unit_id"] == "doc/article-1/clause-1")
        self.assertIn("a) Ít nhất 30 ngày;\nb) Ít nhất 3 ngày.”.\n", clause["text"])
        self.assertEqual(clause["text"], text[clause["source_start"]:clause["source_end"]])
        quoted = [a for a in result["audit"] if a["code"] == "quoted_text"]
        self.assertEqual([a["unit_id"].removeprefix("doc/") for a in quoted], ["article-1/clause-1", "article-1/clause-2", "article-1/clause-3"])
        self.assertTrue(text[quoted[0]["offset"]:quoted[0]["end"]].startswith("“2. Người sử dụng"))
        self.assertTrue(text[quoted[2]["offset"]:quoted[2]["end"]].endswith("2. Nội dung khác.”\n"), "an inner balanced quote does not end the block")
        self.assertNotIn("duplicate_heading", codes(result))

    def test_quotes_that_hide_no_heading_are_not_audited(self):
        _, result = parsed("Điều 1. Giải thích từ ngữ\n“Người lao động” là người làm việc theo hợp đồng.\n1. Khoản một.\n")
        self.assertEqual(ids(result), ["article-1", "article-1/clause-1"])
        self.assertEqual(result["audit"], [])

    def test_unclosed_quote_is_ignored_and_audited(self):
        _, result = parsed("Điều 1. Một\n“Câu mở ngoặc mà không đóng.\n1. Khoản một.\nĐiều 2. Hai\nNội dung.\n")
        self.assertEqual(ids(result), ["article-1", "article-1/clause-1", "article-2"])
        self.assertEqual(codes(result), ["unclosed_quote"])

    def test_misspelled_article_heading_still_opens_the_article(self):
        _, result = parsed("Điều 37. Một\n1. Khoản.\nĐiêu 38. Chậm đóng\n1. Khoản.\nÐiều 39. Trốn đóng\nNội dung.\n")
        self.assertEqual(ids(result), ["article-37", "article-37/clause-1", "article-38", "article-38/clause-1", "article-39"])
        self.assertEqual([(a["code"], a["word"]) for a in result["audit"]], [("heading_variant", "Điêu"), ("heading_variant", "Ðiều")])
        _, upper = parsed("ĐIỀU 1. Một\nNội dung.\n")
        self.assertEqual(upper["audit"], [], "upper case is not a typo")

    def test_appendix_ends_the_structured_body(self):
        source = ("Điều 1. Một\n1. Khoản cuối.\nNơi nhận:\n- Như trên.\n"
                  "Phụ lục I\nMẫu số 01\nQUYẾT ĐỊNH:\nĐiều 1. Trích tiền ký quỹ của ...\n1. Số tài khoản ....\n")
        text, result = parsed(source)
        self.assertEqual(ids(result), ["article-1", "article-1/clause-1"])
        self.assertTrue(result["units"][-1]["text"].endswith("- Như trên.\n"))
        self.assertTrue(result["trailing_text"].startswith("Phụ lục I\n"))
        self.assertEqual(text[result["trailing_span"][0]:], result["trailing_text"])
        self.assertEqual(codes(result), ["appendix_start"])
        _, mention = parsed("Điều 1. Một\nBan hành kèm theo Phụ lục I của Nghị định.\n")
        self.assertEqual(mention["trailing_text"], "", "only a standalone appendix line ends the body")

    def test_excerpt_blocks_articles_with_quoted_amendments(self):
        self.assertEqual([(a["id"], a["blocked"], a["reason"]) for a in outline(AMENDING)],
                         [("article-1", True, "quoted_text"), ("article-2", False, None)])


if __name__ == "__main__":
    unittest.main()
