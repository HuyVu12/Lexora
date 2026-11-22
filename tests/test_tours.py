"""Every step-by-step tour has its strings in both languages and points at elements that exist in the UI."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend" / "src"
TOURS = FRONTEND / "lib" / "tour" / "tours"
KEY = re.compile(r"'(tour\.[\w.]+)'")
TARGET = re.compile(r"\btarget: '([\w-]+)'")
STATIC_ANCHOR = re.compile(r'data-tour="([\w-]+)"')
# Anchors set from data (a nav item's `tour: 'nav-home'` rendered as data-tour={item.tour}).
DATA_ANCHOR = re.compile(r"\btour: '([\w-]+)'")
# Anchors built from a prefix and data (a tab's data-tour="tab-{tab.id}"): any target with that prefix counts.
PREFIX_ANCHOR = re.compile(r'data-tour="([\w-]+-)\{')


def steps(text):
    """Each step object literal (`{ id: '...', ... }`), nested braces included."""
    for match in re.finditer(r"\{\s*id: '", text):
        depth = 0
        for end in range(match.start(), len(text)):
            depth += {"{": 1, "}": -1}.get(text[end], 0)
            if depth == 0:
                yield text[match.start() : end + 1]
                break


def keys(name):
    return set(re.findall(r"^\t'([^']+)':", (FRONTEND / "lib" / "i18n" / name).read_text(encoding="utf-8"), re.M))


class TourTests(unittest.TestCase):
    def setUp(self):
        # Tour files are the ones that define a tour; index.ts and helpers such as routes.ts do not.
        every = {path: path.read_text(encoding="utf-8") for path in TOURS.glob("*.ts")}
        self.files = {path: text for path, text in every.items() if re.search(r": Tour = \{", text)}
        self.ui = {path: path.read_text(encoding="utf-8") for path in FRONTEND.rglob("*.svelte")}

    def test_tours_are_registered(self):
        index = (TOURS / "index.ts").read_text(encoding="utf-8")
        self.assertGreaterEqual(len(self.files), 7)
        for path, text in self.files.items():
            exported = re.findall(r"export const (\w+): Tour", text)
            self.assertTrue(exported, path.name)
            for name in exported:
                self.assertRegex(index, rf"\b{name}\b", f"{path.name}: {name} is not listed in tours/index.ts")

    def test_tour_strings_exist_in_both_languages(self):
        vi, en = keys("vi.ts"), keys("en.ts")
        engine = [FRONTEND / "lib" / "components" / name for name in ("TourOverlay.svelte", "GuideButton.svelte", "PageGuide.svelte", "TopBar.svelte", "TourHelp.svelte")]
        sources = list(self.files.items()) + [(path, path.read_text(encoding="utf-8")) for path in engine]
        used = {(path, key) for path, text in sources for key in KEY.findall(text)}
        self.assertGreater(len(used), 100)
        for path, key in sorted(used):
            self.assertIn(key, vi, f"{path.relative_to(ROOT)}: {key}")
            self.assertIn(key, en, f"{path.relative_to(ROOT)}: {key}")

    def test_every_step_has_a_title_and_a_body(self):
        for path, text in self.files.items():
            found = list(steps(text))
            self.assertGreater(len(found), 3, path.name)
            for step in found:
                self.assertIn("title: 'tour.", step, f"{path.name}: {step[:80]}")
                self.assertIn("body: 'tour.", step, f"{path.name}: {step[:80]}")
                if "wait:" in step:
                    self.assertIn("hint: 'tour.", step, f"{path.name}: a waiting step needs a hint: {step[:80]}")

    def test_targets_exist_in_the_ui(self):
        anchors = set()
        prefixes = set()
        for text in self.ui.values():
            anchors |= set(STATIC_ANCHOR.findall(text))
            prefixes |= set(PREFIX_ANCHOR.findall(text))
            if "data-tour={" in text:
                anchors |= set(DATA_ANCHOR.findall(text))
        targets = {(path, target) for path, text in self.files.items() for target in TARGET.findall(text)}
        self.assertGreater(len(targets), 20)
        for path, target in sorted(targets):
            if any(target.startswith(prefix) for prefix in prefixes):
                continue
            self.assertIn(target, anchors, f"{path.name}: no element carries data-tour=\"{target}\"")

    def test_no_em_dash_in_tour_strings(self):
        for name in ("vi.ts", "en.ts"):
            for line in (FRONTEND / "lib" / "i18n" / name).read_text(encoding="utf-8").splitlines():
                if line.startswith("\t'tour."):
                    self.assertNotIn("—", line, line)


if __name__ == "__main__":
    unittest.main()
