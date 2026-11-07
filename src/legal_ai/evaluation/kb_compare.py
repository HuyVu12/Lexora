"""Side-by-side numbers of knowledge-base extraction runs (`kb-compare-v1`), for the thesis and the app.

`summarize` reads one run directory (written by `kb-extract`): the manifest, `raw.jsonl` (calls, errors, tokens,
cost) and `report.json` (DK3/DK4 sizes, rejection reasons, check outcomes), plus the planted-error report of the
same run when one exists next to it. `compare` re-materializes every run with the current validator first, so all
runs are judged by the same rules, then writes a JSON file and a Markdown table. Offline; no model call.
"""

from datetime import datetime, timezone
import json
from pathlib import Path

from legal_ai.common.io import read_jsonl, write_json

COMPARE_VERSION = "kb-compare-v1"
KB_RUN = "llm-kb-run-v1"
REASON_LABELS = {"actor_not_verbatim": "chủ thể không nguyên văn", "action_not_verbatim": "hành vi không nguyên văn",
                 "object_not_verbatim": "đối tượng không nguyên văn", "outcome_not_verbatim": "kết quả không nguyên văn",
                 "conditions_not_verbatim": "điều kiện không nguyên văn", "exceptions_not_verbatim": "ngoại lệ không nguyên văn",
                 "quantities_not_verbatim": "định lượng không nguyên văn", "deadlines_not_verbatim": "thời hạn không nguyên văn",
                 "beneficiary_not_verbatim": "bên thụ hưởng không nguyên văn", "recipient_not_verbatim": "bên nhận không nguyên văn",
                 "modality_cue_not_verbatim": "từ tình thái bịa", "modality_cue_mismatch": "từ tình thái mâu thuẫn",
                 "modality_not_in_enum": "tính quy phạm sai kiểu", "content_missing": "không có nội dung", "duplicate_of": "trùng lặp",
                 "slots_malformed": "sai cấu trúc", "unit_unknown": "đơn vị không tồn tại", "unit_version_mismatch": "sai phiên bản đơn vị",
                 "sentence_outside_unit": "câu ngoài đơn vị"}


def kb_runs(folder):
    """Knowledge-base run directories under `folder`, oldest first."""
    found = []
    for manifest in sorted(Path(folder).glob("*/manifest.json")):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if data.get("run_version") == KB_RUN and (manifest.parent / "raw.jsonl").exists():
            found.append((data.get("created_at", ""), manifest.parent))
    return [path for _, path in sorted(found)]


def _injection(run_dir):
    for report in Path(run_dir).parent.glob("*/report.json"):
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if data.get("injection_version") and Path(data.get("kb_run", "")).name == Path(run_dir).name:
            detectable = {k: v for k, v in data["by_type"].items() if v["expected_detectable"]}
            semantic = {k: v for k, v in data["by_type"].items() if not v["expected_detectable"]}
            rate = lambda rows: (sum(v["rejected"] for v in rows.values()) / sum(v["injected"] for v in rows.values())
                                 if sum(v["injected"] for v in rows.values()) else None)
            return {"run": report.parent.name, "validator_version": data["validator_version"], "clean_claims": data["clean_claims"],
                    "false_reject_rate": data["false_reject_rate"], "detectable_rate": rate(detectable), "semantic_rate": rate(semantic),
                    "by_type": {k: {"injected": v["injected"], "detection_rate": v["detection_rate"], "expected_detectable": v["expected_detectable"]}
                                for k, v in data["by_type"].items()}}
    return None


