"""Project documents shown on the in-app Documents page (`guides-v1`).

Each document is one Markdown file in the guides folder (default `docs/guides`). It starts with a small front matter
block of `key: value` lines between `---` lines:

    ---
    title: Hướng dẫn gán nhãn
    summary: One sentence shown on the list.
    category: Gán nhãn
    order: 10
    updated: 2026-11-08
    ---

The file name without `.md` is the slug (lower-case letters, digits and hyphens only). Adding a document means adding
a file; nothing else changes. The app renders the Markdown itself; files are read-only data, never executed.
"""

from pathlib import Path
import re

GUIDES_VERSION = "guides-v1"
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")
MAX_BYTES = 400_000


def _split(text):
    meta, body = {}, text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end > 0:
            for line in text[4:end].splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta[key.strip().lower()] = value.strip()
            body = text[end + 5:]
    return meta, body


def _entry(path, meta):
    try:
        order = int(meta.get("order", 1000))
    except ValueError:
        order = 1000
    return {"slug": path.stem, "title": meta.get("title") or path.stem, "summary": meta.get("summary", ""),
            "category": meta.get("category", "Khác"), "order": order, "updated": meta.get("updated")}


class Guides:
    def __init__(self, folder="docs/guides"):
        self.folder = Path(folder)

    def _files(self):
        if not self.folder.is_dir():
            return []
        return [p for p in sorted(self.folder.glob("*.md")) if SLUG.match(p.stem) and p.is_file() and p.stat().st_size <= MAX_BYTES]

    def list(self):
        entries = [_entry(path, _split(path.read_text(encoding="utf-8-sig"))[0]) for path in self._files()]
        return sorted(entries, key=lambda e: (e["order"], e["title"]))

    def get(self, slug):
        if not isinstance(slug, str) or not SLUG.match(slug):
            raise KeyError("Không tìm thấy tài liệu")
        path = self.folder / f"{slug}.md"
        if path not in self._files():
            raise KeyError("Không tìm thấy tài liệu")
        meta, body = _split(path.read_text(encoding="utf-8-sig"))
        return _entry(path, meta) | {"markdown": body.replace("\r\n", "\n")}
