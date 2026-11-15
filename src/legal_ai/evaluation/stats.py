"""Paired statistics over questions (`paired-stats-v1`): condition differences with a bootstrap, Holm and noise.

Every comparison pairs two runs on the questions both scored. `paired_bootstrap` resamples the per-question
differences (second minus first) with replacement, `rounds` times (default 10,000) from `random.Random(seed)`
restarted for every comparison, so a result depends only on its own two runs, never on the other pairs. It reports
the mean difference, the percentile 95% interval, wins/losses/ties and a two-sided p-value: the share of resampled
means, shifted by the observed mean so that they follow the null of no difference, at least as far from zero as the
observed mean, counted as (1 + hits) / (1 + rounds) so it is never 0. `holm` adjusts the p-values of the declared
family (the four main comparisons DK1:DK2, DK2:DK3, DK3:DK4, DK1:DK4 by default); other pairs are exploratory and keep
their raw p. `noise` compares two runs of the same condition (two generations, or two gradings of the same answers)
the same way and adds the mean absolute per-question difference.

Per-question values come from the scoring modules, never re-derived here: a metric name carries its source,
`retrieval.<name>` (`predictions.jsonl` of a retrieval run: recall@K, complete@K, recall_at_tokens@B,
complete_at_tokens@B, context_tokens@K, stale_context_at_tokens@B, recall_at_adaptive), `answer.<name>`
(`answer_run.question_scores`), `grades.<name>` (`answer_grading.item_scores` of a filled sheet and its key) and
`judge.<name>` (`outcome_judge.item_scores`). A question present in one run of a pair but absent, unscored (failed
answer, ungraded or unjudged item) or without a value in the other is listed in the comparison, never dropped silently.
"""

import json
import math
from pathlib import Path
import random

from legal_ai.common.io import digest, read_jsonl
from legal_ai.evaluation import answer_grading, outcome_judge
from legal_ai.evaluation.answer_run import ANSWER_METRICS, answers_not_in_questions, question_scores

STATS_VERSION = "paired-stats-v1"
ROUNDS = 10_000
SEED = "lexora-paired-v1"
MAIN_PAIRS = (("DK1", "DK2"), ("DK2", "DK3"), ("DK3", "DK4"), ("DK1", "DK4"))
RETRIEVAL_METRICS = {"recall": "recall", "complete": "recall", "context_tokens": "context_tokens",
                     "recall_at_tokens": "recall_at_tokens", "complete_at_tokens": "recall_at_tokens", "stale_context_at_tokens": "stale_at_tokens"}
EPSILON = 1e-12


def _mean(values):
    return math.fsum(values) / len(values) if values else None


def _round(value):
    return None if value is None else round(value, 6)


def paired_bootstrap(diffs, rounds=ROUNDS, seed=SEED):
    """Mean of the paired differences with a percentile 95% interval, a two-sided p-value, wins, losses and ties."""
    if rounds < 1:
        raise ValueError("rounds must be at least 1")
    n = len(diffs)
    counts = {"wins": sum(d > EPSILON for d in diffs), "losses": sum(d < -EPSILON for d in diffs)}
    counts["ties"] = n - counts["wins"] - counts["losses"]
    if not n:
        return {"n": 0, "difference": None, "ci95": None, "p_value": None} | counts
    observed = _mean(diffs)
    rng = random.Random(seed)
    draw = rng.random
    means = sorted(math.fsum([diffs[int(draw() * n)] for _ in range(n)]) / n for _ in range(rounds))
    hits = sum(abs(m - observed) >= abs(observed) - EPSILON for m in means)
    low = rounds * 25 // 1000  # 2.5% of the resampled means lie below the interval and 2.5% above it.
    return {"n": n, "difference": observed, "ci95": [means[low], means[rounds - 1 - low]], "p_value": (1 + hits) / (1 + rounds)} | counts


def holm(p_values):
    """Holm step-down adjusted p-values in the input order: monotone in the sorted order and capped at 1. A comparison
    without a p-value (no paired question) still counts in the family, as the least significant, and stays None."""
    m = len(p_values)
    order = sorted(range(m), key=lambda i: 1.0 if p_values[i] is None else p_values[i])
    adjusted, running = [None] * m, 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * (1.0 if p_values[i] is None else p_values[i])))
        adjusted[i] = None if p_values[i] is None else running
    return adjusted


