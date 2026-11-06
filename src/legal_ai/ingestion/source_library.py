"""Pinned local excerpts. Listing/preparing a library item never contacts the network."""

import json
from pathlib import Path

from legal_ai.common.io import digest


class SourceLibrary:
    def __init__(self, catalog=None):
        self.catalog = Path(catalog).resolve() if catalog else None

    def entries(self):
        if self.catalog is None:
            return []
        value = json.loads(self.catalog.read_text(encoding="utf-8"))
        if value.get("schema_version") != "source-library-v1":
            raise ValueError("Unsupported source catalog version")
        return value["entries"]

    def prepare(self, store, source_id):
        entry = next((e for e in self.entries() if e["id"] == source_id), None)
        if entry is None:
            raise ValueError("Nguồn không có trong thư viện đã chuẩn bị")
        path = (self.catalog.parent / entry["file"]).resolve()
        if not path.is_relative_to(self.catalog.parent):
            raise ValueError("Source path left catalog directory")
        raw = path.read_bytes()
        if digest(raw) != entry["sha256"]:
            raise ValueError("Checksum nguồn không khớp; không tạo bản nháp")
        return store.prepare(entry["title"], raw.decode("utf-8"), synthetic=False, source_url=entry["source_url"])
