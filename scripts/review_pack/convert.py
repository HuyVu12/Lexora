"""Convert exported review files (`review-<task>-<name>.json` from the review page) to Lexora's own formats.

    gold       review-gold-*.json   -> lexora-gold-labels-v1 file (annotator huyvu), checked with GoldStore._clean on a TEMP COPY of a store
    csv        review-<task>-*.json -> the original check sheet CSV with the human columns filled (validity, link, amendment)
    audit      review-audit-*.json  -> JSON of {item_id, label, note}; `--store S --set ID --apply` also saves them through AuditStore

Usage (workspace root, standard library only):
    python scripts/review_pack/convert.py gold review-gold-vu.json --store data/kb/vm-lexora-20261124.sqlite --output labels-huyvu.json
    python scripts/review_pack/convert.py csv review-validity-vu.json --data experiments/review-pack-2026-11-24/data --output check-sheet-filled.csv
    python scripts/review_pack/convert.py audit review-audit-vu.json --output audit-huyvu.json

The CSV conversion takes the original row of every item from the `export` block of `<data>/<task>.json` and fills the human columns
from the review. How an option value maps to a column is `option["csv"]` ({column: text}) when the data file gives it, otherwise
the built-in defaults below. An item the reviewer did not finish keeps the (empty) human columns of its export.
"""

import argparse
import csv
from contextlib import closing
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.common.io import canonical, digest  # noqa: E402
from legal_ai.evaluation.rejection_audit import LABELS as AUDIT_LABELS  # noqa: E402
from legal_ai.kb.amendment_check import COLUMNS as AMENDMENT_COLUMNS, VERDICTS as AMENDMENT_VERDICTS  # noqa: E402
from legal_ai.research.audit import AuditStore  # noqa: E402
from legal_ai.research.corpus import CorpusStore  # noqa: E402
from legal_ai.research.gold import GoldStore, LABELS_FORMAT  # noqa: E402

ANNOTATOR, ANNOTATOR_NAME = "huyvu", "Huy Vũ"

VALIDITY_COLUMNS = ["question_id", "group", "as_of", "question", "role", "unit_id", "unit_path", "status_at_as_of", "reason", "quotes", "context",
                    "unit_text", "annotator_agrees", "annotator_note"]
