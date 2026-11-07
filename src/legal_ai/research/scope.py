"""Experiment scope: a research corpus made of chosen articles of pinned vbpl.vn snapshots (`experiment-scope-v1`).

The scope file names, per document, the snapshot SHA-256 under `data/raw/vbpl/<vbpl_id>/<sha>/` and the article
numbers to keep ("13-48" is a range). `build_scope` adds every document to a new corpus as a verbatim excerpt of
those articles with their chapter/section headings, so DK1-DK4, the question set and the extraction gold set all
read the same text. No network: the snapshots must already be on disk.
"""

import json
from pathlib import Path

from legal_ai.ingestion.excerpt import outline
from legal_ai.ingestion.vbpl_api import document_text, unwrap

SCOPE_VERSION = "experiment-scope-v1"


def article_numbers(spec):
    """["3", "13-15"] -> ["3", "13", "14", "15"]; labels such as "4a" stay as they are."""
    numbers = []
    for item in spec:
        if "-" in item:
            first, last = (int(part) for part in item.split("-", 1))
            if first > last:
                raise ValueError(f"empty article range: {item}")
            numbers.extend(str(n) for n in range(first, last + 1))
        else:
            numbers.append(item.strip().lower())
    if len(set(numbers)) != len(numbers):
        raise ValueError("an article is listed twice")
    return numbers


def outline_ids(text, numbers):
    """Outline IDs of the articles with these numbers; every number must name exactly one article."""
    by_number = {}
    for article in outline(text):
        by_number.setdefault(article["id"].rsplit("article-", 1)[1], []).append(article)
    ids = []
    for number in numbers:
        found = by_number.get(number, [])
        if len(found) != 1:
            raise ValueError(f"article {number}: {len(found)} matches")
        if found[0]["blocked"]:
            raise ValueError(f"article {number} has a quoted amendment ({found[0]['reason']}) and cannot be excerpted")
        ids.append(found[0]["id"])
    return ids


def load_scope(path):
    scope = json.loads(Path(path).read_text(encoding="utf-8"))
    if scope.get("scope_version") != SCOPE_VERSION:
        raise ValueError(f"scope file must be {SCOPE_VERSION}")
    return scope


def build_scope(store, scope_path, actor, raw_dir="data/raw/vbpl"):
    """Create the scope's corpus in `store` (a CorpusStore) and add every document; returns the corpus."""
    scope = load_scope(scope_path)
    planned = []  # Resolve every document first so a bad entry leaves no half-built corpus.
    for entry in scope["documents"]:
        folder = Path(raw_dir) / entry["vbpl_id"] / entry["snapshot_sha256"]
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        raw = (folder / "document.json").read_bytes()
        text = document_text(unwrap(raw))["text"]
        planned.append((entry["document_id"], manifest, raw, outline_ids(text, article_numbers(entry["articles"]))))
    corpus = store.create(scope["name"], scope["description"], actor)
    for document_id, manifest, raw, ids in planned:
        store.add_vbpl(corpus["id"], manifest, raw, actor, document_id, ids)
    return store.corpus(corpus["id"])
