"""Immutable, explicitly invoked snapshots from approved official hosts."""

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, HTTPRedirectHandler, build_opener
import json
import re

from legal_ai.common.io import digest, write_json

ALLOWED_HOSTS = {"vbpl.vn", "www.vbpl.vn", "vbpl.moj.gov.vn"}


class OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlparse(newurl)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError("redirect left approved HTTPS hosts")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def snapshot(url, destination, document_id, expected_marker):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", document_id):
        raise ValueError("document ID must be a simple lowercase slug")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("only approved HTTPS vbpl hosts are supported")
    request = Request(url, headers={"User-Agent": "Lexora-Pilot/0.1 (academic source snapshot)"})
    with build_opener(OfficialRedirects()).open(request, timeout=30) as response:
        final_url = response.url
        if urlparse(final_url).hostname not in ALLOWED_HOSTS or urlparse(final_url).scheme != "https":
            raise ValueError("redirect left approved HTTPS hosts")
        content_type = response.headers.get("Content-Type", "")
        charset = response.headers.get_content_charset() or "utf-8"
        data = response.read(10_000_001)
    if len(data) > 10_000_000:
        raise ValueError("snapshot exceeds 10 MB pilot limit")
    text = data.decode(charset, errors="strict")
    if "html" not in content_type.lower() or expected_marker not in text or "Điều" not in text:
        raise ValueError("response is not the expected legal HTML; inspect before use")
    from legal_ai.ingestion.vbpl_html import legal_html
    legal_html(text)
    sha = digest(data)
    folder = Path(destination) / document_id / sha
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "snapshot.html"
    if target.exists() and target.read_bytes() != data:
        raise ValueError("immutable snapshot collision")
    if not target.exists():
        with target.open("xb") as stream:
            stream.write(data)
    metadata = {"document_id": document_id, "source_url": url, "download_url": final_url, "accessed_at": datetime.now(timezone.utc).isoformat(), "source_sha256": sha, "mime_type": content_type, "charset": charset, "local_path": target.as_posix(), "expected_marker": expected_marker, "legal_status": "unknown", "effective_from": None, "effective_to": None, "review_status": "needs_manual_review"}
    manifest = folder / "manifest.json"
    if not manifest.exists():
        write_json(manifest, metadata)
    return json.loads(manifest.read_text(encoding="utf-8"))
