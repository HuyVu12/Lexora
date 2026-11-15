"""Amendment edges by rule (`amendment-rules-v2`): which unit of which document an amending text modifies, adds to,
repeals, rewords or declares expired, each edge anchored to the exact instruction it comes from. No model.

Input is the normalized full text of an amending document (offsets and SHA-256 refer to that text) and the units of
the corpus the targets must be found in. The rules read the text line by line:

- an Article heading such as "Điều 1. Sửa đổi, bổ sung một số điều của Nghị định số 152/2020/NĐ-CP ..." sets the
  document that the following numbered instructions amend;
- an instruction line starts (after an optional "1." or "a)" marker) with "Sửa đổi, bổ sung", "Sửa đổi", "Bổ sung",
  "Bãi bỏ" or "Thay thế" followed by what it acts on (điểm, khoản, Điều, cụm từ, Mẫu...), so a provision that merely
  begins with "Thay thế người lao động ..." is not an instruction; a line naming a document ("... của Bộ luật Tố tụng
  dân sự số 92/2015/QH13 như sau:") binds the following items to it until the next Article; it names its targets ("điểm a và điểm b khoản 4 Điều 9", "khoản 5 Điều 3", "Điều 4",
  "điểm c, d, đ khoản 5 và điểm g khoản 6 Điều 30"); a line that only announces sub-items ("một số điểm, khoản của
  Điều 3") is a group and gives no edge;
- quoted text (the new wording that follows an instruction, or the phrases of "Thay thế cụm từ A bằng cụm từ B") is
  never read as an instruction or a target; the new wording right after an instruction is kept as `new_text`;
- a document number ("152/2020/NĐ-CP") maps to the corpus ID convention ("152-2020-nd-cp").

A target that is not in the corpus (another document, an annex form, a unit the corpus lacks) is kept with a status
and a reason, never guessed. The effective date of an edge is the amending document's `effective_from`; an
instruction with its own date is not detected (a stated limitation).

Version 2 (15/11/2026) keeps every edge v1 found, with the same target and status, and adds:

- `scope` on every edge: `unit` (the unit and everything below it), `own_text` for an instruction that rewrites only
  the heading or lead sentence of a unit ("Sửa đổi, bổ sung tên khoản 8 Điều 9 như sau:"; its points stay as they
  were), `phrase` for a phrase replacement, with the quoted `phrases` [[old, new], ...] so the status of each unit can
  follow from whether its own text holds an old phrase;
- expiry statements in an Article whose heading starts with "Hiệu lực" ("... hết hiệu lực thi hành kể từ ..."), on
  their own line or as the lettered items of a line announcing them ("các Nghị định sau đây hết hiệu lực thi hành:"):
  `expire` when units are named (resolved like any target), `expire_document` for a whole document (status
  `document`, or `external` outside the corpus; unit status keeps following the vbpl.vn dates of the document), and
  `expire_subject` when the statement scopes by subject matter ("Nội dung về lao động nước ngoài ... quy định tại
  Nghị định số 152/2020/NĐ-CP ... hết hiệu lực"): mapping that to units needs legal judgment, so the edge stays
  `unresolved` and is only reported.
"""

import re

from legal_ai.common.io import canonical, digest
from legal_ai.schemas.contract import text_hash

AMENDMENT_VERSION = "amendment-rules-v2"
KINDS = ("modify", "add", "repeal", "replace_phrase", "expire", "expire_document", "expire_subject")
SCOPES = ("unit", "own_text", "phrase")
_MARKER = re.compile(r"\s*(?:\d+[a-zđ]?\.|[a-zđ]\))\s+")
_VERB = re.compile(r"(Sửa đổi, bổ sung|Sửa đổi|Bổ sung|Bãi bỏ|Thay thế(?:, bổ sung)?)\s+(?=(?:một số\s+|các\s+|tên\s+)?"
                   r"(?:điểm|khoản|Điều|điều|cụm từ|từ|đoạn|Mẫu|Phụ lục|Chương|Mục|số thứ tự|quy định)\b)")
