"""Build the review pages of the 24/11/2026 pack from `data/*.json`.

Usage (workspace root):
    python scripts/review_pack/build.py [--data DIR] [--output DIR]

Writes `review.html` (with the model suggestions) and `review-blind.html` (suggestions removed from the embedded
data, not just hidden) as single self-contained files: data in a JSON script tag, no network, no external assets.
The format of the data files is in `experiments/review-pack-2026-11-24/README.md`.
"""

import argparse
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai.extraction.llm_norms import LLM_SLOTS, MODALITIES  # noqa: E402

PACK_ID = "review-pack-2026-11-24"
HERE = Path(__file__).resolve().parent
PACK_DIR = ROOT / "experiments" / PACK_ID
TASK_ORDER = ("gold", "validity", "link", "amendment", "audit")
SHORT = {"gold": "Gold quy phạm", "validity": "Hiệu lực", "link": "Liên kết", "amendment": "Sửa đổi", "audit": "Kiểm tra loại bỏ"}
SLOT_NAMES = {"actor": "Chủ thể", "action": "Hành vi", "object": "Đối tượng", "beneficiary": "Bên thụ hưởng", "recipient": "Bên nhận",
              "conditions": "Điều kiện", "exceptions": "Ngoại lệ", "deadlines": "Thời hạn", "quantities": "Định lượng", "outcome": "Kết quả"}


def load_tasks(data_dir):
    """{task: data} for every `<task>.json` in the directory, known tasks first in the fixed order."""
    found = {}
    for path in sorted(Path(data_dir).glob("*.json")):
        task = json.loads(path.read_text(encoding="utf-8"))
        name = task.get("task") or path.stem
        task["task"] = name
        task.setdefault("title", SHORT.get(name, name))
        task.setdefault("items", [])
        if name == "gold":
            task.setdefault("options", [])
        elif not task.get("options"):
            raise ValueError(f"{path.name}: thiếu danh sách options")
        ids = [i["id"] for i in task["items"]]
        if len(set(ids)) != len(ids):
            raise ValueError(f"{path.name}: có mã mục trùng nhau")
        found[name] = task
    if not found:
        raise ValueError(f"Không có tệp dữ liệu .json trong {data_dir}")
    return {k: found[k] for k in sorted(found, key=lambda t: (TASK_ORDER.index(t) if t in TASK_ORDER else len(TASK_ORDER), t))}


def strip_suggestions(tasks):
    """A deep copy without anything that reveals a suggestion: the model's choice, reason, quotes, confidence, the gold
    draft and the `export` blocks (which hold the original sheet columns, some of them machine verdicts)."""
    blind = copy.deepcopy(tasks)
    for task in blind.values():
        task.pop("drafted_by", None)
        for item in task["items"]:
            for key in ("suggestion", "reason", "confidence", "export"):
                item.pop(key, None)
            if "draft" in item:
                item["draft"] = []
    return blind


def embed(value):
    """JSON for a `<script type=application/json>` tag: no `</script`, `<!--` or line separators can end or confuse it."""
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    for raw, esc in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"), (" ", "\\u2028"), (" ", "\\u2029")):
        text = text.replace(raw, esc)
    return text


def page(tasks, mode):
    template = (HERE / "page.html").read_text(encoding="utf-8")
    shown = tasks if mode == "suggestions" else strip_suggestions(tasks)
    for task in shown.values():
        task.pop("export_columns", None)
        for item in task["items"]:
            item.pop("export", None)
        task["short"] = SHORT.get(task["task"], task["title"])
    pack = {"pack": PACK_ID, "mode": mode, "order": list(shown), "tasks": shown, "modalities": list(MODALITIES),
            "slots": list(LLM_SLOTS), "slot_names": SLOT_NAMES}
    if "__PACK_DATA__" not in template:
        raise ValueError("page.html thiếu chỗ chèn dữ liệu")
    return template.replace("__PACK_DATA__", embed(pack))


def build(data_dir=None, output_dir=None):
    data_dir = Path(data_dir or PACK_DIR / "data")
    output_dir = Path(output_dir or PACK_DIR)
    tasks = load_tasks(data_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, mode in (("review.html", "suggestions"), ("review-blind.html", "blind")):
        path = output_dir / name
        path.write_text(page(copy.deepcopy(tasks), mode), encoding="utf-8")
        written.append(path)
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--data", default=str(PACK_DIR / "data"))
    parser.add_argument("--output", default=str(PACK_DIR))
    args = parser.parse_args(argv)
    for path in build(args.data, args.output):
        print(path)


if __name__ == "__main__":
    main()
