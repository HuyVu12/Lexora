"""Recall-by-token-budget report (research plan WP2): Markdown tables and one SVG line chart per question set, read
from the `metrics.json` of finished retrieval runs. Offline; numbers are copied, never recomputed.

Runs are given as `SET:CONDITION=RUN_DIR`; the set groups runs into one table and one figure.
"""

from html import escape
import json
from pathlib import Path

COLORS = ("#1f5fa8", "#c4572a", "#2f8a4f", "#7b4fa0", "#9a7b1c", "#3c8d99", "#a63d6b", "#5b5b5b")


def _num(value, digits=2):
    return "-" if value is None else f"{value:.{digits}f}".replace(".", ",")


def _int(value):
    return "-" if value is None else f"{value:,}".replace(",", ".")


def load_runs(pairs):
    sets = {}
    for pair in pairs:
        label, _, folder = pair.partition("=")
        if ":" not in label or not folder:
            raise ValueError(f"expected SET:CONDITION=RUN_DIR, got {pair}")
        name, condition = label.split(":", 1)
        metrics = json.loads((Path(folder) / "metrics.json").read_text(encoding="utf-8"))
        manifest = json.loads((Path(folder) / "manifest.json").read_text(encoding="utf-8"))
        sets.setdefault(name, []).append({"condition": condition, "folder": Path(folder).as_posix(), "metrics": metrics, "manifest": manifest})
    return sets


def svg(title, runs, width=640, height=360):
    """A line chart of mean recall against the token budget (log-spaced x positions by budget index)."""
    budgets = sorted({int(b) for r in runs for b in r["metrics"]["mean_recall_at_tokens"]})
    left, right, top, bottom = 56, 150, 36, 44
    plot_w, plot_h = width - left - right, height - top - bottom
    x = lambda i: left + (plot_w * i / max(1, len(budgets) - 1))
    y = lambda v: top + plot_h * (1 - v)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
             f'font-family="Segoe UI, Arial, sans-serif" font-size="12">',
             f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
             f'<text x="{left}" y="22" font-size="14" font-weight="600" fill="#222">{escape(title)}</text>']
    for tick in range(0, 11, 2):
        v = tick / 10
        parts.append(f'<line x1="{left}" x2="{left + plot_w}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#e3e3e3"/>')
        parts.append(f'<text x="{left - 8}" y="{y(v) + 4:.1f}" text-anchor="end" fill="#555">{_num(v, 1)}</text>')
    for i, budget in enumerate(budgets):
        parts.append(f'<text x="{x(i):.1f}" y="{top + plot_h + 18}" text-anchor="middle" fill="#555">{_int(budget)}</text>')
    parts.append(f'<text x="{left + plot_w / 2:.1f}" y="{height - 8}" text-anchor="middle" fill="#333">Ngân sách ngữ cảnh (token âm tiết)</text>')
    parts.append(f'<text x="14" y="{top + plot_h / 2:.1f}" transform="rotate(-90 14 {top + plot_h / 2:.1f})" text-anchor="middle" fill="#333">Recall trung bình</text>')
    for n, run in enumerate(runs):
        color = COLORS[n % len(COLORS)]
        values = run["metrics"]["mean_recall_at_tokens"]
        points = [(x(i), y(values[str(b)])) for i, b in enumerate(budgets) if values.get(str(b)) is not None]
        parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{" ".join(f"{px:.1f},{py:.1f}" for px, py in points)}"/>')
        parts += [f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3" fill="{color}"/>' for px, py in points]
        ly = top + 14 + 18 * n
        parts.append(f'<line x1="{left + plot_w + 16}" x2="{left + plot_w + 36}" y1="{ly}" y2="{ly}" stroke="{color}" stroke-width="2"/>')
        parts.append(f'<text x="{left + plot_w + 42}" y="{ly + 4}" fill="#222">{escape(run["condition"])}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def tables(name, runs):
    budgets = sorted({int(b) for r in runs for b in r["metrics"]["mean_recall_at_tokens"]})
    targets = sorted({t for r in runs for t in r["metrics"].get("tokens_to_reach", {})}, key=float)
    scored = {r["metrics"]["scored_questions"] for r in runs}
    lines = [f"Câu hỏi có nhãn: {', '.join(str(s) for s in sorted(scored))}.", "",
             "Recall trung bình theo ngân sách token:", "",
             "| Điều kiện | " + " | ".join(_int(b) for b in budgets) + " |", "|---|" + "---|" * len(budgets)]
    for run in runs:
        values = run["metrics"]["mean_recall_at_tokens"]
        lines.append(f"| {run['condition']} | " + " | ".join(_num(values.get(str(b))) for b in budgets) + " |")
    lines += ["", "Tỉ lệ câu tìm đủ mọi đơn vị đáp án theo ngân sách:", "",
              "| Điều kiện | " + " | ".join(_int(b) for b in budgets) + " |", "|---|" + "---|" * len(budgets)]
    for run in runs:
        values = run["metrics"].get("mean_complete_at_tokens", {})
        lines.append(f"| {run['condition']} | " + " | ".join(_num(values.get(str(b))) for b in budgets) + " |")
    if targets:
        lines += ["", "Ngân sách nhỏ nhất để recall trung bình đạt ngưỡng (token; `-` là không đạt trong độ sâu đã xếp hạng):", "",
                  "| Điều kiện | " + " | ".join(f"recall {_num(float(t), 1)}" for t in targets) + " | Token trung bình mỗi bản ghi |",
                  "|---|" + "---|" * (len(targets) + 1)]
        for run in runs:
            reach = run["metrics"].get("tokens_to_reach", {})
            lines.append(f"| {run['condition']} | " + " | ".join(_int(reach.get(t)) for t in targets)
                         + f" | {_num(run['metrics'].get('mean_record_tokens'), 1)} |")
    lines += ["", "Lượt chạy:", ""] + [f"- {r['condition']}: `{r['folder']}` (đóng gói {r['metrics'].get('context_packing', 'P0')})" for r in runs]
    return lines


def write_report(pairs, output, title):
    output = Path(output)
    sets = load_runs(pairs)
    lines = [f"# {title}", ""]
    for name, runs in sets.items():
        figure = output.with_name(f"{output.stem}-{name}.svg")
        figure.parent.mkdir(parents=True, exist_ok=True)
        figure.write_text(svg(name, runs), encoding="utf-8")
        lines += [f"## {name}", "", f"![{name}]({figure.name})", ""] + tables(name, runs) + [""]
    output.write_text("\n".join(lines), encoding="utf-8")
    return {"report": output.as_posix(), "sets": {name: [r["condition"] for r in runs] for name, runs in sets.items()}}
