"""Official documents from vbpl.vn, the national legal database of the Ministry of Justice.

`fetch_document` makes one explicitly requested HTTPS GET to the public JSON gateway the vbpl.vn site itself
uses (`/api/qtdc/public/doc/{id}`; undocumented, so it may change) and stores the response bytes as an
immutable snapshot with their SHA-256. Nothing here runs on its own: a caller must ask for one document at a
time, and calls are spaced at least `MIN_INTERVAL` seconds apart. The site's search is behind bot protection
and is never automated; documents are found in the local catalog (`catalog.py`) or by a pasted link.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import threading
import time
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from legal_ai.common.io import digest, write_json
from legal_ai.ingestion.vbpl_html import extract_paragraphs

GATEWAY = "https://vbpl-bientap-gateway.moj.gov.vn/api/qtdc/public/doc/"
GATEWAY_HOST = "vbpl-bientap-gateway.moj.gov.vn"
SITE_HOSTS = {"vbpl.vn", "www.vbpl.vn"}
USER_AGENT = "Lexora/0.1 (academic legal research; one document per explicit request)"
MAX_BYTES = 20_000_000
MIN_INTERVAL = 2.0
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}")
_lock = threading.Lock()
_last_call = [0.0]


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("vbpl.vn trả về chuyển hướng; Lexora không đi theo")


def parse_reference(text):
    """vbpl.vn document ID from a pasted link (`.../van-ban/chi-tiet/139264`, `.../chi-tiet/<slug>--139264?tabs=...`)
    or from a bare ID. Links to other hosts are refused."""
    text = (text or "").strip()
    if _ID.fullmatch(text):
        return text
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in SITE_HOSTS:
        raise ValueError("Hãy dán link văn bản trên vbpl.vn hoặc mã văn bản vbpl.vn")
    match = re.search(r"/van-ban/chi-tiet/([^/?#]+)", parsed.path)
    if not match:
        raise ValueError("Link không phải trang văn bản của vbpl.vn (…/van-ban/chi-tiet/…)")
    tail = match.group(1)
    candidate = tail.rsplit("--", 1)[1] if "--" in tail else tail
    if not _ID.fullmatch(candidate):
        raise ValueError("Không đọc được mã văn bản trong link")
    return candidate


def _get(url, timeout):
    with _lock:
        wait = MIN_INTERVAL - (time.monotonic() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with build_opener(NoRedirects()).open(request, timeout=timeout) as response:
                final = urlparse(response.url)
                if final.scheme != "https" or final.hostname != GATEWAY_HOST:
                    raise ValueError("Phản hồi đến từ máy chủ không mong đợi")
                if "json" not in response.headers.get("Content-Type", "").lower():
                    raise ValueError("vbpl.vn không trả về JSON")
                data = response.read(MAX_BYTES + 1)
        finally:
            _last_call[0] = time.monotonic()
    if len(data) > MAX_BYTES:
        raise ValueError("Văn bản vượt giới hạn 20 MB")
    return data


def unwrap(data):
    """The `data` object of a successful gateway response, or ValueError with the gateway's message."""
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("vbpl.vn trả về JSON không hợp lệ") from exc
    if not isinstance(payload, dict) or payload.get("success") is not True or not isinstance(payload.get("data"), dict):
        message = payload.get("message") if isinstance(payload, dict) else None
        raise ValueError(f"vbpl.vn không trả về văn bản{': ' + message if message else ''}")
    return payload["data"]


def _date(value):
    return value[:10] if isinstance(value, str) and re.match(r"\d{4}-\d{2}-\d{2}", value) else None


def metadata(document):
    """Official metadata of a gateway document. `effect_status` is what vbpl.vn reports at access time."""
    status = document.get("effStatus") or {}
    kind = document.get("docType") or {}
    return {
        "vbpl_id": str(document.get("id")),
        "doc_num": document.get("docNum"),
        "title": document.get("title"),
        "doc_type": kind.get("name"),
        "issue_date": _date(document.get("issueDate")),
        "effective_from": _date(document.get("effFrom")),
        "effective_to": _date(document.get("effTo")),
        "effect_status": {"code": status.get("code"), "name": status.get("name")} if status else None,
        "agency": document.get("agencyName"),
        "is_translation": bool(document.get("isTranslationDoc")),
        "has_content": bool((document.get("documentContent") or {}).get("content")),
        "original_pdf": document.get("documentContentFileName") if document.get("hasOriginalPdf") else None,
    }


def document_text(document):
    """Plain statute text of a gateway document, paragraph by paragraph, ready for normalization."""
    content = (document.get("documentContent") or {}).get("content")
    if not content:
        raise ValueError("vbpl.vn không có nội dung chữ cho văn bản này (có thể chỉ có PDF); hãy tải tệp lên thay thế")
    return extract_paragraphs(content)


def fetch_document(reference, destination, timeout=60):
    """Fetch one document and store it under `destination/<vbpl_id>/<sha256>/` (document.json + manifest.json).
    Returns the manifest; an identical earlier snapshot is reused, a different body never overwrites it."""
    vbpl_id = parse_reference(reference)
    url = GATEWAY + vbpl_id
    data = _get(url, timeout)
    document = unwrap(data)
    if str(document.get("id")) != vbpl_id:
        raise ValueError("vbpl.vn trả về văn bản khác với văn bản yêu cầu")
    sha = digest(data)
    folder = Path(destination) / vbpl_id / sha
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "document.json"
    if target.exists() and target.read_bytes() != data:
        raise ValueError("Bản chụp bất biến bị trùng nhưng khác nội dung")
    if not target.exists():
        with target.open("xb") as stream:
            stream.write(data)
    manifest = folder / "manifest.json"
    if not manifest.exists():
        write_json(manifest, {"source": "vbpl.vn", "vbpl_id": vbpl_id, "api_url": url, "site_url": f"https://vbpl.vn/van-ban/chi-tiet/{vbpl_id}",
                              "accessed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "source_sha256": sha,
                              "local_path": target.as_posix(), "metadata": metadata(document), "review_status": "needs_manual_review"})
    return json.loads(manifest.read_text(encoding="utf-8"))