_DOC = re.compile(r"(?:Bộ luật|Luật|Nghị định|Thông tư|Nghị quyết)(?:[^\"“”\n]{0,80}?)\s+(?:số\s+)?(\d+/\d{4}/[A-ZĐa-zđ0-9]+(?:-[A-ZĐa-zđ0-9]+)*)")
_ARTICLE_HEADING = re.compile(r"Điều\s+\d+[a-zđ]?\.\s")
_ARTICLE = re.compile(r"Điều\s+(\d+[a-zđ]?)(?![\w/])")
_CLAUSES = re.compile(r"khoản\s+(\d+[a-zđ]?(?:\s*(?:,|và)\s*(?:khoản\s+)?\d+[a-zđ]?)*)", re.IGNORECASE)
_POINTS = re.compile(r"điểm\s+([a-zđ](?:\s*(?:,|và)\s*(?:điểm\s+)?[a-zđ])*)\s*$", re.IGNORECASE)
_GROUP = re.compile(r"một số|các\s+(?:điểm|khoản|điều)\b", re.IGNORECASE)
_ANNEX = re.compile(r"Mẫu số|Phụ lục", re.IGNORECASE)
_QUOTE = re.compile(r"[\"“][^\"“”]*[\"”]")
_OPEN = ("\"", "“")
_OWN_TEXT = re.compile(r"(?:Sửa đổi, bổ sung|Sửa đổi)\s+(?:tên|câu dẫn|đoạn dẫn|phần mở đầu|đoạn mở đầu)\s")
_PHRASE = re.compile(r"(?:cụm\s+)?từ\s*[\"“]([^\"“”]*)[\"”]")
_NEW_WORDING = re.compile(r"\b(?:bằng|thành)\b")
_EFFECT_HEADING = re.compile(r"Điều\s+\d+[a-zđ]?\.\s+Hiệu lực")
_EXPIRES = "hết hiệu lực"
_STRUCTURE = re.compile(r"\b(?:Mục|Chương|Phụ lục|Mẫu)\b")
_SUBJECT = re.compile(r"\s*(?:Nội dung|Các quy định|Những quy định|Quy định)\b")
_NUMBERED = re.compile(r"\s*\d+[a-zđ]?\.\s")
_LETTERED = re.compile(r"\s*[a-zđ]\)\s")


def document_id_of(number):
    """"152/2020/NĐ-CP" -> "152-2020-nd-cp", the corpus ID convention."""
    return number.replace("/", "-").replace("Đ", "D").replace("đ", "d").lower()


def _labels(text, word):
    return [x.casefold() for x in re.split(rf"\s*(?:,|và)\s*(?:{word}\s+)?", text.strip()) if x]


def parse_targets(line):
    """[(article, clause or None, point or None)] named by one instruction line, quoted phrases removed first."""
    clean = _QUOTE.sub(lambda m: " " * len(m.group()), line)
    targets, previous = [], 0
    for match in _ARTICLE.finditer(clean):
        segment = clean[previous:match.start()]
        previous = match.end()
        article = match.group(1).casefold()
        clauses = list(_CLAUSES.finditer(segment))
        if not clauses:
            targets.append((article, None, None))
            continue
        start = 0
        for clause in clauses:
            before = segment[start:clause.start()]
            start = clause.end()
            points = _POINTS.search(before)
            labels = _labels(clause.group(1), "khoản")
            point_labels = _labels(points.group(1), "điểm") if points else []
            for n, label in enumerate(labels):
                # "điểm c, d khoản 5": the points belong to the clause right after them (the last listed, as written).
                if point_labels and n == len(labels) - 1:
                    targets.extend((article, label, p) for p in point_labels)
                else:
                    targets.append((article, label, None))
    return list(dict.fromkeys(targets))


def phrases(instruction):
    """[[old, new], ...] of a phrase replacement, read from the quoted text: a quote after "bằng" or "thành" is the new
    wording of the quote before it; an old phrase without one keeps None."""
    pairs, previous = [], 0
    for match in _PHRASE.finditer(instruction):
        between = instruction[previous:match.start()]
        previous = match.end()
        if pairs and pairs[-1][1] is None and _NEW_WORDING.search(between):
            pairs[-1][1] = match.group(1)
        else:
            pairs.append([match.group(1), None])
    return pairs


