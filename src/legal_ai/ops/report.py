"""The results report for the supervisor (`results-report-v1`), built from the experiment folders and the store.

`report_data` gathers the numbers (extraction-model comparison, why claims were rejected, planted errors, the
progress of gold sets, question sets, answer runs and rejection audits) and the team's own notes, which a `dev`
account edits in the app. `render_html` turns that into one self-contained HTML page to send by e-mail; the app
shows the same data on its Report tab.
"""

import csv
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path

REPORT_VERSION = "results-report-v1"
NOTE_KEYS = ("limitations", "next_steps", "questions")
DEFAULT_NOTES = {
    "limitations": [
        "Bị loại không đồng nghĩa với sai; độ chính xác của bộ kiểm chứng chỉ có khi hai người gán nhãn xong bảng kiểm tra.",
        "Bộ kiểm chứng v3 được chỉnh sau khi xem đầu ra của Opus trên cùng phạm vi, trước mọi phép đo; việc này có trong nhật ký quyết định.",
        "Tỉ lệ loại nhầm 0% ở phần chèn lỗi không phải bằng chứng, vì bản ghi sạch lấy từ chính ĐK4.",
        "Mỗi model chạy một lần; phiên bản model qua 9Router không ghim được. Thời gian gọi phản ánh tải của 9Router.",
        "Với Opus, ĐK3 trùng ĐK4, nên nếu dùng Opus cho RQ3 thì hai điều kiện này không khác nhau.",
    ],
    "next_steps": [
        "Hai người gán nhãn bảng kiểm tra quy phạm bị loại, tính kappa và tỉ lệ sai trong nhóm bị loại và nhóm được giữ.",
        "Gán nhãn gold set trích xuất (RQ1) trên trang Gold.",
        "Hoàn thành bộ câu hỏi có nhãn, chạy ĐK1-ĐK4 và chấm mù (RQ3); khóa MVP ngày 27/11.",
    ],
    "questions": [
        "Chọn model cho ĐK3/ĐK4 ở RQ3: nhóm đề xuất gemma4, giữ Opus làm đối chứng.",
        "Có nên cho phép trích dẫn từ câu dẫn của khoản cha (bộ kiểm chứng v4) trước khi đo RQ3?",
        "Quy mô gold set và bộ câu hỏi như vậy đã đủ cho phạm vi đồ án chưa?",
    ],
}
NOTE_TITLES = {"limitations": "Giới hạn đã biết", "next_steps": "Việc tiếp theo", "questions": "Xin ý kiến"}
CATEGORIES = (("context", "Lấy chữ từ câu dẫn hoặc tên Điều"), ("not_found", "Có giá trị không tìm thấy trong luật"),
              ("modality_only", "Chỉ sai nghĩa từ tình thái"), ("other", "Khác"))


def clean_notes(notes):
    """Validated notes: each key a list of at most 12 non-empty lines of at most 400 characters."""
    if not isinstance(notes, dict) or set(notes) - set(NOTE_KEYS):
        raise ValueError("Ghi chú chỉ gồm limitations, next_steps, questions")
    result = {}
    for key in NOTE_KEYS:
        lines = notes.get(key, [])
        if not isinstance(lines, list) or len(lines) > 12 or not all(isinstance(line, str) and len(line) <= 400 for line in lines):
            raise ValueError("Mỗi mục ghi chú tối đa 12 dòng, mỗi dòng tối đa 400 ký tự")
        result[key] = [line.strip() for line in lines if line.strip()]
    return result


