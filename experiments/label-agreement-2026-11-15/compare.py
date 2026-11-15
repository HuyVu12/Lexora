"""Agreement between one annotator and the stored model proposals of a question set (offline, read-only).

Usage (from the workspace root):
    python experiments/label-agreement-2026-11-15/compare.py <store.sqlite> <set_id> <annotator> <output.json>

The model side is the latest `question_proposals` row of every question. Metrics use the app's own `kappa` and
`dice` (`legal_ai.research.questions`), so they match the in-app comparison page. Questions whose note reports the
label-form bug (parent Clause not offered, fixed 15/11/2026) are also scored separately.
"""

from collections import Counter
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from legal_ai.research.questions import FIELDS, dice, kappa  # noqa: E402

BUG_MARK = "BUG"


def article(unit_id):
    return unit_id.split("/clause-")[0]


def agreement(pairs):
    a, b = [p[0] for p in pairs], [p[1] for p in pairs]
    out = {"questions": len(pairs)}
    for field in ("question_type", "expected_status"):
        x, y = [i[field] for i in a], [i[field] for i in b]
        out[field] = {"kappa": round(kappa(x, y), 3), "raw": round(sum(u == v for u, v in zip(x, y)) / len(x), 3),
                      "confusion_annotator_to_model": {f"{u} -> {v}": n for (u, v), n in Counter((u, v) for u, v in zip(x, y) if u != v).items()}}
    dices = [dice(i["relevant_unit_ids"], j["relevant_unit_ids"]) for i, j in zip(a, b)]
    out["unit_dice_mean"] = round(sum(dices) / len(dices), 3)
    out["unit_exact"] = round(sum(d == 1 for d in dices) / len(dices), 3)
    answered = [(i, j) for i, j in zip(a, b) if i["expected_status"] == j["expected_status"] == "answer"]
    out["both_answer"] = len(answered)
    out["article_exact_both_answer"] = round(sum({article(u) for u in i["relevant_unit_ids"]} == {article(u) for u in j["relevant_unit_ids"]}
                                                 for i, j in answered) / len(answered), 3)
    out["full_agreement"] = round(sum(same(i, j) for i, j in zip(a, b)) / len(pairs), 3)
    return out


def same(a, b):
    return all(sorted(a[f]) == sorted(b[f]) if f == "relevant_unit_ids" else a[f] == b[f] for f in FIELDS)


def main(store, set_id, annotator, output):
    db = sqlite3.connect(f"file:{store}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    questions = db.execute("SELECT * FROM questions WHERE set_id = ? AND removed_at IS NULL ORDER BY position", (set_id,)).fetchall()
    labels = {r["question_id"]: r for r in db.execute("SELECT * FROM question_labels WHERE set_id = ? AND annotator = ?", (set_id, annotator))}
    proposals = {}
    for r in db.execute("SELECT * FROM question_proposals WHERE set_id = ? ORDER BY created_at", (set_id,)):
        proposals[r["question_id"]] = r
    pairs, bug, rows = [], set(), []
    for q in questions:
        if q["id"] not in labels or q["id"] not in proposals:
            continue
        mine, model = json.loads(labels[q["id"]]["fields"]), json.loads(proposals[q["id"]]["fields"])
        pairs.append((mine, model))
        note = labels[q["id"]]["note"]
        if BUG_MARK in note:
            bug.add(len(pairs) - 1)
        if not same(mine, model):
            rows.append({"position": q["position"], "question": q["text"], "annotator": mine, "model": model,
                         "model_rationale": proposals[q["id"]]["rationale"], "note": note, "label_form_bug": BUG_MARK in note})
    shown = Counter(json.loads(labels[q]["provenance"])["proposals_shown"] for q in labels)
    models = Counter(json.loads(p["call"]).get("model") for p in proposals.values())
    report = {"store": Path(store).name, "set_id": set_id, "annotator": annotator, "annotator_proposals_shown": dict(shown),
              "model": dict(models), "all": agreement(pairs),
              "without_label_form_bug": agreement([p for n, p in enumerate(pairs) if n not in bug]),
              "label_form_bug_questions": len(bug), "disagreements": rows}
    Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "disagreements"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:5])