def _paired(first, second, names):
    """Question IDs both runs scored, their differences, and what kept every other question out."""
    a, b = first["values"], second["values"]
    questions = {"paired": 0, "not_applicable": 0, "missing": {n: [] for n in names}, "unscored": {n: [] for n in names},
                 "no_value": {n: [] for n in names}}
    paired = []
    for qid in sorted(set(a) | set(b) | set(first["unscored"]) | set(second["unscored"])):
        if qid in a and qid in b:
            if a[qid] is None and b[qid] is None:
                questions["not_applicable"] += 1  # The metric does not apply to the question in either run.
            elif a[qid] is None or b[qid] is None:
                questions["no_value"][names[0] if a[qid] is None else names[1]].append(qid)
            else:
                paired.append(qid)
            continue
        for name, run in zip(names, (first, second)):
            if qid not in run["values"]:
                questions["unscored" if qid in run["unscored"] else "missing"][name].append(qid)
    questions["paired"] = len(paired)
    return paired, [b[q] - a[q] for q in paired], questions


def _summary(first, second, paired, diffs, questions, rounds, seed):
    return {"mean_first": _mean([first["values"][q] for q in paired]), "mean_second": _mean([second["values"][q] for q in paired]),
            **paired_bootstrap(diffs, rounds, seed), "questions": questions}


def compare(first, second, rounds=ROUNDS, seed=SEED, names=("first", "second")):
    """Paired comparison of two runs ({"values": {question_id: value or None}, "unscored": [question_id]}):
    second minus first on the questions both scored."""
    return _summary(first, second, *_paired(first, second, names), rounds, seed)


def noise(first, second, rounds=ROUNDS, seed=SEED):
    """Disagreement of two runs of the same condition on the same questions (generation or grading noise): the paired
    comparison plus the mean absolute per-question difference and how many questions changed value."""
    paired, diffs, questions = _paired(first, second, ("first", "second"))
    return _summary(first, second, paired, diffs, questions, rounds, seed) | {
        "mean_abs_difference": _mean([abs(d) for d in diffs]), "changed": sum(abs(d) > EPSILON for d in diffs)}


def _pooled(runs):
    """All labels' runs as one run keyed by label/question, so noise can be measured across conditions."""
    return {"values": {f"{label}/{q}": v for label, run in runs.items() for q, v in run["values"].items()},
            "unscored": [f"{label}/{q}" for label, run in runs.items() for q in run["unscored"]]}


def _rounded(block):
    if isinstance(block, dict):
        return {k: _rounded(v) for k, v in block.items()}
    if isinstance(block, list):
        return [_rounded(v) for v in block]
    return _round(block) if isinstance(block, float) else block


def _left_out(what, questions):
    """One warning per run and reason for the questions a pairing could not use."""
    return [f"{what}: {len(ids)} question(s) {reason.replace('_', ' ')} in {name}, left out of the pairing"
            for reason in ("missing", "unscored", "no_value") for name, ids in questions[reason].items() if ids]