def edge_scope(edge):
    """The scope of an edge; `amendment-rules-v1` edges carry none, so it is read from their instruction the same way."""
    if edge.get("scope"):
        return edge["scope"]
    if edge["kind"] == "replace_phrase":
        return "phrase"
    if edge["kind"] == "modify" and _OWN_TEXT.match(edge["instruction"]["text"]):
        return "own_text"
    return "unit"


def edge_phrases(edge):
    return edge["phrases"] if "phrases" in edge else phrases(edge["instruction"]["text"])


def _expiry(document, body, quote, units_by_doc, effective_from, sha, announced_doc=None):
    """Edges of one expiry statement (a line, or an item of an announced list) of an effect Article."""
    clean = _QUOTE.sub(lambda m: " " * len(m.group()), body)
    named = _DOC.search(clean)
    target_doc = document_id_of(named.group(1)) if named else announced_doc
    base = {"edge_version": AMENDMENT_VERSION, "amending_document_id": document["document_id"], "amending_text_sha256": sha,
            "instruction": quote, "effective_from": effective_from, "scope": "unit", "target_document_id": target_doc,
            "target": None, "target_unit_id": None, "anchor_unit_id": None}
    if target_doc is None:
        return [base | {"kind": "expire_document", "status": "unresolved", "reason": "no_target_named"}]
    segment = clean[:named.start()] if named else clean
    targets = parse_targets(segment)
    if targets:
        out = []
        for target in targets:
            unit, anchor, status, reason = _resolve(units_by_doc, target_doc, target)
            out.append(base | {"kind": "expire", "target": {"article": target[0], "clause": target[1], "point": target[2]},
                               "target_unit_id": unit["unit_id"] if unit else None, "anchor_unit_id": anchor["unit_id"] if anchor else None,
                               "status": status, "reason": reason})
        return out
    if _STRUCTURE.search(segment):
        return [base | {"kind": "expire", "status": "unresolved" if target_doc in units_by_doc else "external", "reason": "structure_target"}]
    if segment.strip() and _SUBJECT.match(segment):
        return [base | {"kind": "expire_subject", "status": "unresolved", "reason": "subject_scope_needs_legal_judgment"}]
    if target_doc not in units_by_doc:
        return [base | {"kind": "expire_document", "status": "external", "reason": "target_document_not_in_corpus"}]
    return [base | {"kind": "expire_document", "status": "document", "reason": None}]


def _kind(verb):
    return {"Sửa đổi, bổ sung": "modify", "Sửa đổi": "modify", "Bổ sung": "add", "Bãi bỏ": "repeal"}.get(verb, "replace_phrase")


def _resolve(units_by_doc, document_id, target):
    """The unit a target names in the corpus, its nearest existing ancestor for an added unit, and a status."""
    article, clause, point = target
    rows = units_by_doc.get(document_id)
    if rows is None:
        return None, None, "external", "target_document_not_in_corpus"
    found = [u for u in rows if u["unit_type"] == "article" and u["label"].casefold() == article]
    if len(found) != 1:
        return None, None, "unresolved", "article_not_found" if not found else "multiple_articles"
    unit = found[0]
    for kind, label in (("clause", clause), ("point", point)):
        if label is None:
            break
        child = [u for u in rows if u["parent_id"] == unit["unit_id"] and u["unit_type"] == kind and u["label"].casefold() == label]
        if len(child) != 1:
            return None, unit, "unresolved", f"{kind}_not_found" if not child else f"multiple_{kind}s"
        unit = child[0]
    return unit, unit, "resolved", None


