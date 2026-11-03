"""Extract the legal HTML embedded in VBPL's public Next.js document page.

Supports the observed Flight T (UTF-8 byte length) format. Fails closed when
the page no longer has exactly one legal body; never parses navigation as law.
"""

from html.parser import HTMLParser
import json
import re


def legal_html(snapshot_html):
    chunks = re.findall(r"self\.__next_f\.push\((\[1,.*?\])\)</script>", snapshot_html)
    stream = "".join(json.loads(chunk)[1] for chunk in chunks)
    raw = stream.encode("utf-8")
    bodies = []
    for match in re.finditer(rb"(?:^|\n)([0-9a-f]+):T([0-9a-f]+),", raw):
        size = int(match.group(2), 16)
        fragment = raw[match.end():match.end() + size]
        if len(fragment) != size:
            raise ValueError("truncated VBPL text payload")
        body = fragment.decode("utf-8")
        if "prov-article" in body and "<p" in body:
            bodies.append(body)
    if len(bodies) != 1:
        raise ValueError(f"expected one VBPL legal body, found {len(bodies)}")
    return bodies[0]


class Paragraphs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks, self.current, self.parts, self.index = [], None, [], 0

    def handle_starttag(self, tag, attrs):
        if tag == "p":
            if self.current is not None:
                raise ValueError("nested paragraphs: review HTML source")
            self.index += 1
            attributes = dict(attrs)
            self.current = {"locator": f"p:nth-of-document({self.index})", "html_id": attributes.get("id"), "html_class": attributes.get("class", "")}
            self.parts = []
        elif tag == "br" and self.current is not None:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.current is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "p" and self.current is not None:
            text = "".join(self.parts)
            if text.strip():
                self.blocks.append({**self.current, "text": text})
            self.current, self.parts = None, []


def extract_paragraphs(body):
    parser = Paragraphs()
    parser.feed(body)
    if parser.current is not None or not parser.blocks:
        raise ValueError("incomplete/empty legal paragraphs")
    position, spans, texts = 0, [], []
    for block in parser.blocks:
        text = block["text"] + "\n"
        spans.append({**block, "start": position, "end": position + len(text)})
        texts.append(text)
        position += len(text)
    return {"text": "".join(texts), "paragraphs": spans}