def build_report(metric, runs, pairs=MAIN_PAIRS, exploratory=(), repeats=None, regraded=None, rounds=ROUNDS, seed=SEED, inputs=None):
    """The full report from per-question values already loaded: `runs`, `repeats` (second generation of a label,
    graded the same way) and `regraded` (the same answers graded a second time), each {label: run}; `inputs`
    (paths and hashes) is recorded as given."""
    labels = set(runs)
    for a, b in list(pairs) + list(exploratory):
        if a not in labels or b not in labels:
            raise ValueError(f"pair {a}:{b} names a label without a run; labels: {sorted(labels)}")
    for name, extra in (("repeat", repeats or {}), ("regrade", regraded or {})):
        if set(extra) - labels:
            raise ValueError(f"{name} labels without a main run: {sorted(set(extra) - labels)}")
    if len(set(pairs) | set(exploratory)) != len(pairs) + len(exploratory):
        raise ValueError("a pair is declared twice")
    report = {"stats_version": STATS_VERSION, "metric": metric, "inputs": inputs or {},
              "method": {"rounds": rounds, "seed": seed, "difference": "second minus first per question, mean over the questions both runs scored",
                         "resampling": "paired bootstrap over questions; random.Random(seed) restarted for every comparison",
                         "ci95": "percentile interval of the resampled means (2.5% cut from each tail)",
                         "p_value": "two-sided: (1 + resampled means shifted to the null at least as far from 0 as the observed mean) / (1 + rounds)",
                         "holm": "step-down over the main family only; exploratory pairs keep their raw p",
                         "noise": "two runs of the same label on the same questions; difference = second minus first"},
              "runs": {}, "comparisons": [], "noise": {}, "warnings": []}
    for label, run in runs.items():
        values = [v for v in run["values"].values() if v is not None]
        report["runs"][label] = {"mean": _mean(values), "scored": len(values),
                                 "not_applicable": sum(v is None for v in run["values"].values()), "unscored": sorted(run["unscored"])}
    kinds = {"generation": {label: (runs[label], second) for label, second in (repeats or {}).items()},
             "grading": {label: (runs[label], second) for label, second in (regraded or {}).items()}}
    for kind, items in kinds.items():
        if not items:
            continue
        report["noise"][kind] = {"by_label": {label: noise(a, b, rounds, seed) for label, (a, b) in sorted(items.items())},
                                 "pooled": noise(_pooled({l: a for l, (a, _) in items.items()}), _pooled({l: b for l, (_, b) in items.items()}), rounds, seed)}
        for label, block in report["noise"][kind]["by_label"].items():
            report["warnings"] += _left_out(f"{kind} noise of {label}", block["questions"])
    for family, declared in (("main", pairs), ("exploratory", exploratory)):
        for a, b in declared:
            entry = {"pair": f"{a}:{b}", "first": a, "second": b, "family": family, "difference_of": f"{b} minus {a}"}
            entry |= compare(runs[a], runs[b], rounds, seed, (a, b) if a != b else ("first", "second"))
            entry["noise"] = {kind: {label: {"difference": block["by_label"][label]["difference"],
                                             "mean_abs_difference": block["by_label"][label]["mean_abs_difference"]}
                                     for label in (a, b) if label in block["by_label"]} for kind, block in report["noise"].items()}
            report["comparisons"].append(entry)
            report["warnings"] += _left_out(entry["pair"], entry["questions"])
    main = [c for c in report["comparisons"] if c["family"] == "main"]
    for entry, adjusted in zip(main, holm([c["p_value"] for c in main])):
        entry["p_holm"] = adjusted
    for entry in report["comparisons"]:
        entry.setdefault("p_holm", None)
    return _rounded(report)


# Loading per-question values from run directories.

def parse_metric(metric):
    source, _, name = metric.partition(".")
    if source not in ("retrieval", "answer", "grades", "judge") or not name:
        raise ValueError(f"metric must be retrieval.<name>, answer.<name>, grades.<name> or judge.<name>, not {metric!r}")
    return source, name


def _file(path):
    return {"path": Path(path).as_posix(), "sha256": digest(Path(path).read_bytes())}


def _retrieval_values(name, run_dir):
    run_dir = Path(run_dir)
    field, _, point = name.partition("@")
    if name == "recall_at_adaptive":
        pick = lambda row: row.get("recall_at_adaptive")
    elif field in RETRIEVAL_METRICS and point:
        def pick(row):
            block = row.get(RETRIEVAL_METRICS[field])
            if field == "stale_context_at_tokens":
                value = (block or {}).get(point)  # Only questions with outdated units carry it.
            elif block is None or point not in block:
                raise ValueError(f"retrieval.{name}: {point} is not measured in {run_dir.as_posix()} (has {sorted(block or {}, key=int)})")
            else:
                value = block[point]
            if value is None:
                return None
            return float(value == 1.0) if field.startswith("complete") else float(value)
    else:
        raise ValueError(f"unknown retrieval metric {name!r}; use recall@K, complete@K, context_tokens@K, recall_at_tokens@B, "
                         "complete_at_tokens@B, stale_context_at_tokens@B or recall_at_adaptive")
    rows = read_jsonl(run_dir / "predictions.jsonl")
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    return {"values": {row["question_id"]: pick(row) for row in rows}, "unscored": [],
            "info": {"run": run_dir.as_posix(), "condition": manifest["condition"]["condition"],
                     "questions_sha256": manifest["inputs"]["questions"]["sha256"], "predictions": _file(run_dir / "predictions.jsonl")}}