def detect(document, text, units, effective_from=None):
    """Amendment edges of one amending document (`document`: {document_id, title?}) over its normalized `text`."""
    units_by_doc = {}
    for unit in units:
        units_by_doc.setdefault(unit["document_id"], []).append(unit)
    sha = text_hash(text)
    edges, context_doc, inside, position = [], None, False, 0
    effect, announced = False, None  # Inside an Article headed "Hiệu lực ..."; the open list of an announcing line.
    lines = text.split("\n")
    starts = []
    for line in lines:
        starts.append(position)
        position += len(line) + 1
    pending = []  # Edges waiting for the quoted new wording that follows their instruction.
    for number, line in enumerate(lines):
        start = starts[number]
        stripped = line.strip()
        if inside or stripped.startswith(_OPEN):
            if not inside:
                inside = True
                quote_start = start + line.index(stripped[0])
            if re.search(r"[\"”][.;,]?\s*$", stripped) and (len(stripped) > 1 or not stripped.startswith(_OPEN)):
                inside = False
                for edge in pending:
                    end = start + len(line.rstrip())
                    edge["new_text"] = {"start": quote_start, "end": end, "sha256": text_hash(text[quote_start:end])}
                pending = []
            continue
        pending = []
        if _ARTICLE_HEADING.match(stripped):
            doc = _DOC.search(stripped)
            heading_verb = _VERB.search(stripped[:120])
            context_doc = document_id_of(doc.group(1)) if doc and heading_verb else None
            effect, announced = bool(_EFFECT_HEADING.match(stripped)), None
            continue
        if effect:
            lead = _MARKER.match(line)
            body_at = lead.end() if lead else len(line) - len(line.lstrip())
            body = line[body_at:].rstrip()
            if _NUMBERED.match(line) or not _LETTERED.match(line):
                announced = None  # A new clause or a plain line closes an announced list.
            quote = {"start": start + body_at, "end": start + len(line.rstrip()), "text": body}
            if _EXPIRES in body and body.endswith(":"):
                named = _DOC.search(_QUOTE.sub(lambda m: " " * len(m.group()), body))
                announced = (document_id_of(named.group(1)) if named else None,)
                continue
            if _EXPIRES in body:
                edges += _expiry(document, body, quote, units_by_doc, effective_from, sha)
                continue
            if announced is not None and _LETTERED.match(line):
                edges += _expiry(document, body, quote, units_by_doc, effective_from, sha, announced[0])
                continue
        marker = _MARKER.match(line)
        body_at = marker.end() if marker else len(line) - len(line.lstrip())
        verb = _VERB.match(line, body_at)
        if not verb:
            continue
        instruction = line[body_at:]
        kind = _kind(verb.group(1))
        named = _DOC.search(_QUOTE.sub(lambda m: " " * len(m.group()), instruction))
        target_doc = document_id_of(named.group(1)) if named else context_doc
        context_doc = target_doc  # "1. Sửa đổi ... của Luật X như sau:" binds the items that follow, until the next Article.
        targets = parse_targets(instruction)
        quote = {"start": start + body_at, "end": start + len(line.rstrip()), "text": instruction.rstrip()}
        scope = "phrase" if kind == "replace_phrase" else "own_text" if kind == "modify" and _OWN_TEXT.match(instruction) else "unit"
        base = {"edge_version": AMENDMENT_VERSION, "kind": kind, "amending_document_id": document["document_id"],
                "amending_text_sha256": sha, "instruction": quote, "effective_from": effective_from, "scope": scope,
                **({"phrases": phrases(instruction)} if kind == "replace_phrase" else {})}
        if not targets:
            reason = "annex_target" if _ANNEX.search(instruction) else "no_target_named"
            if _GROUP.search(instruction) and not _ANNEX.search(instruction):
                continue  # "Sửa đổi, bổ sung một số khoản của Điều 7 như sau:" announces the lettered items below.
            edges.append(base | {"target_document_id": target_doc, "target": None, "target_unit_id": None, "anchor_unit_id": None,
                                 "status": "unresolved", "reason": reason})
            continue
        if _GROUP.search(instruction[:60]) and instruction.rstrip().endswith(":"):
            continue
        for target in targets:
            if target_doc is None:
                unit, anchor, status, reason = None, None, "unresolved", "target_document_not_named"
            else:
                unit, anchor, status, reason = _resolve(units_by_doc, target_doc, target)
            if kind == "add" and status == "unresolved" and anchor is not None:
                status, reason = "resolved_parent", "added_unit_not_in_amended_text"
            edge = base | {"target_document_id": target_doc,
                           "target": {"article": target[0], "clause": target[1], "point": target[2]},
                           "target_unit_id": unit["unit_id"] if unit else None,
                           "anchor_unit_id": anchor["unit_id"] if anchor else None, "status": status, "reason": reason}
            edges.append(edge)
            if kind in ("modify", "add") and instruction.rstrip().endswith(("như sau:", "như sau")):
                pending.append(edge)
    for edge in edges:
        edge["edge_id"] = digest(canonical([AMENDMENT_VERSION, edge["amending_text_sha256"], edge["instruction"]["start"], edge["kind"], edge["target"]]))[:24]
    return edges


