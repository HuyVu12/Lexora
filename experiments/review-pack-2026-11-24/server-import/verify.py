"""Check, read-only, that the validity set and the link set (24/11/2026 import) were imported correctly into a workspace store.

Opens the store (and the backup taken before the import) with read-only SQLite connections; never writes.
Fails loudly (exit 1) unless:
- corpus version `v48feefc6d53b` is present with bundle hash 84932db6...ef8b, recomputed here from the stored rows;
- for each of `validity`, `link` exactly one question set on that version with the expected name holds exactly the questions of
  `<set>-drafts.json` (30 / 35), in order, each with a model proposal equal to the draft's fields and only units of
  the version; paraphrase families are as in the drafts (`paraphrase_of`);
- every row the backup had in the corpus and question tables is still there unchanged (so the existing lookup set,
  its labels and proposals, and corpus v1 are untouched), and the only new rows belong to the new version and sets.

Usage: python verify.py --store <store after import> --backup <backup taken before the import>
"""

import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "src"))
from legal_ai.common.io import canonical, digest  # noqa: E402
from legal_ai.research.corpus import CorpusStore  # noqa: E402

VERSION_ID = "v48feefc6d53b"
BUNDLE_SHA256 = "84932db6a555c7a11fdd9a2c47c40845f84a9dd5316609dbb04fe9b26e70ef8b"
SETS = {"validity": (30, "Bộ hiệu lực v1 (corpus v3, nháp model 16/11)"), "link": (35, "Bộ cần liên kết v1 (corpus v3, nháp model 23/11)")}
TABLES = ("corpora", "corpus_documents", "corpus_versions", "question_sets", "questions", "question_proposals", "question_labels",
          "question_annotators", "question_adjudications", "question_calls", "question_drafts")