def _answer_values(name, run_dir, questions):
    if name not in ANSWER_METRICS:
        raise ValueError(f"unknown answer metric {name!r}; use one of {', '.join(ANSWER_METRICS)}")
    if not questions:
        raise ValueError("answer.* metrics need --questions")
    run_dir = Path(run_dir)
    scores = question_scores(run_dir, questions)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    return {"values": {q: s[name] for q, s in scores.items() if s["error"] is None},
            "unscored": sorted(q for q, s in scores.items() if s["error"] is not None),
            "info": {"run": run_dir.as_posix(), "condition": manifest["condition"], "model": manifest["model"],
                     "questions_sha256": manifest["questions_sha256"], "answers": _file(run_dir / "answers.jsonl"),
                     "answers_not_in_questions": answers_not_in_questions(run_dir, questions)}}


def _graded_values(source, name, run_dirs, sheet, key, judge):
    """Values of graded items (filled sheet or outcome judge run) for each answer run, found through the key."""
    allowed = answer_grading.SHEET_METRICS if source == "grades" else outcome_judge.METRICS + ("refused",)
    if name not in allowed:
        raise ValueError(f"unknown {source} metric {name!r}; use one of {', '.join(allowed)}")
    if not sheet or not key or (source == "judge" and not judge):
        raise ValueError(f"{source}.* metrics need --sheet and --key" + (" and --judge" if source == "judge" else ""))
    key_file = json.loads(Path(key).read_text(encoding="utf-8"))
    items, failed = key_file["items"], key_file.get("failed")  # Keys made before failures were recorded have none.
    scores = answer_grading.item_scores(sheet) if source == "grades" else outcome_judge.item_scores(judge, sheet)
    result = {}
    for label, run_dir in run_dirs.items():
        target = Path(run_dir).resolve()
        mine = {item_id: entry for item_id, entry in items.items() if Path(entry["answer_dir"]).resolve() == target}
        lost = sorted(e["question_id"] for e in (failed or {}).values() if Path(e["answer_dir"]).resolve() == target)
        if not mine and not lost:
            raise ValueError(f"{label}: answer run {Path(run_dir).as_posix()} is not in the key {Path(key).as_posix()}")
        value = lambda v: None if v is None else float(v)
        result[label] = {"values": {e["question_id"]: value(scores[i][name]) for i, e in mine.items() if i in scores},
                         # Unscored: items not graded or judged, and answers that failed before grading.
                         "unscored": sorted([e["question_id"] for i, e in mine.items() if i not in scores] + lost),
                         "info": {"run": Path(run_dir).as_posix(), "condition": next(iter(mine.values()), {"condition": None})["condition"],
                                  "items": len(mine), "failed_answers": None if failed is None else len(lost)}}
    return result


def load_values(metric, run_dirs, questions=None, sheet=None, key=None, judge=None):
    """{label: {"values", "unscored", "info"}} of one metric for labelled run directories."""
    source, name = parse_metric(metric)
    if source == "retrieval":
        return {label: _retrieval_values(name, d) for label, d in run_dirs.items()}
    if source == "answer":
        return {label: _answer_values(name, d, questions) for label, d in run_dirs.items()}
    return _graded_values(source, name, run_dirs, sheet, key, judge)


def labelled(specs):
    """{label: directory} from LABEL=DIR arguments."""
    result = {}
    for spec in specs or ():
        label, sep, path = spec.partition("=")
        if not sep or not label or not path:
            raise ValueError(f"expected LABEL=DIR, got {spec!r}")
        if label in result:
            raise ValueError(f"label {label} given twice")
        result[label] = path
    return result


def parse_pairs(specs):
    pairs = []
    for spec in specs or ():
        first, sep, second = spec.partition(":")
        if not sep or not first or not second or ":" in second:
            raise ValueError(f"expected A:B (B minus A), got {spec!r}")
        pairs.append((first, second))
    return pairs


