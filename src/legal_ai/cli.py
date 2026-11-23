"""Local CLI. Network access only via the explicit snapshot and vbpl-fetch subcommands."""

import argparse
import json
from pathlib import Path

from legal_ai.common.io import read_jsonl, write_json, write_jsonl, digest
from legal_ai.ingestion.parser import parse
from legal_ai.ingestion.snapshot import snapshot
from legal_ai.normalization.text import normalize
from legal_ai.schemas.contract import VERSION, validate_document, validate_unit, validate_evidence


def main():
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="lexora")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("snapshot", help="download an explicitly approved vbpl HTML snapshot")
    command.add_argument("url")
    command.add_argument("--document-id", required=True)
    command.add_argument("--marker", required=True)
    command.add_argument("--output", default="data/raw")
    command = commands.add_parser("parse", help="parse a UTF-8 text source, without network access")
    command.add_argument("input")
    command.add_argument("--document-id", required=True)
    command.add_argument("--output", required=True)
    command = commands.add_parser("validate", help="check a JSONL contract bundle")
    command.add_argument("bundle")
    command.add_argument("--output", required=True)
    command = commands.add_parser("build-pilot", help="build pilot from pinned local VBPL snapshots")
    command.add_argument("--config", default="configs/sources-pilot.json")
    command.add_argument("--raw-root", default="data/raw")
    command.add_argument("--output", required=True)
    command = commands.add_parser("search", help="retrieve exact source passages; no generated legal answer")
    command.add_argument("bundle")
    command.add_argument("question")
    command.add_argument("--top-k", type=int, default=5)
    command = commands.add_parser("catalog-build", help="build the local document catalog from downloaded dataset files; no network")
    command.add_argument("--raw", default="data/catalog/raw")
    command.add_argument("--output", required=True, help="new catalog file, e.g. data/catalog/catalog-v1.sqlite")
    command = commands.add_parser("catalog-search", help="search the local catalog by title or number, accents ignored; no network")
    command.add_argument("catalog")
    command.add_argument("query")
    command.add_argument("--limit", type=int, default=10)
    command.add_argument("--include-translations", action="store_true")
    command = commands.add_parser("vbpl-fetch", help="fetch ONE explicitly approved vbpl.vn document (link or ID) as an immutable snapshot")
    command.add_argument("reference", help="vbpl.vn document link or ID")
    command.add_argument("--output", default="data/raw/vbpl")
    command = commands.add_parser("corpus-export", help="write a frozen research corpus version as a contract bundle for run-retrieval")
    command.add_argument("--store", required=True, help="workspace SQLite store of the web app")
    command.add_argument("--version", required=True, help="corpus version ID (shown in the app)")
    command.add_argument("--output", required=True, help="new, empty directory")
    command = commands.add_parser("corpus-version-export", help="write one frozen research corpus version (rows, source bytes, hashes) to a JSON file for another store; offline")
    command.add_argument("--store", required=True, help="workspace SQLite store holding the version")
    command.add_argument("--version", required=True, help="corpus version ID (shown in the app)")
    command.add_argument("--output", required=True, help="new JSON file")
    command = commands.add_parser("corpus-version-import", help="add a frozen corpus version from a corpus-version-export file to a store, same ID and bundle hash; offline")
    command.add_argument("file", help="file written by corpus-version-export")
    command.add_argument("--store", required=True, help="workspace SQLite store to add the version to")
    command.add_argument("--actor", required=True, help="account recorded as the importer")
    command.add_argument("--expect-version", help="refuse the file unless it holds this version ID")
    command = commands.add_parser("corpus-scope", help="create a research corpus from the chosen articles of pinned local vbpl.vn snapshots; no network")
    command.add_argument("--store", required=True, help="workspace SQLite store of the web app")
    command.add_argument("--config", default="configs/experiment-scope-v1.json")
    command.add_argument("--actor", required=True, help="account name recorded as the creator")
    command = commands.add_parser("kb-extract", help="DK3/DK4 knowledge base: one Claude Code model extracts norms from every sentence of a corpus bundle")
    command.add_argument("bundle", help="contract bundle written by corpus-export")
    command.add_argument("--output", required=True, help="new directory, or an earlier run of the same bundle to resume")
    command.add_argument("--model", default="claude-opus-5-5")
    command.add_argument("--effort", default="medium")
    command.add_argument("--max-calls", type=int, default=0, help="call budget of this session (required unless --dry-run)")
    command.add_argument("--approve-claude", action="store_true", help="explicit approval of the model calls")
    command.add_argument("--router-model", help="extract with one approved 9Router model instead (a MODEL_* alias from .env or a model name)")
    command.add_argument("--approve-router", action="store_true", help="explicit approval of the 9Router endpoint, model and data")
    command.add_argument("--timeout", type=int, default=300, help="seconds per 9Router call (5-600)")
    command.add_argument("--max-tokens", type=int, default=16000, help="output token limit per 9Router call, the same for every compared model")
    command.add_argument("--dry-run", action="store_true", help="only count batches and characters; no model call")
    command = commands.add_parser("kb-materialize", help="rebuild dk3/dk4 and the validation report of a knowledge-base run from raw.jsonl; offline")
    command.add_argument("run", help="knowledge-base run directory")
    command.add_argument("--bundle", help="contract bundle (default: the one recorded in the run manifest)")
    command.add_argument("--output", help="new directory for a derived knowledge base (the run itself is not touched); needed for a non-default --validator or --inherit")
    command.add_argument("--validator", default="kb-validator-v3", choices=["kb-validator-v3", "kb-validator-v4"],
                         help="kb-validator-v4 also accepts values quoted from the parent unit's lead-in")
    command.add_argument("--inherit", choices=["claims-inherit-v1"], help="fill an empty actor, action or outcome from the parent's lead-in before validation (needs kb-validator-v4)")
    command = commands.add_parser("kb-keys-gen", help="kb-keys-v2 model keys: 2-3 everyday questions per unit with claims, written by one Claude Code model; retrieval index only; resumes")
    command.add_argument("kb_run", help="knowledge-base run (normally a derived one: claims-inherit-v1 + kb-validator-v4)")
    command.add_argument("--bundle", required=True, help="contract bundle the knowledge base was extracted from")
    command.add_argument("--output", required=True, help="new directory, or an earlier keys run with the same inputs to resume")
    scope = command.add_mutually_exclusive_group(required=True)
    scope.add_argument("--units-from", nargs="+", metavar="PATH", help="retrieval run directories (top-N records) or question files (gold units): keys for the units of the Articles they touch")
    scope.add_argument("--all", action="store_true", help="keys for every leaf unit with claims")
    command.add_argument("--top-n", type=int, default=30, help="ranked records per question taken from a retrieval run")
    command.add_argument("--split", help="only questions of this split (for example dev)")
    command.add_argument("--batch-size", type=int, default=8, help="units per call (one Article per call)")
    command.add_argument("--max-calls", type=int, default=0, help="call budget of this session (required unless --dry-run)")
    command.add_argument("--extract-claude-model", help="Claude Code model, e.g. claude-sonnet-5-5 (required unless --dry-run)")
    command.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    command.add_argument("--approve-claude", action="store_true", help="explicit approval of the model calls")
    command.add_argument("--dry-run", action="store_true", help="write the plan and the exact prompts; no model call")
    command.add_argument("--reuse", nargs="+", metavar="RUN", help="earlier keys runs (same model, effort, prompt, bundle, knowledge base) whose answered batches are copied instead of paid again")
    command = commands.add_parser("amendment-build", help="amendment edges (amendment-rules-v2) of pinned vbpl.vn snapshots against a corpus bundle; offline, no model")
    command.add_argument("bundle", help="contract bundle whose units are the targets")
    command.add_argument("--config", default="configs/amendments-v1.json", help="amending sources (pinned snapshots)")
    command.add_argument("--output", required=True, help="new directory for edges.jsonl and manifest.json")
    command = commands.add_parser("amendment-sheet", help="CSV check sheet with one row per amendment edge (resolved or not) for two people to compare with the source text; offline")
    command.add_argument("edges", help="amendment-build output directory (edges.jsonl, manifest.json)")
    command.add_argument("--sheet", required=True, help="new CSV file to write")
    command.add_argument("--bundle", help="contract bundle (default: the one recorded in the edge manifest)")
    command = commands.add_parser("amendment-score", help="verdict counts of a filled amendment check sheet; with --compare, agreement of two checkers; offline")
    command.add_argument("sheet")
    command.add_argument("--compare", help="the second checker's sheet of the same edges: raw agreement and Cohen's kappa")
    command = commands.add_parser("budget-report", help="recall-by-token-budget tables and SVG curves from retrieval runs; offline")
    command.add_argument("--runs", nargs="+", required=True, help="LABEL=RUN_DIR pairs; the label groups runs into one figure (SET:CONDITION)")
    command.add_argument("--output", required=True, help="Markdown file; one SVG per question set is written next to it")
    command.add_argument("--title", default="Đường cong recall theo ngân sách token")
    command.add_argument("--set-title", nargs="*", default=[], help="SET=Title pairs for headings and figure titles")
    command = commands.add_parser("answer-run", help="cited answers for one retrieval run through Claude Code; resumes an earlier run")
    command.add_argument("retrieval_run", help="run directory written by run-retrieval")
    command.add_argument("--questions", required=True, help="the question file the retrieval run used")
    command.add_argument("--config", default="configs/experiments/answer.json")
    command.add_argument("--output", required=True, help="new directory, or an earlier answer run with the same inputs")
    command.add_argument("--split", choices=["dev", "held_out"], help="answer only this split")
    command.add_argument("--max-calls", type=int, required=True, help="call budget of this session")
    command.add_argument("--approve-claude", action="store_true", help="explicit approval of the model calls")
    command.add_argument("--router-model", help="answer with one approved 9Router model instead of the config's Claude model (a MODEL_* alias or a name)")
    command.add_argument("--approve-router", action="store_true", help="explicit approval of the 9Router calls")
    command.add_argument("--timeout", type=int, default=300, help="seconds per 9Router call")
    command.add_argument("--max-tokens", type=int, default=8000, help="answer token limit for 9Router models")
    command = commands.add_parser("kb-relations", help="typed relations between articles (exception, procedure, consequence, condition, detail) for the KB graph; resumes")
    command.add_argument("bundle", help="contract bundle written by corpus-export")
    command.add_argument("--output", required=True, help="new directory, or an earlier relation run of the same bundle")
    command.add_argument("--sample", type=int, help="only a seeded sample of this many articles")
    command.add_argument("--max-calls", type=int, help="call budget of this session (required unless --materialize)")
    command.add_argument("--router-model", help="one approved 9Router model (a MODEL_* alias or a name)")
    command.add_argument("--approve-router", action="store_true", help="explicit approval of the 9Router calls")
    command.add_argument("--timeout", type=int, default=300)
    command.add_argument("--max-tokens", type=int, default=8000)
    command.add_argument("--claude-model", help="extract through the local claude CLI instead, e.g. claude-sonnet-5-5")
    command.add_argument("--claude-effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    command.add_argument("--approve-claude", action="store_true", help="explicit approval of the Claude Code calls")
    command.add_argument("--workers", type=int, default=1, help="calls at once (Claude Code calls spend most of their time starting up)")
    command.add_argument("--dense-candidates", type=int, default=0, help="add this many nearest articles by the local embedding model (shared.json)")
    command.add_argument("--candidate-chars", type=int, default=900, help="characters of each candidate article shown to the model")
    command.add_argument("--materialize", action="store_true", help="only validate raw.jsonl again; offline")
    command = commands.add_parser("neighbor-select", help="a model picks which legal-chain graph neighbours each question needs; resumes, then writes a retrieval run")
    command.add_argument("retrieval_run", help="base run directory written by run-retrieval (DK3/DK4 without graph expansion)")
    command.add_argument("--relation-run", required=True, help="relation run whose typed relations form the graph")
    command.add_argument("--output", required=True, help="new directory, or an earlier selection run with the same inputs")
    command.add_argument("--model", default="claude-haiku-5-5")
    command.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    command.add_argument("--max-calls", type=int, default=0, help="call budget of this session (required unless --dry-run or --materialize)")
    command.add_argument("--approve-claude", action="store_true", help="explicit approval of the Claude Code calls")
    command.add_argument("--workers", type=int, default=1, help="calls at once")
    command.add_argument("--dry-run", action="store_true", help="only count calls, candidates and characters; no model call")
    command.add_argument("--materialize", action="store_true", help="only rebuild run/ from raw.jsonl; offline")
    command.add_argument("--grouping", default="question", choices=["question", "issue"], help="issue: seeds, candidates and caps per decomposed issue (v2)")
    command = commands.add_parser("decompose-questions", help="split each question into legal issues with search queries, once for every condition; resumes")
    command.add_argument("questions", help="question file")
    command.add_argument("--output", required=True, help="new directory, or an earlier decomposition run of the same file")
    command.add_argument("--max-calls", type=int, required=True, help="call budget of this session")
    command.add_argument("--router-model", help="one approved 9Router model (a MODEL_* alias or a name)")
    command.add_argument("--approve-router", action="store_true", help="explicit approval of the 9Router calls")
    command.add_argument("--timeout", type=int, default=300, help="seconds per 9Router call")
    command.add_argument("--max-tokens", type=int, default=4000)
    command.add_argument("--claude-model", help="decompose through the local claude CLI instead, e.g. claude-sonnet-5-5")
    command.add_argument("--claude-effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    command.add_argument("--approve-claude", action="store_true", help="explicit approval of the Claude Code calls")
    command = commands.add_parser("query-slots", help="norm-query-v1: modality, actor, required slots and topic query of each enumeration question, once for every condition; resumes")
    command.add_argument("questions", help="question file")
    command.add_argument("--output", required=True, help="new directory, or an earlier analysis run of the same file")
    command.add_argument("--max-calls", type=int, required=True, help="call budget of this session")
    command.add_argument("--router-model", help="one approved 9Router model (a MODEL_* alias or a name)")
    command.add_argument("--approve-router", action="store_true", help="explicit approval of the 9Router calls")
    command.add_argument("--timeout", type=int, default=300, help="seconds per 9Router call")
    command.add_argument("--max-tokens", type=int, default=2000)
    command.add_argument("--claude-model", help="analyze through the local claude CLI instead")
    command.add_argument("--claude-effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    command.add_argument("--approve-claude", action="store_true", help="explicit approval of the Claude Code calls")
    command = commands.add_parser("enum-drafts", help="draft enumeration questions and a check sheet from an adjudicated extraction gold file; offline")
    command.add_argument("gold", help="adjudicated gold JSONL (extraction-gold-v1)")
    command.add_argument("--bundle", required=True, help="contract bundle the gold was labelled on")
    command.add_argument("--aliases", default="configs/experiments/actor-aliases.json")
    command.add_argument("--level", default="article", choices=["article", "chapter"], help="topic scope of a question")
    command.add_argument("--min-units", type=int, default=2)
    command.add_argument("--output", required=True, help="new question file (JSON); the check sheet is written next to it as .csv")
    command = commands.add_parser("enum-gate", help="extraction coverage of the gold answer units of an enumeration set by a knowledge-base run (WP5 gate); offline")
    command.add_argument("questions", help="enumeration question file")
    command.add_argument("--kb-run", required=True, help="knowledge-base run directory")
    command.add_argument("--claims", default="dk3.jsonl", choices=["dk3.jsonl", "dk4.jsonl"])
    command = commands.add_parser("answer-score", help="automatic metrics of an answer run (refusals, citations against gold units); offline")
    command.add_argument("answer_run")
    command.add_argument("--questions", required=True)
    command = commands.add_parser("answer-sheet", help="blinded CSV grading sheet pooling several answer runs, and its separate key; offline")
    command.add_argument("answer_runs", nargs="+")
    command.add_argument("--questions", required=True)
    command.add_argument("--sheet", required=True, help="CSV file to write")
    command.add_argument("--key", required=True, help="JSON key file to write; keep it away from graders")
    command = commands.add_parser("answer-grades", help="per-condition scores of a filled grading sheet; offline")
    command.add_argument("sheet")
    command.add_argument("--key", required=True)
    command.add_argument("--compare", help="a second filled sheet of the same items: report Cohen's kappa")
    command = commands.add_parser("answer-judge", help="fill a copy of a grading sheet with a Claude Code judge (supplement to people)")
    command.add_argument("sheet")
    command.add_argument("--output", required=True, help="CSV file to write")
    command.add_argument("--config", default="configs/experiments/answer.json")
    command.add_argument("--max-calls", type=int, required=True)
    command.add_argument("--approve-claude", action="store_true")
    command = commands.add_parser("answer-outcome-judge", help="Claude Code judge of case answers against the real outcome and issues (supplement to people); resumes")
    command.add_argument("sheet", help="blinded sheet from answer-sheet")
    command.add_argument("--key", required=True)
    command.add_argument("--questions", required=True, help="question file whose questions carry issues and reference_outcome")
    command.add_argument("--output", required=True, help="new directory, or an earlier judge run of the same inputs")
    command.add_argument("--model", required=True, help="judge model, e.g. claude-sonnet-5-5")
    command.add_argument("--effort", default="medium")
    command.add_argument("--workers", type=int, default=1)
    command.add_argument("--max-calls", type=int, required=True)
    command.add_argument("--approve-claude", action="store_true")
    command = commands.add_parser("answer-outcome-score", help="per-model, per-condition scores and paired differences of an outcome judge run; offline")
    command.add_argument("judge_run")
    command.add_argument("--sheet", required=True)
    command.add_argument("--key", required=True)
    command = commands.add_parser("paired-stats", help="paired bootstrap with Holm correction, and generation/grading noise, of a per-question metric across labelled runs; offline")
    command.add_argument("--metric", required=True, help="retrieval.recall@10, retrieval.recall_at_tokens@3000, answer.citation_gold_char_precision, grades.correctness, judge.correctness, ...")
    command.add_argument("--runs", nargs="+", required=True, metavar="LABEL=DIR", help="retrieval or answer run per label, e.g. DK1=<dir> DK2=<dir>")
    command.add_argument("--pairs", nargs="+", default=["DK1:DK2", "DK2:DK3", "DK3:DK4", "DK1:DK4"], metavar="A:B", help="Holm family (default the four main comparisons); difference = B minus A")
    command.add_argument("--exploratory", nargs="*", default=[], metavar="A:B", help="further pairs reported with raw p only")
    command.add_argument("--repeat", nargs="*", default=[], metavar="LABEL=DIR", help="second generation run of a label (graded the same way): generation noise")
    command.add_argument("--regrade", help="second grading of the same answers: an outcome judge run (judge.*) or a filled sheet of the same key (grades.*)")
    command.add_argument("--questions", help="question file (answer.* metrics)")
    command.add_argument("--sheet", help="grading sheet (grades.*: the filled sheet; judge.*: the sheet the judge read)")
    command.add_argument("--key", help="key of the grading sheet")
    command.add_argument("--judge", help="outcome judge run (judge.* metrics)")
    command.add_argument("--rounds", type=int, default=10000)
    command.add_argument("--seed", default="lexora-paired-v1")
    command.add_argument("--output", required=True, help="new JSON report file")
    command = commands.add_parser("demo-build", help="new demo store: three accounts with printed random passwords and the frozen experiment-scope corpus; offline")
    command.add_argument("--store", required=True, help="new SQLite file")
    command.add_argument("--scope", default="configs/experiment-scope-v1.json")
    command = commands.add_parser("preflight", help="fairness checks of DK1-DK4 retrieval (and answer) runs before reporting RQ3; offline")
    command.add_argument("--retrieval", nargs="+", required=True, help="retrieval run directories, one per condition")
    command.add_argument("--answers", nargs="*", default=[], help="answer run directories made from those retrieval runs")
    command.add_argument("--output", help="write the report as JSON here")
    command = commands.add_parser("kb-compare", help="re-validate knowledge-base runs with the current validator and write a side-by-side report; offline")
    command.add_argument("runs", nargs="*", help="run directories (default: every knowledge-base run under experiments/runs)")
    command.add_argument("--json", default="docs/results/extraction-models.json")
    command.add_argument("--markdown", default="docs/results/extraction-models.md")
    command = commands.add_parser("kb-inject", help="RQ2: plant errors of each type in DK4 claims and measure what the validator catches; offline")
    command.add_argument("run", help="knowledge-base run directory")
    command.add_argument("--output", required=True, help="new, empty directory")
    command.add_argument("--per-type", type=int, default=30)
    command.add_argument("--seed", default="lexora-inject-v1")
    command.add_argument("--validator", default="kb-validator-v3", choices=["kb-validator-v3", "kb-validator-v4"],
                         help="validator applied to the corrupted and clean claims; kb-validator-v4 also accepts values quoted from the parent's lead-in")
    command.add_argument("--inherit", choices=["claims-inherit-v1"],
                         help="after putting the errors in, fill empty actor, action or outcome slots from the lead-in, then validate (needs kb-validator-v4)")
    command = commands.add_parser("kb-plant", help="stress test: a copy of a knowledge-base run with visible errors planted in the claims of the questions' gold units; DK4 re-validated; offline")
    command.add_argument("run", help="knowledge-base run directory")
    command.add_argument("--questions", required=True, help="question file; its relevant_unit_ids are the targets")
    command.add_argument("--output", required=True, help="new, empty directory")
    command.add_argument("--seed", default="lexora-plant-v1")
    command.add_argument("--validator", default="kb-validator-v3", choices=["kb-validator-v3", "kb-validator-v4"],
                         help="validator applied to the corrupted and clean claims; kb-validator-v4 also accepts values quoted from the parent's lead-in")
    command.add_argument("--inherit", choices=["claims-inherit-v1"],
                         help="after putting the errors in, fill empty actor, action or outcome slots from the lead-in, then validate (needs kb-validator-v4)")
    command = commands.add_parser("question-drafts", help="add model-drafted questions with proposed labels to a question set (new or existing); offline")
    command.add_argument("drafts", nargs="+", help="JSON files, each a list of drafted questions")
    command.add_argument("--store", required=True)
    command.add_argument("--actor", required=True, help="account recorded as the one who added the drafts")
    command.add_argument("--author", required=True, help="who drafted them, e.g. claude-opus-5-5 (agent session)")
    group = command.add_mutually_exclusive_group(required=True)
    group.add_argument("--set", help="existing question set ID")
    group.add_argument("--version", help="frozen corpus version ID for a new set (with --name and --guideline)")
    command.add_argument("--name")
    command.add_argument("--guideline", help="labelling guideline file for a new set")
    command = commands.add_parser("kb-audit-sheet", help="blinded CSV sample of rejected and accepted claims for people to label against the statute; offline")
    command.add_argument("runs", nargs="+", help="knowledge-base run directories")
    command.add_argument("--sheet", required=True, help="CSV file to write")
    command.add_argument("--key", required=True, help="JSON key file to write; keep it away from annotators")
    command.add_argument("--rejected", type=int, default=30, help="rejected claims per run")
    command.add_argument("--accepted", type=int, default=10, help="accepted claims per run")
    command.add_argument("--seed", default="lexora-rejection-audit-v1")
    command = commands.add_parser("kb-audit-import", help="put an audit sheet and its key into a workspace store so annotators label it in the app; offline")
    command.add_argument("sheet")
    command.add_argument("--key", required=True)
    command.add_argument("--store", required=True)
    command.add_argument("--name", required=True)
    command.add_argument("--actor", required=True)
    command = commands.add_parser("kb-audit-score", help="share of wrong claims among rejected and accepted ones in a labelled audit sheet; offline")
    command.add_argument("sheet")
    command.add_argument("--key", required=True)
    command.add_argument("--compare", help="a second annotator's sheet of the same items: report Cohen's kappa")
    command = commands.add_parser("gold-template", help="RQ1: empty extraction gold rows for every sentence of the chosen articles; offline")
    command.add_argument("bundle")
    command.add_argument("--output", required=True, help="JSONL file to write")
    group = command.add_mutually_exclusive_group(required=True)
    group.add_argument("--article", action="append", help="article unit ID, e.g. 45-2019-qh14/chapter-iii/section-1/article-24 (repeatable)")
    group.add_argument("--sample", type=int, help="seeded sample of this many articles, spread over documents")
    command.add_argument("--seed", default="lexora-gold-v1")
    command = commands.add_parser("gold-check", help="RQ1: check a filled gold file (exact quotes, offsets); offline")
    command.add_argument("gold")
    command.add_argument("--bundle", required=True)
    command = commands.add_parser("gold-agreement", help="RQ1: agreement of two annotators on the same gold template; offline")
    command.add_argument("first")
    command.add_argument("second")
    command = commands.add_parser("gold-score", help="RQ1: P/R/F1 of the rule baseline or a knowledge-base run against the gold file; offline")
    command.add_argument("gold")
    command.add_argument("--bundle", required=True)
    command.add_argument("--predictions", required=True, help="'rules', or a dk3.jsonl / dk4.jsonl of a knowledge-base run")
    command.add_argument("--inherited", default="score", choices=["score", "ignore"],
                         help="gold-inherited-v1: 'score' (default) scores slots inherited from the lead-in as they are, "
                              "'ignore' leaves them out (the gold guideline leaves lead-in values empty)")
    command = commands.add_parser("run-retrieval", help="DK1/DK2 retrieval run with Recall@K into a new run directory; no network")
    command.add_argument("bundle")
    command.add_argument("--condition", required=True, help="configs/experiments/dk1.json or dk2.json")
    command.add_argument("--questions", default="tests/fixtures/pilot-questions.json")
    command.add_argument("--shared", default="configs/pilot.json")
    command.add_argument("--output", required=True, help="new, empty directory, e.g. experiments/runs/<run-id>")
    command = commands.add_parser("graph-build", help="build a local knowledge graph and evidence viewer")
    command.add_argument("bundle")
    command.add_argument("--output", required=True)
    command.add_argument("--config", default="configs/knowledge-graph.json")
    args = parser.parse_args()
    try:
        if args.command == "snapshot":
            print(json.dumps(snapshot(args.url, args.output, args.document_id, args.marker), ensure_ascii=False, indent=2))
        elif args.command == "build-pilot":
            from legal_ai.ingestion.pilot import build_pilot
            print(json.dumps(build_pilot(args.config, args.raw_root, args.output), ensure_ascii=False, indent=2))
        elif args.command == "catalog-build":
            from legal_ai.ingestion.catalog import build_catalog
            print(json.dumps(build_catalog(args.raw, args.output), ensure_ascii=False, indent=2))
        elif args.command == "catalog-search":
            from legal_ai.ingestion.catalog import Catalog
            print(json.dumps(Catalog(args.catalog).search(args.query, args.limit, args.include_translations), ensure_ascii=False, indent=2))
        elif args.command == "vbpl-fetch":
            from legal_ai.ingestion.vbpl_api import fetch_document
            print(json.dumps(fetch_document(args.reference, args.output), ensure_ascii=False, indent=2))
        elif args.command == "corpus-export":
            from legal_ai.research.corpus import CorpusStore
            print(json.dumps(CorpusStore(args.store).export_version(args.version, args.output), ensure_ascii=False, indent=2))
        elif args.command == "corpus-version-export":
            from legal_ai.research.corpus import CorpusStore
            output = Path(args.output)
            if output.exists():
                raise ValueError("output file exists: use a new file name")
            body = CorpusStore(args.store).version_file(args.version)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
            manifest = body["payload"]["version"]["manifest"]
            print(json.dumps({"output": output.as_posix(), "version_id": body["version_id"], "bundle_sha256": body["bundle_sha256"],
                              "documents": len(manifest["documents"]), "units": manifest["unit_count"]}, ensure_ascii=False, indent=2))
        elif args.command == "corpus-version-import":
            from legal_ai.research.corpus import CorpusStore
            body = json.loads(Path(args.file).read_text(encoding="utf-8"))
            print(json.dumps(CorpusStore(args.store).import_version_file(body, args.actor, args.expect_version), ensure_ascii=False, indent=2))
        elif args.command == "corpus-scope":
            from legal_ai.research.corpus import CorpusStore
            from legal_ai.research.scope import build_scope
            corpus = build_scope(CorpusStore(args.store), args.config, args.actor)
            print(json.dumps({"corpus_id": corpus["id"], "name": corpus["name"],
                              "documents": [{"document_id": d["document_id"], "articles": d["article_count"], "audit": d["audit_count"]} for d in corpus["documents"]]},
                             ensure_ascii=False, indent=2))
        elif args.command == "amendment-build":
            from legal_ai.kb.amendments import build
            print(json.dumps(build(args.bundle, args.config, args.output), ensure_ascii=False, indent=2))
        elif args.command in ("amendment-sheet", "amendment-score"):
            from legal_ai.kb import amendment_check
            if args.command == "amendment-sheet":
                report = amendment_check.make_sheet(args.edges, args.sheet, args.bundle)
            else:
                report = amendment_check.score_sheet(args.sheet)
                if args.compare:
                    report["agreement"] = amendment_check.agreement(args.sheet, args.compare)
            print(json.dumps(report, ensure_ascii=False, indent=2))
        elif args.command == "budget-report":
            from legal_ai.evaluation.budget_report import write_report
            print(json.dumps(write_report(args.runs, args.output, args.title, args.set_title), ensure_ascii=False, indent=2))
        elif args.command in ("kb-extract", "kb-materialize"):
            from legal_ai.evaluation import kb_run
            if args.command == "kb-materialize":
                bundle = args.bundle or json.loads((Path(args.run) / "manifest.json").read_text(encoding="utf-8"))["bundle"]
                units = read_jsonl(Path(bundle) / "units.jsonl")
                if args.output:
                    report = kb_run.materialize(units, args.output, source=args.run, validator=args.validator, inheritance=args.inherit)
                else:
                    report = kb_run.materialize(units, args.run, validator=args.validator, inheritance=args.inherit)
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                units = read_jsonl(Path(args.bundle) / "units.jsonl")
                if args.dry_run:
                    print(json.dumps(kb_run.estimate(units), ensure_ascii=False, indent=2))
                else:
                    if args.max_calls < 1:
                        raise ValueError("--max-calls must be a positive call budget")
                    if args.router_model:
                        from legal_ai.providers.router import RouterProvider, read_settings
                        settings = read_settings(Path.cwd() / ".env")
                        name = settings[args.router_model] if args.router_model.startswith("MODEL_") and settings.get(args.router_model) else args.router_model
                        provider = RouterProvider(settings, model=name, approved_route=args.approve_router, max_calls=args.max_calls, timeout=args.timeout)
                        kb_run.start(args.bundle, args.output, name, "temperature-0", provider="9router", max_tokens=args.max_tokens)
                    else:
                        from legal_ai.providers.claude_code import ClaudeCodeProvider
                        provider = ClaudeCodeProvider(args.model, args.effort, args.max_calls, approved=args.approve_claude)
                        kb_run.start(args.bundle, args.output, args.model, args.effort)
                    counts = kb_run.extract(units, provider, args.output, log=lambda line: print(line, flush=True), max_tokens=args.max_tokens)
                    print(json.dumps({"calls": counts, "report": kb_run.materialize(units, args.output)}, ensure_ascii=False, indent=2))
        elif args.command == "kb-keys-gen":
            from legal_ai.evaluation import keys_run
            head, summary, planned, system = keys_run.plan(args.bundle, args.kb_run, sources=args.units_from, top_n=args.top_n, split=args.split,
                                                           batch_size=args.batch_size)
            if args.dry_run:  # No provider is built: nothing can reach a model.
                output = Path(args.output)
                if output.exists() and any(output.iterdir()):
                    raise ValueError("output must be a new, empty directory")
                if args.reuse and not args.extract_claude_model:
                    parser.error("--reuse needs --extract-claude-model to check the earlier runs' model")
                expected = head | {"provider": "claude-code", "model": args.extract_claude_model, "effort": args.effort}
                reused = {row["key"] for row in keys_run.reusable(planned, args.reuse, expected)}
                summary["batches_reusable"] = len(reused)
                body = keys_run.write_plan(output, expected | {"dry_run": True}, summary, planned, system)
                print(json.dumps({"output": output.as_posix(), "scope": body["scope"], "summary": summary}, ensure_ascii=False, indent=2))
            else:
                if args.max_calls < 1 or not args.extract_claude_model:
                    parser.error("kb-keys-gen needs --extract-claude-model, --max-calls and --approve-claude unless --dry-run")
                from legal_ai.providers.claude_code import ClaudeCodeProvider
                provider = ClaudeCodeProvider(args.extract_claude_model, args.effort, args.max_calls, approved=args.approve_claude)
                keys_run.start(args.output, head, args.extract_claude_model, args.effort)
                keys_run.write_plan(args.output, head, summary, planned, system)
                copied = keys_run.reuse(planned, args.output, args.reuse)
                counts = keys_run.generate(planned, system, provider, args.output, log=lambda line: print(line, flush=True))
                print(json.dumps({"reused": copied, "calls": counts, "usage": keys_run.materialize(args.output)}, ensure_ascii=False, indent=2))
        elif args.command in ("answer-run", "answer-judge"):
            from legal_ai.providers.claude_code import ClaudeCodeProvider
            config = json.loads(Path(args.config).read_text(encoding="utf-8"))
            log = lambda line: print(line, flush=True)
            if args.command == "answer-run":
                from legal_ai.evaluation.answer_run import run as answer_run
                if args.router_model:
                    from legal_ai.providers.router import ChatStructured, RouterProvider, read_settings
                    settings = read_settings(Path.cwd() / ".env")
                    name = settings.get(args.router_model, args.router_model) if args.router_model.startswith("MODEL_") else args.router_model
                    chat = RouterProvider(settings, model=name, approved_route=args.approve_router, max_calls=args.max_calls, timeout=args.timeout)
                    provider = ChatStructured(chat, max_tokens=args.max_tokens)
                else:
                    provider = ClaudeCodeProvider(config["model"], config["effort"], args.max_calls, approved=args.approve_claude)
                print(json.dumps(answer_run(args.retrieval_run, args.questions, args.config, provider, args.output, split=args.split, log=log), indent=2))
            else:
                from legal_ai.evaluation.answer_grading import judge_sheet
                provider = ClaudeCodeProvider(config["judge_model"], config["judge_effort"], args.max_calls, approved=args.approve_claude)
                print(json.dumps(judge_sheet(args.sheet, provider, args.output, log=log), indent=2))
        elif args.command == "neighbor-select":
            from legal_ai.evaluation import neighbor_select
            neighbor_select.start(args.retrieval_run, args.relation_run, args.output, args.model, args.effort, grouping=args.grouping)
            if args.dry_run:
                print(json.dumps(neighbor_select.estimate(args.output), ensure_ascii=False, indent=2))
            else:
                if not args.materialize:
                    if args.max_calls < 1:
                        parser.error("neighbor-select needs --max-calls (and --approve-claude) unless --dry-run or --materialize")
                    from legal_ai.providers.claude_code import ClaudeCodeProvider
                    provider = ClaudeCodeProvider(args.model, args.effort, args.max_calls, approved=args.approve_claude)
                    print(json.dumps(neighbor_select.select(args.output, provider, log=lambda line: print(line, flush=True), workers=args.workers)))
                print(json.dumps(neighbor_select.materialize(args.output), ensure_ascii=False, indent=2))
        elif args.command == "kb-relations":
            from legal_ai.evaluation import relation_run
            units = read_jsonl(Path(args.bundle) / "units.jsonl")
            aliases = {"Bộ luật Lao động": "45-2019-qh14"}
            embedder, embedding = None, None
            if args.dense_candidates:
                from legal_ai.retrieval.embeddings import LocalEmbedder
                model = json.loads(Path("configs/experiments/shared.json").read_text(encoding="utf-8"))["embedding_model"]
                embedder = LocalEmbedder(model["path"], model["name"], model["revision"], 512, cache=model.get("cache"))
                embedding = {"model": model["name"], "revision": model["revision"], "max_seq_length": 512}
            if not args.materialize:
                if not args.max_calls or bool(args.router_model) == bool(args.claude_model):
                    parser.error("kb-relations needs --max-calls and one of --router-model (with --approve-router) or --claude-model (with --approve-claude)")
                if args.claude_model:
                    from legal_ai.providers.claude_code import ClaudeCodeProvider
                    provider = ClaudeCodeProvider(args.claude_model, args.claude_effort, args.max_calls, approved=args.approve_claude)
                    relation_run.start(args.bundle, args.output, args.claude_model, "claude-code", args.sample, args.dense_candidates, args.candidate_chars, embedding)
                else:
                    from legal_ai.providers.router import ChatStructured, RouterProvider, read_settings
                    settings = read_settings(Path.cwd() / ".env")
                    name = settings.get(args.router_model, args.router_model) if args.router_model.startswith("MODEL_") else args.router_model
                    chat = RouterProvider(settings, model=name, approved_route=args.approve_router, max_calls=args.max_calls, timeout=args.timeout)
                    provider = ChatStructured(chat, max_tokens=args.max_tokens)
                    relation_run.start(args.bundle, args.output, name, "9router", args.sample, args.dense_candidates, args.candidate_chars, embedding)
                counts = relation_run.extract(units, provider, args.output, aliases, log=lambda line: print(line, flush=True), workers=args.workers,
                                              embedder=embedder)
                print(json.dumps(counts, indent=2))
            print(json.dumps(relation_run.materialize(units, args.output), ensure_ascii=False, indent=2))
        elif args.command == "decompose-questions":
            from legal_ai.evaluation.decompose import run as decompose_run
            if bool(args.router_model) == bool(args.claude_model):
                parser.error("decompose-questions needs one of --router-model (with --approve-router) or --claude-model (with --approve-claude)")
            if args.claude_model:
                from legal_ai.providers.claude_code import ClaudeCodeProvider
                provider = ClaudeCodeProvider(args.claude_model, args.claude_effort, args.max_calls, approved=args.approve_claude)
            else:
                from legal_ai.providers.router import ChatStructured, RouterProvider, read_settings
                settings = read_settings(Path.cwd() / ".env")
                name = settings.get(args.router_model, args.router_model) if args.router_model.startswith("MODEL_") else args.router_model
                chat = RouterProvider(settings, model=name, approved_route=args.approve_router, max_calls=args.max_calls, timeout=args.timeout)
                provider = ChatStructured(chat, max_tokens=args.max_tokens)
            counts = decompose_run(args.questions, provider, args.output, log=lambda line: print(line, flush=True))
            print(json.dumps(counts, indent=2))
        elif args.command == "query-slots":
            from legal_ai.retrieval.norm_query import analyze
            if bool(args.router_model) == bool(args.claude_model):
                parser.error("query-slots needs one of --router-model (with --approve-router) or --claude-model (with --approve-claude)")
            if args.claude_model:
                from legal_ai.providers.claude_code import ClaudeCodeProvider
                provider = ClaudeCodeProvider(args.claude_model, args.claude_effort, args.max_calls, approved=args.approve_claude)
            else:
                from legal_ai.providers.router import ChatStructured, RouterProvider, read_settings
                settings = read_settings(Path.cwd() / ".env")
                name = settings.get(args.router_model, args.router_model) if args.router_model.startswith("MODEL_") else args.router_model
                chat = RouterProvider(settings, model=name, approved_route=args.approve_router, max_calls=args.max_calls, timeout=args.timeout)
                provider = ChatStructured(chat, max_tokens=args.max_tokens)
            print(json.dumps(analyze(args.questions, provider, args.output, log=lambda line: print(line, flush=True)), indent=2))
        elif args.command == "enum-drafts":
            from legal_ai.research.enumeration import DRAFT_VERSION, check_sheet, drafts
            from legal_ai.retrieval.norm_query import load_aliases
            output = Path(args.output)
            if output.exists():
                parser.error("output exists: use a new question file")
            gold, bundle = read_jsonl(args.gold), Path(args.bundle)
            units, documents = read_jsonl(bundle / "units.jsonl"), read_jsonl(bundle / "documents.jsonl")
            rows = drafts(gold, units, documents, load_aliases(args.aliases), args.level, args.min_units)
            write_json(output, {"description": f"Enumeration drafts ({DRAFT_VERSION}) from {Path(args.gold).as_posix()}, scope {args.level}; "
                                               "annotators rewrite and check every question before freezing", "questions": rows})
            check_sheet(output.with_suffix(".csv"), rows, gold, units)
            print(json.dumps({"questions": len(rows), "answer_units": sum(len(r["relevant_unit_ids"]) for r in rows),
                              "sheet": output.with_suffix(".csv").as_posix()}, ensure_ascii=False, indent=2))
        elif args.command == "enum-gate":
            from legal_ai.retrieval.norm_query import coverage
            questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))["questions"]
            result = coverage(questions, read_jsonl(Path(args.kb_run) / args.claims))
            print(json.dumps(result | {"uncovered": result["uncovered"][:50]}, ensure_ascii=False, indent=2))
        elif args.command == "answer-score":
            from legal_ai.evaluation.answer_run import score
            print(json.dumps(score(args.answer_run, args.questions), ensure_ascii=False, indent=2))
        elif args.command == "answer-sheet":
            from legal_ai.evaluation.answer_grading import make_sheet
            print(json.dumps(make_sheet(args.answer_runs, args.questions, args.sheet, args.key), indent=2))
        elif args.command == "answer-grades":
            from legal_ai.evaluation.answer_grading import agreement, score_sheet
            report = score_sheet(args.sheet, args.key)
            if args.compare:
                report["agreement"] = agreement(args.sheet, args.compare, args.key)
            print(json.dumps(report, ensure_ascii=False, indent=2))
        elif args.command == "answer-outcome-judge":
            from legal_ai.evaluation.outcome_judge import judge as outcome_judge
            from legal_ai.providers.claude_code import ClaudeCodeProvider
            provider = ClaudeCodeProvider(args.model, args.effort, args.max_calls, approved=args.approve_claude)
            print(json.dumps(outcome_judge(args.sheet, args.key, args.questions, provider, args.output, workers=args.workers,
                                           log=lambda line: print(line, flush=True)), indent=2))
        elif args.command == "answer-outcome-score":
            from legal_ai.evaluation.outcome_judge import score as outcome_score
            print(json.dumps(outcome_score(args.judge_run, args.sheet, args.key), ensure_ascii=False, indent=2))
        elif args.command == "paired-stats":
            from legal_ai.evaluation import stats
            if Path(args.output).exists():
                raise ValueError(f"{args.output} exists; write the report to a new file")
            report = stats.compare_runs(args.metric, stats.labelled(args.runs), stats.parse_pairs(args.pairs), stats.parse_pairs(args.exploratory),
                                        stats.labelled(args.repeat), args.regrade, args.questions, args.sheet, args.key, args.judge, args.rounds, args.seed)
            write_json(args.output, report)
            print(stats.table(report))
            print(f"\nreport: {Path(args.output).as_posix()}")
        elif args.command == "demo-build":
            from legal_ai.demo_setup import build as demo_build
            result = demo_build(args.store, args.scope)
            print(f"Demo store: {result['store']}")
            print(f"Corpus: {result['corpus']['name']} ({result['corpus']['documents']} documents), frozen version {result['version']['number']} ({result['version']['id']})")
            print("Accounts (passwords are shown only now; note them down):")
            for username, role, password in result["accounts"]:
                print(f"  {username:8} {role:9} {password}")
        elif args.command == "preflight":
            from legal_ai.evaluation.preflight import check
            report = check(args.retrieval, args.answers)
            if args.output:
                write_json(args.output, report)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            if report["status"] == "fail":
                return 1
        elif args.command == "kb-compare":
            from legal_ai.evaluation.kb_compare import compare, kb_runs
            runs = args.runs or kb_runs("experiments/runs")
            summaries = compare(runs, args.json, args.markdown)
            print(json.dumps([{k: s[k] for k in ("model", "batches_ok", "batches_attempted", "dk3_claims", "dk4_claims", "rejected")} for s in summaries],
                             ensure_ascii=False, indent=2))
        elif args.command == "kb-inject":
            from legal_ai.evaluation.error_injection import run as inject_run
            bundle = json.loads((Path(args.run) / "manifest.json").read_text(encoding="utf-8"))["bundle"]
            print(json.dumps(inject_run(args.run, read_jsonl(Path(bundle) / "units.jsonl"), args.output, args.per_type, args.seed,
                                        validator=args.validator, inheritance=args.inherit), ensure_ascii=False, indent=2))
        elif args.command == "kb-plant":
            from legal_ai.evaluation.error_injection import plant
            bundle = json.loads((Path(args.run) / "manifest.json").read_text(encoding="utf-8"))["bundle"]
            questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))["questions"]
            targets = {u for q in questions for u in q.get("relevant_unit_ids") or []}
            print(json.dumps(plant(args.run, read_jsonl(Path(bundle) / "units.jsonl"), args.output, targets, args.seed,
                                   validator=args.validator, inheritance=args.inherit), ensure_ascii=False, indent=2))
        elif args.command == "question-drafts":
            from legal_ai.research.corpus import CorpusStore
            from legal_ai.research.questions import QuestionStore
            store = QuestionStore(args.store, CorpusStore(args.store))
            set_id = args.set
            if set_id is None:
                if not args.name:
                    raise ValueError("a new set needs --name")
                guideline = Path(args.guideline).read_text(encoding="utf-8") if args.guideline else ""
                set_id = store.create(args.name, args.version, guideline, args.actor)["id"]
            items = []
            for path in args.drafts:
                batch = json.loads(Path(path).read_text(encoding="utf-8"))
                offset = len(items)  # paraphrase_of is local to each file.
                items += [item | {"batch": Path(path).stem, "paraphrase_of": None if item.get("paraphrase_of") is None else item["paraphrase_of"] + offset}
                          for item in batch]
            print(json.dumps({"set_id": set_id} | store.import_drafts(set_id, items, args.actor, args.author), ensure_ascii=False, indent=2))
        elif args.command == "kb-audit-sheet":
            from legal_ai.evaluation.rejection_audit import make_sheet as audit_sheet
            print(json.dumps(audit_sheet(args.runs, args.sheet, args.key, args.rejected, args.accepted, args.seed), indent=2))
        elif args.command == "kb-audit-import":
            from legal_ai.research.audit import AuditStore
            print(json.dumps(AuditStore(args.store).import_files(args.name, args.sheet, args.key, args.actor), ensure_ascii=False, indent=2))
        elif args.command == "kb-audit-score":
            from legal_ai.evaluation.rejection_audit import agreement as audit_agreement, score_sheet as audit_score
            report = audit_score(args.sheet, args.key)
            if args.compare:
                report["agreement"] = audit_agreement(args.sheet, args.compare)
            print(json.dumps(report, ensure_ascii=False, indent=2))
        elif args.command.startswith("gold-"):
            from legal_ai.evaluation import extraction_gold as gold
            if args.command == "gold-agreement":
                print(json.dumps(gold.agreement(read_jsonl(args.first), read_jsonl(args.second)), ensure_ascii=False, indent=2))
            else:
                units = read_jsonl(Path(args.bundle) / "units.jsonl")
                if args.command == "gold-template":
                    articles = args.article or gold.sample_articles(units, args.sample, args.seed)
                    rows = gold.template(units, articles)
                    write_jsonl(args.output, rows)
                    print(json.dumps({"articles": articles, "sentences": len(rows)}, ensure_ascii=False, indent=2))
                else:
                    rows = read_jsonl(args.gold)
                    problems = gold.check(rows, units)
                    if args.command == "gold-check" or problems:
                        print(json.dumps({"rows": len(rows), "problems": problems}, ensure_ascii=False, indent=2))
                        if problems:
                            raise ValueError(f"{len(problems)} problems in the gold file")
                    else:
                        if args.predictions == "rules":
                            report = gold.score(rows, gold.rule_predictions(units, rows))
                        else:
                            report = gold.score_claims(rows, read_jsonl(args.predictions), units, args.inherited)
                        print(json.dumps(report, ensure_ascii=False, indent=2))
        elif args.command == "run-retrieval":
            from legal_ai.evaluation.retrieval_run import run
            shared = json.loads(Path(args.shared).read_text(encoding="utf-8"))
            embedder = None
            if shared["retrieval"].get("method") in ("dense", "hybrid"):
                from legal_ai.retrieval.embeddings import LocalEmbedder
                model = shared["embedding_model"]
                embedder = LocalEmbedder(model["path"], model["name"], model["revision"], model.get("max_seq_length", 1024), cache=model.get("cache"))
            print(json.dumps(run(args.bundle, args.questions, args.condition, args.shared, args.output, embedder), ensure_ascii=False, indent=2))
        elif args.command == "graph-build":
            from legal_ai.kb.graph import GRAPH_VERSION, build_graph
            config = json.loads(Path(args.config).read_text(encoding="utf-8"))
            if config.get("graph_version") != GRAPH_VERSION:
                raise ValueError("graph config version does not match runtime; review migration before rebuilding")
            print(json.dumps(build_graph(args.bundle, args.output, config["source_aliases"], config["include_review_candidates"], config.get("extraction_mode", "unit-cues")), ensure_ascii=False, indent=2))
        elif args.command == "search":
            from legal_ai.retrieval.bm25 import search
            from legal_ai.validation.bundle import validate_bundle
            folder = Path(args.bundle)
            documents, units, evidence, claims = [read_jsonl(folder / f"{name}.jsonl") for name in ("documents", "units", "evidence", "claims")]
            validate_bundle(documents, units, evidence, claims)
            results = search(units, args.question, args.top_k)
            print(json.dumps({"mode": "lexical_source_retrieval", "legal_status": "unknown", "generated_answer": False, "results": results}, ensure_ascii=False, indent=2))
        elif args.command == "parse":
            raw = Path(args.input).read_bytes().decode("utf-8")
            normalized = normalize(raw, Path(args.input).as_posix())
            version = digest(normalized["normalized_sha256"])
            result = parse(normalized, args.document_id, version)
            for unit in result["units"]:
                validate_unit(unit)
            folder = Path(args.output)
            write_json(folder / "normalized.json", normalized)
            write_jsonl(folder / "units.jsonl", result.pop("units"))
            write_json(folder / "parser-report.json", result)
            print(json.dumps({"output": str(folder), "audit_count": len(result["audit"]), "schema_version": VERSION}))
        else:
            folder = Path(args.bundle)
            documents = [validate_document(row) for row in read_jsonl(folder / "documents.jsonl")]
            units = [validate_unit(row) for row in read_jsonl(folder / "units.jsonl")]
            evidence = [validate_evidence(row) for row in read_jsonl(folder / "evidence.jsonl")]
            claims = read_jsonl(folder / "claims.jsonl")
            from legal_ai.validation.bundle import validate_bundle
            results = validate_bundle(documents, units, evidence, claims)
            write_jsonl(args.output, results)
            print(json.dumps({state: sum(row["decision"] == state for row in results) for state in ("accepted", "rejected", "needs_review")}))
            if any(row["decision"] == "rejected" for row in results):
                return 1
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
