"""Candidate pairs for the validity question set v1, built deterministically from the frozen corpus v3 and its edges.

Two files, both re-creatable at any time (no network, no model):

- `pairs-expired.jsonl`: provisions of NĐ 12/2022/NĐ-CP (expired on 2026-09-10 per vbpl.vn) and NĐ 283/2026/NĐ-CP
  (in force from 2026-09-10) that describe the same thing. Articles of the sanction chapters (II-IV) are matched by
  heading (difflib ratio of the heading text without "Điều N.", best match, at least 0.8), then every leaf clause or
  point of the old article is matched to the most similar leaf of the new article (ratio at least 0.85). A pair is
  a candidate only: the question drafts quote the shared wording of both units, and the validator checks the quotes.
- `pairs-amended.jsonl`: one row per resolved `modify` or `replace_phrase` edge of `amendment-rules-v1` whose new
  wording is a corpus unit (`amending_unit_id`): the amended unit, the amending unit, the edge date and both
  documents' dates as vbpl.vn reported them. Rows on the foreign-worker part of NĐ 152/2020 (chapters I and II) carry
  a caveat: NĐ 219/2025 says that part stopped applying when it took effect, which the unit-status model does not see.

Usage: python pairs.py  (from the repository root or this folder)
"""

import difflib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BUNDLE = ROOT / "data/normalized/experiment-scope-v3-v48feefc6d53b"
EDGES = ROOT / "data/kb/amendments-scope-v3-v48feefc6d53b/edges.jsonl"
OLD, NEW = "12-2022-nd-cp", "283-2026-nd-cp"
SANCTION_CHAPTERS = re.compile(r"/chapter-(ii|iii|iv)/")
HEADING = re.compile(r"^Điều\s+\d+[a-zđ]?\.\s*")
# NĐ 219/2025, khoản 2 Điều 35 (verbatim in the corpus): the foreign-worker content of NĐ 152/2020 as amended by
# NĐ 70/2023 stops applying from 2025-08-07, while vbpl.vn reports NĐ 152/2020 in force until 2026-11-15.
FOREIGN_WORKER_EXPIRY = ("219-2025-nd-cp/chapter-v/article-35/clause-2",
                         "Nội dung về lao động nước ngoài làm việc tại Việt Nam quy định tại Nghị định số 152/2020/NĐ-CP")


def load(path):
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def ratio(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def expired_pairs(units, documents):
    parents = {u["parent_id"] for u in units}
    articles = {doc: [u for u in units if u["document_id"] == doc and u["unit_type"] == "article" and SANCTION_CHAPTERS.search(u["unit_id"])]
                for doc in (OLD, NEW)}
    leaves = {}
    for unit in units:
        if unit["document_id"] in (OLD, NEW) and unit["unit_id"] not in parents and unit["unit_type"] in ("clause", "point"):
            article = unit["unit_id"].split("/clause-")[0]
            leaves.setdefault(article, []).append(unit)
    heading = lambda u: HEADING.sub("", u["text"].strip().splitlines()[0])
    out = []
    for old in articles[OLD]:
        scored = [(ratio(heading(old), heading(new)), new) for new in articles[NEW]]
        best_score, new = max(scored, key=lambda pair: (pair[0], pair[1]["unit_id"]))
        if best_score < 0.8:
            continue
        for leaf in leaves.get(old["unit_id"], []):
            candidates = [(ratio(leaf["text"], other["text"]), other) for other in leaves.get(new["unit_id"], [])]
            if not candidates:
                continue
            score, match = max(candidates, key=lambda pair: (pair[0], pair[1]["unit_id"]))
            if score < 0.85:
                continue
            out.append({"old_unit_id": leaf["unit_id"], "new_unit_id": match["unit_id"], "text_ratio": round(score, 4),
                        "old_article": heading(old), "new_article": heading(new), "heading_ratio": round(best_score, 4),
                        "old_effective_to": documents[OLD]["effective_to"], "new_effective_from": documents[NEW]["effective_from"],
                        "old_text": leaf["text"].strip(), "new_text": match["text"].strip()})
    return out


def amended_pairs(units_by_id, documents, edges):
    expiry_unit, expiry_quote = FOREIGN_WORKER_EXPIRY
    expiry_holds = expiry_unit in units_by_id and expiry_quote in units_by_id[expiry_unit]["text"]
    out = []
    for edge in edges:
        if edge["status"] != "resolved" or edge["kind"] not in ("modify", "replace_phrase") or edge.get("amending_unit_id") not in units_by_id:
            continue
        old, new = units_by_id[edge["target_unit_id"]], units_by_id[edge["amending_unit_id"]]
        row = {"old_unit_id": old["unit_id"], "amending_unit_id": new["unit_id"], "kind": edge["kind"], "edge_id": edge["edge_id"],
               "edge_effective_from": edge["effective_from"], "instruction": edge["instruction"]["text"],
               "old_document": {k: documents[old["document_id"]][k] for k in ("document_id", "effective_from", "effective_to")},
               "amending_document": {k: documents[new["document_id"]][k] for k in ("document_id", "effective_from", "effective_to")},
               "old_text": old["text"].strip(), "amending_text": new["text"].strip()}
        if expiry_holds and re.match(r"152-2020-nd-cp/chapter-(i|ii)/", old["unit_id"]):
            row["caveat"] = (f"{expiry_unit}: \"{expiry_quote} ... hết hiệu lực thi hành kể từ ngày Nghị định này có hiệu lực\" "
                             f"(NĐ 219/2025 hiệu lực từ {documents['219-2025-nd-cp']['effective_from']}); unit status does not model it, "
                             f"so questions use an as_of between {edge['effective_from']} and the day before")
        out.append(row)
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    units = load(BUNDLE / "units.jsonl")
    documents = {d["document_id"]: d for d in load(BUNDLE / "documents.jsonl")}
    expired = expired_pairs(units, documents)
    amended = amended_pairs({u["unit_id"]: u for u in units}, documents, load(EDGES))
    for name, rows in (("pairs-expired.jsonl", expired), ("pairs-amended.jsonl", amended)):
        with (HERE / name).open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"pairs_expired": len(expired), "pairs_expired_identical_text": sum(r["text_ratio"] == 1.0 for r in expired),
                      "pairs_amended": len(amended), "pairs_amended_with_caveat": sum("caveat" in r for r in amended)}, indent=1))


if __name__ == "__main__":
    main()