def link_amending_units(edges, units, text):
    """Set `amending_unit_id` on edges whose instruction is a leaf unit of the corpus (scope v3 keeps amending articles
    as units of the amending document, or of a `<id>-sua-doi` entry): the unit text must hold the instruction and, when
    the edge has one, its whole quoted new wording, so the link is exact, never a guess."""
    parents = {u["parent_id"] for u in units}
    leaves = {}
    for unit in units:
        if unit["unit_id"] not in parents:
            leaves.setdefault(unit["document_id"], []).append(unit)
    for edge in edges:
        doc = edge["amending_document_id"]
        candidates = leaves.get(doc, []) + leaves.get(f"{doc}-sua-doi", [])
        wording = text[edge["new_text"]["start"]:edge["new_text"]["end"]] if edge.get("new_text") else ""
        found = [u for u in candidates if edge["instruction"]["text"] in u["text"] and wording in u["text"]]
        edge["amending_unit_id"] = found[0]["unit_id"] if len(found) == 1 else None
    return edges


def build(bundle, config_path, output, raw_dir="data/raw/vbpl"):
    """Edges of every amending snapshot listed in the config ({"sources": [{document_id, vbpl_id, snapshot_sha256}]})
    resolved against the units of a contract bundle; writes `edges.jsonl` and `manifest.json` to a new directory."""
    import json
    from datetime import datetime, timezone
    from pathlib import Path

    from legal_ai.common.io import read_jsonl, write_json, write_jsonl
    from legal_ai.ingestion.vbpl_api import document_text, metadata, unwrap
    from legal_ai.normalization.text import normalize

    output, bundle = Path(output), Path(bundle)
    if output.exists() and any(output.iterdir()):
        raise ValueError("output must be empty: use a new directory")
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    units_path = bundle / "units.jsonl"
    units = read_jsonl(units_path)
    edges, sources = [], []
    for source in config["sources"]:
        folder = Path(raw_dir) / source["vbpl_id"] / source["snapshot_sha256"]
        raw = (folder / "document.json").read_bytes()
        if digest(raw) != source["snapshot_sha256"]:
            raise ValueError(f"snapshot does not match its SHA-256: {source['document_id']}")
        document = unwrap(raw)
        meta = metadata(document)
        text = normalize(document_text(document)["text"])["text"]
        found = detect({"document_id": source["document_id"]}, text, units, meta["effective_from"])
        link_amending_units(found, units, text)
        edges += found
        sources.append({"document_id": source["document_id"], "vbpl_id": source["vbpl_id"], "snapshot_sha256": source["snapshot_sha256"],
                        "normalized_sha256": text_hash(text), "effective_from": meta["effective_from"], "effective_to": meta["effective_to"],
                        "effect_status": meta["effect_status"], "edges": len(found)})
    manifest = {"edge_version": AMENDMENT_VERSION, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "bundle": bundle.as_posix(), "units_sha256": digest(units_path.read_bytes()), "config_sha256": digest(Path(config_path).read_bytes()),
                "sources": sources, "summary": summary(edges), "network": False, "model_calls": 0,
                "limitations": ["Rules only: every edge needs human review against the source text before it is reported",
                                "Expiry by subject matter (expire_subject) stays unresolved: mapping it to units needs legal judgment",
                                "The effective date of an edge is the amending document's effective_from; dates inside an instruction are not read",
                                "Targets outside the corpus (other documents, annex forms) are kept as external or unresolved, never guessed",
                                "Effect dates and statuses are what vbpl.vn reported at access time"]}
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "edges.jsonl", edges)
    write_json(output / "manifest.json", manifest)
    return manifest


def summary(edges):
    by = {}
    for edge in edges:
        key = (edge["kind"], edge["status"])
        by[f"{key[0]}/{key[1]}"] = by.get(f"{key[0]}/{key[1]}", 0) + 1
    return {"edges": len(edges), "by_kind_status": dict(sorted(by.items())),
            "resolved": sum(e["status"] in ("resolved", "resolved_parent") for e in edges)}