def compare_runs(metric, runs, pairs=MAIN_PAIRS, exploratory=(), repeats=None, regrade=None, questions=None, sheet=None, key=None,
                 judge=None, rounds=ROUNDS, seed=SEED):
    """Load the metric for labelled runs ({label: dir}) and build the report. `repeats` are second generation runs
    ({label: dir}, graded by the same sheet or judge run); `regrade` is a second grading of the same answers: another
    outcome judge run (judge.*) or another filled sheet of the same key (grades.*)."""
    source, _ = parse_metric(metric)
    if regrade and source not in ("grades", "judge"):
        raise ValueError("--regrade applies to grades.* and judge.* metrics only")
    loaded = load_values(metric, runs, questions, sheet, key, judge)
    second = load_values(metric, repeats, questions, sheet, key, judge) if repeats else None
    regraded = None
    if regrade:
        regraded = load_values(metric, runs, questions, regrade if source == "grades" else sheet, key, regrade if source == "judge" else None)
    inputs = {"runs": {l: r["info"] for l, r in loaded.items()}, "repeats": {l: r["info"] for l, r in (second or {}).items()}}
    for name, path in (("questions", questions), ("sheet", sheet), ("key", key)):
        if path:
            inputs[name] = _file(path)
    if judge:
        inputs["judge"] = _file(Path(judge) / "judged.jsonl")
    if regrade:
        inputs["regrade"] = _file(Path(regrade) / "judged.jsonl" if source == "judge" else regrade)
    values = lambda block: block and {l: {k: r[k] for k in ("values", "unscored")} for l, r in block.items()}
    report = build_report(metric, values(loaded), pairs, exploratory, values(second), values(regraded), rounds, seed, inputs)
    hashes = {r["info"]["questions_sha256"] for r in list(loaded.values()) + list((second or {}).values()) if "questions_sha256" in r["info"]}
    if len(hashes) > 1:
        report["warnings"].insert(0, "the runs were made from different question files (questions_sha256 differ)")
    if questions and source == "answer" and hashes and inputs["questions"]["sha256"] not in hashes:
        report["warnings"].insert(0, "--questions differs from the question file the answer runs were made from")
    for name, block in (("runs", loaded), ("repeats", second or {})):
        for label, r in block.items():
            if r["info"].get("answers_not_in_questions"):
                report["warnings"].append(f"{name} {label}: {len(r['info']['answers_not_in_questions'])} answer(s) to questions not in --questions, left out")
    if source in ("grades", "judge") and json.loads(Path(key).read_text(encoding="utf-8")).get("failed") is None:
        report["warnings"].append("the key predates recorded failures: answers that failed before grading show as missing, not unscored")
    return report


def table(report):
    """Compact text table of a report: run means, comparisons with noise, warnings."""
    fmt = lambda v, sign=False: "-" if v is None else (f"{v:+.4f}" if sign else f"{v:.4f}")
    lines = [f"{report['stats_version']}  metric={report['metric']}  rounds={report['method']['rounds']}  seed={report['method']['seed']}", "",
             f"{'run':<14}{'scored':>7}{'n/a':>5}{'unscored':>9}  mean"]
    for label, run in report["runs"].items():
        lines.append(f"{label:<14}{run['scored']:>7}{run['not_applicable']:>5}{len(run['unscored']):>9}  {fmt(run['mean'])}")
    noise_kinds = list(report["noise"])
    lines += ["", f"{'pair (B-A)':<16}{'n':>4}  {'diff':>8}  {'95% CI':<19}  {'p':>7}  {'p_holm':>7}  {'W/L/T':<9}"
              + "".join(f"  {('noise ' + k[:3]):<17}" for k in noise_kinds)]
    for c in report["comparisons"]:
        ci = "-" if c["ci95"] is None else f"[{c['ci95'][0]:+.3f}, {c['ci95'][1]:+.3f}]"
        row = (f"{c['pair'] + ('' if c['family'] == 'main' else ' *'):<16}{c['n']:>4}  {fmt(c['difference'], True):>8}  {ci:<19}  "
               f"{fmt(c['p_value']):>7}  {fmt(c['p_holm']):>7}  {str(c['wins']) + '/' + str(c['losses']) + '/' + str(c['ties']):<9}")
        for kind in noise_kinds:
            parts = [f"{fmt(c['noise'][kind][l]['difference'], True)}" if l in c["noise"][kind] else "-" for l in (c["first"], c["second"])]
            row += f"  {'/'.join(parts):<17}"
        lines.append(row)
    if any(c["family"] == "exploratory" for c in report["comparisons"]):
        lines.append("* exploratory: not in the Holm family")
    for kind, block in report["noise"].items():
        lines += ["", f"noise ({kind}): label  n  diff  95% CI  mean|diff|  changed"]
        for label, n in list(block["by_label"].items()) + [("pooled", block["pooled"])]:
            ci = "-" if n["ci95"] is None else f"[{n['ci95'][0]:+.3f}, {n['ci95'][1]:+.3f}]"
            lines.append(f"  {label:<12}{n['n']:>4}  {fmt(n['difference'], True)}  {ci}  {fmt(n['mean_abs_difference'])}  {n['changed']}")
    if report["warnings"]:
        lines += ["", "warnings:"] + [f"  {w}" for w in report["warnings"]]
    return "\n".join(lines)
