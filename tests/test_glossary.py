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
FRONTEND = ROOT / "frontend" / "src"


class GlossaryTests(unittest.TestCase):
    def test_every_slot_modality_and_origin_label_has_an_explanation(self):
        roles = (FRONTEND / "lib" / "roles.ts").read_text(encoding="utf-8")
        for name in ("SLOT_ORDER", "MODALITIES"):
            values = re.search(rf"export const {name} = \[(.*?)\]", roles, re.S).group(1)
            for key in re.findall(r"'(\w+)'", values):
                self.assertIn(key, GLOSSARY, f"{name}: {key}")
        self.assertIn("unknown_modality", GLOSSARY)
        messages = (FRONTEND / "lib" / "i18n" / "vi.ts").read_text(encoding="utf-8")
        for key in re.findall(r"'origin\.(\w+)':", messages):
            self.assertIn(key, GLOSSARY, f"origin.{key}")
        viewer = (SRC / "kb" / "entity-viewer.html").read_text(encoding="utf-8")
        roles = re.search(r"const roles=\{(.*?)\};", viewer).group(1)
        for key in re.findall(r"(\w+):", roles):
            self.assertIn(key, GLOSSARY, key)

    def test_every_data_term_used_in_markup_exists(self):
        pages = [(path, path.relative_to(ROOT)) for path in FRONTEND.rglob("*.svelte")]
        pages += [(SRC / name, name) for name in ("kb/entity-viewer.html", "kb/viewer.html")]
        self.assertGreater(len(pages), 2)
        for path, name in pages:
            text = path.read_text(encoding="utf-8")
            for key in re.findall(r"""data-term["']?[:=]\s*["'](\w+)["']""", text):
                self.assertIn(key, GLOSSARY, f"{name}: {key}")
            for key in re.findall(r'<Term\b[^>]*\bkey="(\w+)"', text):
                self.assertIn(key, GLOSSARY, f"{name}: {key}")
            for key in re.findall(r"\bterm\('(\w+)'", text):
                self.assertIn(key, GLOSSARY, f"{name}: {key}")

    def test_entries_are_complete_and_examples_contain_their_highlight(self):
        for key, entry in GLOSSARY.items():
            self.assertTrue(entry["term"] and entry["definition"], key)
            self.assertNotIn("\u2014", json.dumps(entry, ensure_ascii=False), key)
            if "highlight" in entry:
                self.assertIn(entry["highlight"], entry["example"], key)

    def test_question_labels_built_from_codes_have_explanations(self):
        from legal_ai.research.questions import QUESTION_TYPES, STATUSES
        for kind in QUESTION_TYPES:
            self.assertIn(f"q_{kind}", GLOSSARY)
        for status in STATUSES:
            self.assertIn(f"expect_{status}", GLOSSARY)

    def test_every_parser_audit_code_has_an_explanation(self):
        import re
        parser = (ROOT / "src" / "legal_ai" / "ingestion" / "parser.py").read_text(encoding="utf-8")
        codes = set(re.findall(r'"code": "(\w+)"', parser)) | set(re.findall(r'\("(\w+_(?:quote|text))", index', parser))
        page = (ROOT / "frontend" / "src" / "routes" / "research" / "[id]" / "document" / "[row]" / "+page.svelte").read_text(encoding="utf-8")
        shown = set(re.findall(r"'(\w+)'", page.split("AUDIT_CODES = new Set([", 1)[1].split("]", 1)[0]))
        self.assertTrue({"duplicate_heading", "quoted_text", "appendix_start"} <= codes)
        self.assertEqual(codes, shown, "the document page lists every audit code the parser emits")
        for code in shown:
            self.assertIn(f"audit_{code}", GLOSSARY, code)

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

    def test_viewer_pages_carry_the_marker(self):
        for name in ("kb/entity-viewer.html", "kb/viewer.html"):
            self.assertEqual((SRC / name).read_text(encoding="utf-8").count(MARKER), 1, name)


if __name__ == "__main__":
    unittest.main()