def read_only(path):
    db = sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def rows(db, table):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone():
        return []
    return [tuple(r) for r in db.execute(f"SELECT * FROM {table}")]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", required=True)
    parser.add_argument("--backup", required=True)
    args = parser.parse_args()
    errors, report = [], {"store": args.store}

    with closing(read_only(args.store)) as db, closing(read_only(args.backup)) as old:
        version = db.execute("SELECT * FROM corpus_versions WHERE id = ?", (VERSION_ID,)).fetchone()
        if version is None:
            errors.append(f"corpus version {VERSION_ID} is missing")
            units = set()
        else:
            ids = json.loads(version["document_rows"])
            docs = {r["id"]: r for r in db.execute(f"SELECT * FROM corpus_documents WHERE id IN ({','.join('?' * len(ids))})", ids)}
            documents, all_units = [], []
            for row_id in ids:
                document, doc_units, _ = CorpusStore._contract(docs[row_id])
                documents.append(document)
                all_units.extend(doc_units)
            computed = digest(canonical({"documents": documents, "units": all_units}))
            stored = json.loads(version["manifest"])["bundle_sha256"]
            if not computed == stored == BUNDLE_SHA256:
                errors.append(f"bundle hash: stored {stored}, recomputed {computed}, expected {BUNDLE_SHA256}")
            units = {u["unit_id"] for u in all_units}
            report["version"] = {"id": VERSION_ID, "bundle_sha256": computed, "documents": len(documents), "units": len(all_units)}

        sets = {r["id"]: r for r in db.execute("SELECT * FROM question_sets WHERE corpus_version_id = ?", (VERSION_ID,))}
        new_sets, report["sets"] = set(), {}
        for name, (expected, set_name) in SETS.items():
            drafts = json.loads((HERE / f"{name}-drafts.json").read_text(encoding="utf-8"))
            texts = [d["text"] for d in drafts]
            matches = []
            for set_id in sets:
                questions = db.execute("SELECT * FROM questions WHERE set_id = ? AND removed_at IS NULL ORDER BY position", (set_id,)).fetchall()
                if [q["text"] for q in questions] == texts:
                    matches.append((set_id, questions))
            if len(matches) != 1:
                errors.append(f"{name}: {len(matches)} sets on {VERSION_ID} hold exactly the drafted questions (expected 1)")
                continue
            set_id, questions = matches[0]
            if sets[set_id]["name"] != set_name:
                errors.append(f"{name}: set name {sets[set_id]['name']!r}, expected {set_name!r}")
            if not sets[set_id]["guideline"].strip():
                errors.append(f"{name}: empty guideline")
            new_sets.add(set_id)
            if len(questions) != expected:
                errors.append(f"{name}: {len(questions)} questions, expected {expected}")
            family_of = []
            for n, (q, d) in enumerate(zip(questions, drafts)):
                proposal = db.execute("SELECT * FROM question_proposals WHERE set_id = ? AND question_id = ? ORDER BY created_at DESC, rowid DESC LIMIT 1",
                                      (set_id, q["id"])).fetchone()
                if proposal is None:
                    errors.append(f"{name}/{d['source_question_id']}: no proposal")
                    continue
                fields = json.loads(proposal["fields"])
                if fields != {k: d[k] for k in ("question_type", "expected_status", "relevant_unit_ids")}:
                    errors.append(f"{name}/{d['source_question_id']}: proposal differs from the draft")
                if set(fields["relevant_unit_ids"]) - units:
                    errors.append(f"{name}/{d['source_question_id']}: proposal units outside the version")
                if not proposal["rationale"]:
                    errors.append(f"{name}/{d['source_question_id']}: empty rationale")
                origin = json.loads(q["origin_detail"])
                if q["origin"] != "model" or origin.get("draft_index") != n:
                    errors.append(f"{name}/{d['source_question_id']}: origin {q['origin']} {origin}")
                source = d["paraphrase_of"]
                family_of.append(family_of[source] if source is not None else q["family_id"])
                if q["family_id"] != family_of[-1]:
                    errors.append(f"{name}/{d['source_question_id']}: family {q['family_id']} differs from item {source}")
            groups = {}
            for d, q in zip(drafts, questions):
                groups.setdefault(q["family_id"], []).append(d["source_question_id"])
            if len(groups) != len({f for f in family_of}):
                errors.append(f"{name}: families merged across paraphrase groups")
            labels = db.execute("SELECT COUNT(*) FROM question_labels WHERE set_id = ?", (set_id,)).fetchone()[0]
            report["sets"][name] = {"set_id": set_id, "name": sets[set_id]["name"], "questions": len(questions), "families": len(groups),
                                    "paraphrase_families": {f: m for f, m in groups.items() if len(m) > 1}, "proposals": len(questions),
                                    "labels": labels}
            if labels:
                errors.append(f"{name}: {labels} labels exist, expected none right after the import")

        changed, added = {}, {}
        for table in TABLES:
            before, after = set(rows(old, table)), set(rows(db, table))
            if before - after:
                changed[table] = len(before - after)
            added[table] = len(after - before)
        if changed:
            errors.append(f"rows of the backup changed or removed: {changed}")
        expected_new_sets = len(new_sets)
        if added.get("question_sets", 0) != expected_new_sets or added.get("corpus_versions", 0) != 0:
            errors.append(f"unexpected new rows: {added}")
        report["new_rows"] = added
        lookup = old.execute("SELECT id, name FROM question_sets").fetchall()
        report["existing_sets_untouched"] = [
            {"set_id": r["id"], "name": r["name"], "questions": db.execute("SELECT COUNT(*) FROM questions WHERE set_id = ? AND removed_at IS NULL", (r["id"],)).fetchone()[0],
             "labels": db.execute("SELECT COUNT(*) FROM question_labels WHERE set_id = ?", (r["id"],)).fetchone()[0]} for r in lookup]

    print(json.dumps(report, ensure_ascii=False, indent=1))
    if errors:
        print(f"FAILED: {len(errors)} problem(s)")
        for line in errors:
            print("  " + line)
        sys.exit(1)
    print("OK: the validity and link sets are in the store with proposals; existing data (incl. labels) unchanged")


if __name__ == "__main__":
    main()
