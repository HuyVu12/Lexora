"""Demo store builder: accounts with random passwords, a frozen scope corpus, no knowledge base. Synthetic snapshot."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_corpus import vbpl_snapshot
from legal_ai.auth import AccountStore
from legal_ai.demo_setup import build
from legal_ai.kb.import_review import ReviewStore
from legal_ai.research.corpus import CorpusStore


class DemoSetupTests(unittest.TestCase):
    def test_demo_store_has_accounts_a_frozen_corpus_and_no_unreviewed_knowledge_base(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest, raw = vbpl_snapshot(content="<p>Điều 1. Phạm vi</p><p>Văn bản giả định.</p><p>Điều 2. Thử việc</p><p>1. Bên A phải báo trước.</p>")
            snapshot = root / "raw" / "139264" / manifest["source_sha256"]
            snapshot.mkdir(parents=True)
            (snapshot / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (snapshot / "document.json").write_bytes(raw)
            scope = root / "scope.json"
            scope.write_text(json.dumps({"scope_version": "experiment-scope-v1", "name": "Phạm vi thử", "description": "Thử",
                                         "documents": [{"document_id": "luat-gia-dinh", "vbpl_id": "139264", "snapshot_sha256": manifest["source_sha256"],
                                                        "articles": ["2"]}]}, ensure_ascii=False), encoding="utf-8")
            store = root / "demo.sqlite"
            result = build(store, scope, raw_dir=root / "raw")
            accounts = AccountStore(store)
            passwords = {username: password for username, _, password in result["accounts"]}
            self.assertEqual(sorted(passwords), ["admin", "dev", "nhansu", "phapche"])
            self.assertEqual(len(set(passwords.values())), 4, "every account gets its own random password")
            _token, account = accounts.login("phapche", passwords["phapche"])
            self.assertEqual(account["role"], "reviewer")
            corpus = CorpusStore(store).corpus(result["corpus"]["id"])
            self.assertEqual((len(corpus["versions"]), corpus["documents"][0]["article_count"]), (1, 1))
            self.assertEqual(ReviewStore(store).knowledge_bases(), [], "no knowledge base until a person reviews one")
            self.assertNotIn(passwords["admin"], store.read_bytes().decode("latin-1"), "passwords are never stored in clear")
            with self.assertRaisesRegex(ValueError, "new file"):
                build(store, scope, raw_dir=root / "raw")


if __name__ == "__main__":
    unittest.main()