def summarize(run_dir):
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    report = json.loads((run_dir / "report.json").read_text(encoding="utf-8")) if (run_dir / "report.json").exists() else {}
    raw = read_jsonl(run_dir / "raw.jsonl")
    latest = {}
    for row in raw:
        if row["key"] not in latest or row.get("status") == "ok":
            latest[row["key"]] = row
    errors = {}
    for row in latest.values():
        if row.get("status") != "ok":
            errors[row.get("code")] = errors.get(row.get("code"), 0) + 1
    usage = lambda *names: sum(sum((row.get("usage") or {}).get(name) or 0 for name in names) for row in raw)
    dk3, dk4 = report.get("dk3_claims", 0), report.get("dk4_claims", 0)
    sentences = sum(len(row["rows"]) for row in latest.values())
    return {"run": run_dir.name, "run_id": manifest.get("run_id"), "created_at": manifest.get("created_at"),
            "provider": manifest.get("provider", "claude-code"), "model": manifest.get("model"), "effort": manifest.get("effort"),
            "max_tokens": manifest.get("max_tokens"), "validator_version": report.get("validator_version"),
            "batches_attempted": len(latest), "batches_ok": sum(row.get("status") == "ok" for row in latest.values()),
            "batch_errors": errors, "calls_made": len(raw), "sentences_attempted": sentences,
            "sentences_without_answer": report.get("sentences_without_answer"),
            "dk3_claims": dk3, "dk4_claims": dk4, "rejected": dk3 - dk4, "rejected_rate": (dk3 - dk4) / dk3 if dk3 else None,
            "reasons": report.get("reasons", {}), "checks": report.get("checks", {}),
            "modality_unverified_rate": (report.get("checks", {}).get("V4_modality", {}).get("unverified", 0) / dk3) if dk3 else None,
            # Claude Code reports cached prompt parts separately; 9Router reports prompt/completion tokens.
            "prompt_tokens": usage("prompt_tokens", "input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"),
            "completion_tokens": usage("completion_tokens", "output_tokens"),
            "cost_usd": report.get("cost_usd"), "injection": _injection(run_dir)}


def _cost(value):
    return "-" if not value else f"{value:.2f} USD"


def _pct(value):
    return "-" if value is None else f"{value * 100:.1f}%"


def markdown(summaries, generated_at):
    lines = ["# So sánh model trích xuất kho tri thức (ĐK3/ĐK4)", "",
             f"Tệp do `python -m legal_ai.cli kb-compare` sinh ra lúc {generated_at}; không sửa tay.",
             "Mọi lượt dùng cùng phạm vi thực nghiệm, cùng prompt `norm-llm-v1` và được kiểm chứng lại bằng cùng một bộ kiểm chứng.", "",
             "| Model | Nhà cung cấp | Lượt OK / thử | Câu chưa có trả lời | ĐK3 | ĐK4 | Bị loại | Tính quy phạm chưa xác minh | Chi phí niêm yết |",
             "|---|---|---|---|---|---|---|---|---|"]
    for s in summaries:
        lines.append(f"| `{s['model']}` | {s['provider']} | {s['batches_ok']}/{s['batches_attempted']} | {s['sentences_without_answer']} | "
                     f"{s['dk3_claims']} | {s['dk4_claims']} | {s['rejected']} ({_pct(s['rejected_rate'])}) | {_pct(s['modality_unverified_rate'])} | "
                     f"{_cost(s['cost_usd'])} |")
    lines += ["", "## Lý do bị loại", ""]
    for s in summaries:
        reasons = ", ".join(f"{REASON_LABELS.get(k, k)}: {v}" for k, v in sorted(s["reasons"].items(), key=lambda kv: -kv[1])) or "không có"
        errors = ", ".join(f"{k}: {v}" for k, v in s["batch_errors"].items()) or "không có"
        lines.append(f"- `{s['model']}`: {reasons}. Lượt lỗi: {errors}.")
    lines += ["", "## Chèn lỗi có chủ đích (RQ2)", ""]
    for s in summaries:
        inj = s["injection"]
        if inj:
            lines.append(f"- `{s['model']}`: bắt {_pct(inj['detectable_rate'])} lỗi thuộc loại phát hiện được, {_pct(inj['semantic_rate'])} lỗi ngữ nghĩa, "
                         f"loại nhầm {_pct(inj['false_reject_rate'])} trên {inj['clean_claims']} bản ghi sạch ({inj['validator_version']}).")
        else:
            lines.append(f"- `{s['model']}`: chưa chạy `kb-inject`.")
    lines += ["", "Chi phí chỉ có với Claude Code (giá niêm yết, trừ vào hạn mức gói); lượt qua 9Router không báo chi phí.", ""]
    return "\n".join(lines)


def compare(run_dirs, json_path, md_path):
    from legal_ai.evaluation.kb_run import materialize
    for run_dir in run_dirs:
        bundle = json.loads((Path(run_dir) / "manifest.json").read_text(encoding="utf-8"))["bundle"]
        materialize(read_jsonl(Path(bundle) / "units.jsonl"), run_dir)
    summaries = [summarize(run_dir) for run_dir in run_dirs]
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    write_json(json_path, {"compare_version": COMPARE_VERSION, "generated_at": generated_at, "runs": summaries})
    Path(md_path).parent.mkdir(parents=True, exist_ok=True)
    Path(md_path).write_text(markdown(summaries, generated_at), encoding="utf-8")
    return summaries