LINK_COLUMNS = ["question_id", "question", "A_label", "A_text", "B_label", "B_text", "reference_answer", "needs_B (co/khong)", "gold_ok (co/khong)", "note"]
SHEETS = {
    "validity": {"columns": VALIDITY_COLUMNS, "value": ["annotator_agrees"], "note": "annotator_note",
                 "defaults": {"dong_y": {"annotator_agrees": "co"}, "khong_dong_y": {"annotator_agrees": "khong"}}},
    "link": {"columns": LINK_COLUMNS, "value": ["needs_B (co/khong)", "gold_ok (co/khong)"], "note": "note", "defaults": {}},
    "amendment": {"columns": list(AMENDMENT_COLUMNS), "value": ["verdict"], "note": "note", "defaults": {}, "allowed": {"verdict": AMENDMENT_VERDICTS}},
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _review(path_or_dict, task=None):
    review = path_or_dict if isinstance(path_or_dict, dict) else read_json(path_or_dict)
    if task and review.get("task") != task:
        raise ValueError(f"Tệp kết quả là của việc {review.get('task')!r}, không phải {task!r}")
    if not isinstance(review.get("items"), list):
        raise ValueError("Tệp kết quả thiếu danh sách items")
    return review


# Gold ---------------------------------------------------------------------------------------------
def _store_norm(norm):
    return {"modality": norm.get("modality"), "modality_cue": norm.get("modality_cue") or norm.get("cue") or None, "slots": norm.get("slots") or {}}


def gold_labels(review, store_path, set_id=None):
    """The labels file for the people who hold the store; every sentence is checked with `GoldStore._clean` on a temp copy of the store."""
    review = _review(review, "gold")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        copy = Path(temp) / "store.sqlite"
        shutil.copyfile(store_path, copy)
        golds = GoldStore(copy, CorpusStore(copy))
        sets = golds.sets()
        if set_id is None:
            if len(sets) != 1:
                raise ValueError("Store có nhiều bộ gold, hãy chỉ định --set: " + ", ".join(s["id"] for s in sets))
            set_id = sets[0]["id"]
        with closing(golds._connect()) as db:
            row, rows = golds._rows(db, set_id)
        units = golds._units(row["corpus_version_id"])
        items, problems = [], []
        for item in review["items"]:
            if item["id"] not in rows:
                problems.append(f"{item['id']}: không thuộc bộ gold {set_id}")
                continue
            if item.get("value") not in ("norms", "no_norm"):
                continue
            norms = [_store_norm(n) for n in (item.get("edited_norms") or [])]
            try:
                clean = golds._clean(rows[item["id"]], norms, units)
            except ValueError as error:
                problems.append(f"{item['id']}: {error}")
                continue
            items.append({"key": item["id"], "norms": clean, "updated_at": review.get("exported_at") or ""})
        if problems:
            raise ValueError("Không chuyển được:\n" + "\n".join(problems))
        if not items:
            raise ValueError("Tệp kết quả chưa có câu nào xong")
        items.sort(key=lambda i: i["key"])
        body = {"format": LABELS_FORMAT, "set_id": set_id, "corpus_version_id": row["corpus_version_id"], "annotator": ANNOTATOR,
                "annotator_name": ANNOTATOR_NAME, "labels": items, "exported_at": review.get("exported_at") or ""}
        return body | {"labels_sha256": digest(canonical(items))}


# CSV ----------------------------------------------------------------------------------------------
def csv_rows(task, review, data_dir):
    spec = SHEETS[task]
    review = _review(review, task)
    data = read_json(Path(data_dir) / f"{task}.json")
    options = {o["value"]: o for o in data["options"]}
    done = {r["id"]: r for r in review["items"]}
    unknown = sorted(set(done) - {i["id"] for i in data["items"]})
    if unknown:
        raise ValueError("Mã mục không có trong dữ liệu: " + ", ".join(unknown[:5]))
    rows = []
    for item in data["items"]:
        if "export" not in item:
            raise ValueError(f"Mục {item['id']} thiếu khối export")
        row = {c: str(item["export"].get(c, "")) for c in spec["columns"]}
        got = done.get(item["id"])
        if got is not None and got.get("value") is not None:
            value = got["value"]
            if value not in options:
                raise ValueError(f"{item['id']}: giá trị {value!r} không có trong options")
            mapping = options[value].get("csv") or spec["defaults"].get(value) or {spec["value"][-1]: value}
            for column, text in mapping.items():
                if column not in spec["columns"]:
                    raise ValueError(f"Cột {column!r} không có trong bảng {task}")
                row[column] = text
            for column, allowed in spec.get("allowed", {}).items():
                if row[column] and row[column] not in allowed:
                    raise ValueError(f"{item['id']}: {column} {row[column]!r} không thuộc {list(allowed)}")
            row[spec["note"]] = got.get("note") or ""
        elif got is not None and got.get("note"):
            row[spec["note"]] = got["note"]
        rows.append(row)
    return spec["columns"], rows


def write_csv(task, review, data_dir, output):
    columns, rows = csv_rows(task, review, data_dir)
    with Path(output).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


# Audit --------------------------------------------------------------------------------------------
def audit_labels(review):
    review = _review(review, "audit")
    labels = []
    for item in review["items"]:
        if item.get("value") is None:
            continue
        if item["value"] not in AUDIT_LABELS:
            raise ValueError(f"{item['id']}: nhãn {item['value']!r} không thuộc {list(AUDIT_LABELS)}")
        labels.append({"item_id": item["id"], "label": item["value"], "note": item.get("note") or ""})
    return {"annotator": ANNOTATOR, "annotator_name": ANNOTATOR_NAME, "labels": labels}


def save_audit(labels, store_path, set_id):
    """Save the labels through `AuditStore.save_label` into the store at `store_path` (pass a copy when testing)."""
    store = AuditStore(store_path)
    for item in labels["labels"]:
        store.save_label(set_id, item["item_id"], labels["annotator"], labels["annotator_name"], item["label"], item["note"])
    return len(labels["labels"])


def _write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    gold = sub.add_parser("gold")
    gold.add_argument("review")
    gold.add_argument("--store", required=True, help="store with the gold set; only a temp copy is opened")
    gold.add_argument("--set")
    gold.add_argument("--output", required=True)
    sheet = sub.add_parser("csv")
    sheet.add_argument("review")
    sheet.add_argument("--data", default=str(ROOT / "experiments" / "review-pack-2026-11-24" / "data"))
    sheet.add_argument("--output", required=True)
    audit = sub.add_parser("audit")
    audit.add_argument("review")
    audit.add_argument("--output", required=True)
    audit.add_argument("--store", help="audit store to save into (needs --set and --apply)")
    audit.add_argument("--set")
    audit.add_argument("--apply", action="store_true", help="really write the labels into --store")
    args = parser.parse_args(argv)
    if args.command == "gold":
        body = gold_labels(args.review, args.store, args.set)
        _write_json(args.output, body)
        print(f"{len(body['labels'])} nhãn -> {args.output}")
    elif args.command == "csv":
        task = _review(args.review)["task"]
        if task not in SHEETS:
            raise SystemExit(f"Việc {task!r} không có bảng CSV")
        print(f"{write_csv(task, args.review, args.data, args.output)} dòng -> {args.output}")
    else:
        labels = audit_labels(args.review)
        _write_json(args.output, labels)
        print(f"{len(labels['labels'])} nhãn -> {args.output}")
        if args.apply:
            if not (args.store and args.set):
                raise SystemExit("--apply cần --store và --set")
            print(f"đã lưu {save_audit(labels, args.store, args.set)} nhãn vào {args.store}")


if __name__ == "__main__":
    main()
