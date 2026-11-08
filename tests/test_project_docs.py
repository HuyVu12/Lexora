"""Project documents for the Documents page: Markdown files with front matter, listed and served by slug."""

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.guides import Guides


class ProjectDocsTests(unittest.TestCase):
    def test_documents_are_listed_by_order_and_served_by_safe_slug_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "b-guide.md").write_text("---\ntitle: Hướng dẫn B\ncategory: Gán nhãn\norder: 20\nupdated: 2026-11-08\n---\n\n## Mục\nNội dung.\n", encoding="utf-8")
            (root / "a-guide.md").write_text("---\ntitle: Hướng dẫn A\nsummary: Tóm tắt\norder: 10\n---\nA\n", encoding="utf-8")
            (root / "plain.md").write_text("Không có front matter\n", encoding="utf-8")
            (root / "Bad Name.md").write_text("x", encoding="utf-8")
            (root / "secret.txt").write_text("x", encoding="utf-8")
            guides = Guides(root)
            listed = guides.list()
            self.assertEqual([d["slug"] for d in listed], ["a-guide", "b-guide", "plain"])
            self.assertEqual((listed[1]["category"], listed[1]["updated"], listed[2]["title"], listed[2]["category"]),
                             ("Gán nhãn", "2026-11-08", "plain", "Khác"))
            self.assertEqual(guides.get("b-guide")["markdown"].strip(), "## Mục\nNội dung.")
            for slug in ("../secret", "secret", "Bad Name", "b-guide.md", ""):
                with self.assertRaises(KeyError):
                    guides.get(slug)

    def test_repository_documents_have_titles_and_categories(self):
        documents = Guides(ROOT / "docs" / "guides").list()
        self.assertIn("huong-dan-gan-nhan", [d["slug"] for d in documents])
        self.assertTrue(all(d["title"] != d["slug"] and d["category"] != "Khác" and d["updated"] for d in documents),
                        "every shipped document declares title, category and updated in its front matter")


if __name__ == "__main__":
    unittest.main()
