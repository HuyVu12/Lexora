"""The CLI dispatcher: every branch can use the module-level helpers (a local import of one of them in any branch used
to make it unbound in all the others, which broke `cli search`)."""

import ast
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_retrieval_run import SYNTHETIC, bundle
from legal_ai import cli


class CliTests(unittest.TestCase):
    def test_main_never_rebinds_module_level_io_helpers(self):
        tree = ast.parse((ROOT / "src" / "legal_ai" / "cli.py").read_text(encoding="utf-8"))
        main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
        rebound = [alias.name for node in ast.walk(main) if isinstance(node, ast.ImportFrom) and node.module == "legal_ai.common.io"
                   for alias in node.names if alias.name in {"read_jsonl", "write_json", "write_jsonl", "digest"}]
        self.assertEqual(rebound, [])

    def test_search_runs_on_a_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            bundle(Path(folder), {"syn-a": SYNTHETIC})
            out = io.StringIO()
            with patch.object(sys, "argv", ["cli", "search", folder, "báo trước bao nhiêu ngày", "--top-k", "1"]), redirect_stdout(out):
                cli.main()
            result = json.loads(out.getvalue())
            self.assertEqual(len(result["results"]), 1)
            self.assertFalse(result["generated_answer"])


if __name__ == "__main__":
    unittest.main()
