"""Plain statute text from an uploaded file: TXT, HTML, DOCX or a PDF with a text layer.

TXT, HTML and DOCX use the standard library; PDF needs `pypdf` (the `web` extra) and is imported only when a
PDF arrives. A scanned PDF has no text layer and is refused with a message asking for OCR or another format.
The returned text still goes through `normalization.text.normalize`, which all evidence offsets anchor to.
"""

from html.parser import HTMLParser
import io
from pathlib import PurePath
import re
import zipfile
from xml.etree import ElementTree

from legal_ai.ingestion.vbpl_html import extract_paragraphs

MAX_FILE_BYTES = 20_000_000
FORMATS = {".txt": "txt", ".html": "html", ".htm": "html", ".docx": "docx", ".pdf": "pdf"}
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_BLOCKS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "table", "section", "article"}


class _BlockText(HTMLParser):
    """Text of any HTML page, one line per block element; scripts and styles dropped."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "head"}:
            self.skip += 1
        elif tag in _BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "head"}:
            self.skip = max(0, self.skip - 1)
        elif tag in _BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def _lines(text):
    """Trim each line, drop empty lines; keeps line order so Điều/Khoản headings stay on their own lines."""
    return "".join(line.strip() + "\n" for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip())


def _decode(data):
    for bom, codec in ((b"\xef\xbb\xbf", "utf-8"), (b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16")):
        if data.startswith(bom):
            return data.decode(codec).lstrip("﻿")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("the file is not UTF-8 text; save it as UTF-8 and try again") from exc


def _html(data):
    text = _decode(data)
    try:
        return extract_paragraphs(text)["text"]
    except ValueError:
        parser = _BlockText()
        parser.feed(text)
        return _lines("".join(parser.parts))


def _docx(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            xml = archive.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise ValueError("the file is not a valid DOCX document") from exc
    paragraphs = []
    for paragraph in ElementTree.fromstring(xml).iter(f"{_W}p"):
        parts = []
        for node in paragraph.iter():
            if node.tag == f"{_W}t":
                parts.append(node.text or "")
            elif node.tag == f"{_W}tab":
                parts.append(" ")
            elif node.tag in {f"{_W}br", f"{_W}cr"}:
                parts.append("\n")
        paragraphs.append("".join(parts))
    return _lines("\n".join(paragraphs))


def _pdf(data):
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as exc:
        raise ValueError("PDF import needs pypdf: install the web extra (pip install -e \".[web]\")") from exc
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ValueError("the PDF is password protected")
        pages = [page.extract_text() or "" for page in reader.pages]
    except PdfReadError as exc:
        raise ValueError("the file is not a readable PDF") from exc
    text = _lines("\n".join(pages))
    if len(re.sub(r"\s", "", text)) < 20 * max(1, len(pages)):  # Scans yield next to nothing per page.
        raise ValueError("the PDF has almost no text layer (probably scanned); use OCR or a DOCX/TXT/HTML copy")
    return text


def extract_text(filename, data):
    """{"format", "text", "warnings"} for an uploaded file; ValueError with a reader-facing reason otherwise."""
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise ValueError("the file is empty")
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("the file exceeds 20 MB")
    kind = FORMATS.get(PurePath(filename or "").suffix.lower())
    if kind is None:
        raise ValueError("supported files: TXT, HTML, DOCX, PDF with a text layer")
    text = {"txt": lambda d: _lines(_decode(d)), "html": _html, "docx": _docx, "pdf": _pdf}[kind](bytes(data))
    if not text.strip():
        raise ValueError("no text found in the file")
    warnings = []
    if kind == "pdf":
        warnings.append("pdf_line_breaks")  # PDF lines wrap mid-sentence; check headings in the parser report.
    if not re.search(r"(?m)^Điều\s+\d+", text):
        warnings.append("no_article_headings")
    return {"format": kind, "text": text, "warnings": warnings}