def experiment_runs(folder):
    """[{name, kind, created_at}] for every run directory with a manifest; kind is kb, retrieval, answer, injection or other."""
    folder = Path(folder)
    runs = []
    for manifest_path in sorted(folder.glob("*/manifest.json")) if folder.exists() else []:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if "retrieval_run" in manifest:
            kind = "answer"
        elif "kb_version" in manifest or manifest.get("run_version", "").startswith("llm-kb"):
            kind = "kb"
        elif "condition" in manifest and "retrieval" in manifest:
            kind = "retrieval"
        else:
            kind = "other"
        runs.append({"name": manifest_path.parent.name, "kind": kind, "created_at": manifest.get("created_at")})
    for report_path in sorted(folder.glob("*/report.json")) if folder.exists() else []:
        if not (report_path.parent / "manifest.json").exists():
            try:
                if json.loads(report_path.read_text(encoding="utf-8")).get("injection_version"):
                    runs.append({"name": report_path.parent.name, "kind": "injection", "created_at": None})
            except ValueError:
                continue
    return runs


def audits(folder):
    """Progress of rejection-audit sheets: items and labelled rows of every CSV next to an audit key."""
    found = []
    for key_path in sorted(Path(folder).glob("*/key.json")) if Path(folder).exists() else []:
        try:
            key = json.loads(key_path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if not key.get("audit_version"):
            continue
        sheets = []
        for sheet in sorted(key_path.parent.glob("*.csv")):
            with sheet.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            sheets.append({"file": sheet.name, "items": len(rows), "labelled": sum(1 for r in rows if (r.get("label") or "").strip())})
        found.append({"name": key_path.parent.name, "items": len(key.get("items", {})), "sheets": sheets})
    return found


def report_data(kb_summaries, *, golds, question_sets, runs, audit_progress, notes):
    full = [s for s in kb_summaries if not (s.get("batches_planned") and s["batches_attempted"] < s["batches_planned"])]
    sampled = [s["model"] for s in kb_summaries if s not in full]
    rows = []
    for s in sorted(full, key=lambda s: -(s.get("rejected_rate") or 0)):
        inj = s.get("injection") or {}
        rows.append({"model": s["model"], "provider": s["provider"], "batches_ok": s["batches_ok"], "batches_planned": s.get("batches_planned"),
                     "sentence_answer_rate": s.get("sentence_answer_rate"), "dk3": s["dk3_claims"], "dk4": s["dk4_claims"],
                     "rejected": s["rejected"], "rejected_rate": s.get("rejected_rate"), "detectable_rate": inj.get("detectable_rate"),
                     "semantic_rate": inj.get("semantic_rate"), "call_error_rate": s.get("call_error_rate"),
                     "explained": (s.get("rejection_explained") or {}).get("categories", {})})
    labelled_gold = sum(1 for g in golds if g.get("labelled"))
    status = [
        {"rq": "RQ1", "title": "Chất lượng trích xuất", "facts": f"{len(golds)} bộ gold, {labelled_gold} bộ đã có nhãn, {sum(1 for g in golds if g.get('adjudicated'))} bộ đã đối soát",
         "state": "done" if any(g.get("adjudicated") for g in golds) else ("partial" if labelled_gold else "todo")},
        {"rq": "RQ2", "title": "Hiệu quả kiểm chứng", "facts": f"{sum(1 for r in rows if r['detectable_rate'] is not None)} model có số liệu chèn lỗi; "
         + (", ".join(f"bảng {a['name']}: {max((s['labelled'] for s in a['sheets']), default=0)}/{a['items']} dòng đã gán" for a in audit_progress) or "chưa có bảng kiểm tra"),
         "state": "done" if audit_progress and all(any(s["labelled"] == a["items"] for s in a["sheets"]) for a in audit_progress) else ("partial" if rows else "todo")},
        {"rq": "RQ3", "title": "Chất lượng câu trả lời ĐK1-ĐK4", "facts": f"{sum(1 for q in question_sets if q.get('frozen'))} bộ câu hỏi đã chốt, "
         f"{sum(1 for r in runs if r['kind'] == 'retrieval')} lượt truy xuất, {sum(1 for r in runs if r['kind'] == 'answer')} lượt sinh câu trả lời",
         "state": "partial" if any(r["kind"] == "answer" for r in runs) else "todo"},
    ]
    return {"report_version": REPORT_VERSION, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": status, "extraction": rows, "sampled_models": sampled, "audits": audit_progress,
            "notes": notes or DEFAULT_NOTES}


def _pct(value):
    return "-" if value is None else f"{value * 100:.1f}%".replace(".", ",")


STATE_LABELS = {"done": ("Có số liệu", "good"), "partial": ("Một phần", "warn"), "todo": ("Chưa có", "todo")}
STYLE = """
:root { --paper:#f6f7f9; --sheet:#fff; --ink:#1c2330; --muted:#5d6676; --line:#dde1e8; --accent:#2c5a85;
  --ctx:#6f9bc4; --nf:#c0573e; --mod:#d9a43a; --oth:#7a8291; --good:#2f7d4f; --warn:#a8701a; --todo:#7a8291; }
* { box-sizing: border-box; }
body { margin:0; background:var(--paper); color:var(--ink); font:400 15px/1.6 "Be Vietnam Pro","Segoe UI",system-ui,sans-serif; }
main { max-width:900px; margin:0 auto; padding:36px 20px 56px; display:grid; gap:24px; }
header { border-bottom:2px solid var(--ink); padding-bottom:16px; display:grid; gap:6px; }
h1, h2 { font-family:"Source Serif 4",Georgia,serif; font-weight:600; margin:0; text-wrap:balance; }
h1 { font-size:28px; line-height:1.2; } h2 { font-size:19px; }
section { background:var(--sheet); border:1px solid var(--line); border-radius:8px; padding:20px 22px; display:grid; gap:12px; }
p { margin:0; } ul { margin:0; padding-left:20px; display:grid; gap:5px; }
.small { font-size:13px; color:var(--muted); }
.wrap { overflow-x:auto; }
table { border-collapse:collapse; width:100%; font-size:14px; font-variant-numeric:tabular-nums; }
th, td { text-align:left; padding:7px 10px; border-bottom:1px solid var(--line); vertical-align:top; }
th { font-size:12px; color:var(--muted); font-weight:600; text-transform:uppercase; letter-spacing:.03em; }
.n { text-align:right; white-space:nowrap; }
.pill { display:inline-block; font-size:12px; font-weight:600; padding:1px 9px; border-radius:999px; border:1px solid currentColor; white-space:nowrap; }
.good { color:var(--good); } .warn { color:var(--warn); } .todo { color:var(--todo); }
.bar { display:flex; height:16px; min-width:2px; }
.bar span { display:block; height:100%; }
.c-context { background:var(--ctx); } .c-not_found { background:var(--nf); } .c-modality_only { background:var(--mod); } .c-other { background:var(--oth); }
.legend { display:flex; flex-wrap:wrap; gap:4px 16px; font-size:13px; color:var(--muted); }
.legend i { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:6px; }
.chart td { border:0; padding:4px 8px; }
.cols { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:18px; }
@media (max-width:700px) { .cols { grid-template-columns:1fr; } }
"""


def render_html(data):
    e = lambda value: escape(str(value))
    status_rows = "".join(f"<tr><td><strong>{e(s['rq'])}</strong> {e(s['title'])}</td><td><span class=\"pill {STATE_LABELS[s['state']][1]}\">"
                          f"{STATE_LABELS[s['state']][0]}</span></td><td>{e(s['facts'])}</td></tr>" for s in data["status"])
    model_rows = "".join(f"<tr><td>{e(r['model'])}</td><td class=\"n\">{r['batches_ok']}/{r['batches_planned'] or '-'}</td><td class=\"n\">{_pct(r['sentence_answer_rate'])}</td>"
                         f"<td class=\"n\">{r['dk3']}</td><td class=\"n\">{r['dk4']}</td><td class=\"n\">{_pct(r['rejected_rate'])}</td>"
                         f"<td class=\"n\">{_pct(r['detectable_rate'])}</td><td class=\"n\">{_pct(r['call_error_rate'])}</td></tr>" for r in data["extraction"])
    top = max([r["rejected_rate"] or 0 for r in data["extraction"]] + [0.01])
    chart_rows = ""
    for r in data["extraction"]:
        parts = "".join(f"<span class=\"c-{key}\" style=\"flex:{r['explained'].get(key, 0)}\" title=\"{e(label)}: {r['explained'].get(key, 0)}\"></span>"
                        for key, label in CATEGORIES if r["explained"].get(key))
        width = (r["rejected_rate"] or 0) / top * 100
        chart_rows += (f"<tr><td>{e(r['model'])}</td><td style=\"width:60%\"><div class=\"bar\" style=\"width:{width:.1f}%\">{parts}</div></td>"
                       f"<td class=\"n\">{_pct(r['rejected_rate'])}</td></tr>")
    legend = "".join(f"<span><i class=\"c-{key}\"></i>{e(label)}</span>" for key, label in CATEGORIES)
    notes = "".join(f"<div><h2>{e(NOTE_TITLES[key])}</h2><ul>{''.join(f'<li>{e(line)}</li>' for line in data['notes'].get(key, []))}</ul></div>" for key in NOTE_KEYS)
    sampled = f" Chỉ chạy mẫu, không đưa vào bảng: {e(', '.join(data['sampled_models']))}." if data["sampled_models"] else ""
    generated = datetime.fromisoformat(data["generated_at"]).astimezone().strftime("%d/%m/%Y %H:%M")
    return f"""<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lexora: báo cáo kết quả {generated[:10]}</title>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;600&family=Source+Serif+4:opsz,wght@8..60,600&display=swap" rel="stylesheet">
<style>{STYLE}</style></head><body><main>
<header><h1>Lexora: báo cáo kết quả thực nghiệm</h1>
<p>RAG trên kho tri thức pháp luật lao động có bằng chứng nguyên văn; so sánh bốn điều kiện ĐK1-ĐK4.</p>
<p class="small">Sinh tự động từ ứng dụng lúc {generated}; số liệu lấy trực tiếp từ các lượt chạy.</p></header>
<section><h2>Trạng thái theo câu hỏi nghiên cứu</h2><div class="wrap"><table><thead><tr><th>Câu hỏi</th><th>Số liệu</th><th>Hiện có</th></tr></thead>
<tbody>{status_rows}</tbody></table></div></section>
<section><h2>So sánh model trích xuất (ĐK3 trước, ĐK4 sau kiểm chứng)</h2>
<p>Cùng phạm vi, cùng prompt, nhiệt độ 0, cùng bộ kiểm chứng; mỗi model một lượt.</p>
<div class="wrap"><table><thead><tr><th>Model</th><th class="n">Lô OK</th><th class="n">Câu có trả lời</th><th class="n">ĐK3</th><th class="n">ĐK4</th>
<th class="n">Bị loại</th><th class="n">Bắt lỗi chèn</th><th class="n">Lượt gọi lỗi</th></tr></thead><tbody>{model_rows}</tbody></table></div>
<p class="small">"Bắt lỗi chèn": tỉ lệ bị loại trong các loại lỗi kỹ thuật được chèn có chủ đích vào ĐK4. Lỗi ngữ nghĩa với trích dẫn nguyên văn gần như không bị bắt, đúng như thiết kế.{sampled}</p></section>
<section><h2>Bị loại vì đâu</h2>
<p>Với mỗi giá trị không nằm nguyên văn trong câu, chương trình tìm xem nó có trong câu dẫn của khoản hoặc tên Điều không. Bị loại không có nghĩa là sai.</p>
<div class="legend">{legend}</div><table class="chart"><tbody>{chart_rows}</tbody></table></section>
<section class="cols">{notes}</section>
</main></body></html>
"""
