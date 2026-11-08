"""Build a fresh demo workspace store from local files only (`demo-store-v1`).

The store gets four accounts (admin, reviewer, reader, dev) with random passwords that are printed once and never
written to disk, and the experiment-scope research corpus frozen as version 1, built from the pinned vbpl.vn
snapshots under `data/raw/vbpl`. It holds no knowledge base: during the rehearsal a person imports, reviews and
publishes one, and the runbook (`docs/demo-runbook.md`) has them back the store up right after, so the backup holds
human-reviewed content only. No network, no model call.
"""

from pathlib import Path
import secrets

from legal_ai.auth import AccountStore
from legal_ai.kb.import_review import ReviewStore
from legal_ai.research.corpus import CorpusStore
from legal_ai.research.scope import build_scope

DEMO_VERSION = "demo-store-v1"
ACCOUNTS = (("admin", "Quản trị demo", "admin"), ("phapche", "Người duyệt pháp chế", "reviewer"), ("nhansu", "Người tra cứu nhân sự", "reader"),
            ("dev", "Giám sát kỹ thuật", "dev"))


def build(store_path, scope_path="configs/experiment-scope-v1.json", raw_dir="data/raw/vbpl"):
    """Create the demo store; returns {accounts: [(username, role, password)], corpus, version}."""
    store_path = Path(store_path)
    if store_path.exists():
        raise ValueError("the demo store must be a new file; an existing store keeps its data")
    ReviewStore(store_path)  # Creates the knowledge-base tables, empty.
    accounts = AccountStore(store_path)
    made = []
    for username, name, role in ACCOUNTS:
        password = secrets.token_urlsafe(12)
        accounts.create(username, name, role, password)
        made.append((username, role, password))
    corpora = CorpusStore(store_path)
    corpus = build_scope(corpora, scope_path, "admin", raw_dir=raw_dir)
    version = corpora.freeze(corpus["id"], "Phạm vi thực nghiệm, dựng bởi demo-build", "admin")
    return {"demo_version": DEMO_VERSION, "store": store_path.as_posix(), "accounts": made,
            "corpus": {"id": corpus["id"], "name": corpus["name"], "documents": len(corpus["documents"])},
            "version": {"id": version["id"], "number": version["number"], "bundle_sha256": version["bundle_sha256"]}}
