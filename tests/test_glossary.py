"""The hover glossary covers every review word the UI shows and embeds safely in each page."""

import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.glossary import GLOSSARY, MARKER, embed_terms, glossary_json
from legal_ai.schemas.contract import MODALITY_CUES

SRC = ROOT / "src" / "legal_ai"


class GlossaryTests(unittest.TestCase):
    def test_every_slot_and_modality_label_has_an_explanation(self):
        app = (SRC / "demo-app.js").read_text(encoding="utf-8")
        slots = re.search(r"const SLOT = \{(.*?)\};", app, re.S).group(1)
        modalities = re.search(r"const MODALITY = \{(.*?)\};", app, re.S).group(1)
        for key in re.findall(r"(\w+):", slots):
            self.assertIn(key, GLOSSARY, key)
        for key in re.findall(r"(\w+):", modalities):
            self.assertIn("unknown_modality" if key == "unknown" else key, GLOSSARY, key)
        viewer = (SRC / "kb" / "entity-viewer.html").read_text(encoding="utf-8")
        roles = re.search(r"const roles=\{(.*?)\};", viewer).group(1)
        for key in re.findall(r"(\w+):", roles):
            self.assertIn(key, GLOSSARY, key)

    def test_every_data_term_used_in_markup_exists(self):
        for name in ("demo-app.js", "kb/entity-viewer.html", "kb/viewer.html"):
            text = (SRC / name).read_text(encoding="utf-8")
            for key in re.findall(r"""data-term["']?[:=]\s*["'](\w+)["']""", text):
                self.assertIn(key, GLOSSARY, f"{name}: {key}")
            for key in re.findall(r"""\bterm\('(\w+)'""", text):
                self.assertIn(key, GLOSSARY, f"{name}: {key}")

    def test_entries_are_complete_and_examples_contain_their_highlight(self):
        for key, entry in GLOSSARY.items():
            self.assertTrue(entry["term"] and entry["definition"], key)
            self.assertNotIn("\u2014", json.dumps(entry, ensure_ascii=False), key)
            if "highlight" in entry:
                self.assertIn(entry["highlight"], entry["example"], key)

    def test_modality_cues_named_in_glossary_are_cues_lexora_accepts(self):
        for modality, cues in MODALITY_CUES.items():
            named = {cue.strip() for cue in GLOSSARY[modality]["cues"].split(",")}
            self.assertEqual(named, cues, modality)

    def test_embedding_replaces_marker_once_and_escapes_script_markup(self):
        page = embed_terms(f"<body>{MARKER}<script>main()</script></body>")
        self.assertNotIn(MARKER, page)
        self.assertIn('<script id="lexora-glossary" type="application/json">', page)
        self.assertIn("<script data-lexora-terms>", page)
        self.assertNotIn("</", glossary_json())
        with self.assertRaises(ValueError):
            embed_terms("<body>no marker</body>")

    def test_english_glossary_covers_every_key_without_em_dashes(self):
        from legal_ai.glossary import bilingual
        from legal_ai.glossary_en import GLOSSARY_EN
        self.assertEqual(set(GLOSSARY_EN), set(GLOSSARY))
        for key, both in bilingual().items():
            self.assertTrue(both["en"]["term"] and both["en"]["definition"], key)
            self.assertEqual(both["en"].get("example"), GLOSSARY[key].get("example"), key)
            self.assertEqual("cues" in both["en"], "cues" in GLOSSARY[key], key)
            self.assertNotIn("\u2014", str(both["en"]), key)

    def test_all_pages_carry_the_marker(self):
        for name in ("demo.html", "kb/entity-viewer.html", "kb/viewer.html"):
            self.assertEqual((SRC / name).read_text(encoding="utf-8").count(MARKER), 1, name)


if __name__ == "__main__":
    unittest.main()
