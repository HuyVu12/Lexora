"""Every page guide has its strings in both languages, and step badges stay within the guide's steps."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend" / "src"
GUIDE = re.compile(r'<PageGuide name="(\w+)"(?: steps=\{(\d+)\})?( note)?')


def keys(name):
    return set(re.findall(r"^\t'([^']+)':", (FRONTEND / "lib" / "i18n" / name).read_text(encoding="utf-8"), re.M))


class GuideTests(unittest.TestCase):
    def setUp(self):
        self.pages = {path: path.read_text(encoding="utf-8") for path in (FRONTEND / "routes").rglob("+page.svelte")}

    def test_guides_have_their_strings_in_both_languages(self):
        vi, en = keys("vi.ts"), keys("en.ts")
        used = [(path, match) for path, text in self.pages.items() for match in GUIDE.finditer(text)]
        self.assertGreaterEqual(len(used), 14)
        for path, match in used:
            name, steps, note = match.group(1), int(match.group(2) or 0), bool(match.group(3))
            needed = [f"guide.{name}.page", f"guide.{name}.purpose"] + [f"guide.{name}.{n}{s}" for n in range(1, steps + 1) for s in ("", ".d")]
            needed += [f"guide.{name}.note"] if note else []
            for key in needed:
                self.assertIn(key, vi, f"{path.relative_to(ROOT)}: {key}")
                self.assertIn(key, en, f"{path.relative_to(ROOT)}: {key}")
            self.assertNotIn(f"guide.{name}.{steps + 1}", vi, f"{name}: the guide shows fewer steps than written")

    def test_step_badges_stay_within_the_guide(self):
        for path, text in self.pages.items():
            badges = [int(n) for n in re.findall(r"<StepTag n=\{(\d+)\}", text)]
            if not badges:
                continue
            guides = [int(m.group(2) or 0) for m in GUIDE.finditer(text)]
            self.assertTrue(guides, f"{path.relative_to(ROOT)} has step badges but no guide")
            self.assertLessEqual(max(badges), max(guides), path.relative_to(ROOT))


if __name__ == "__main__":
    unittest.main()
