# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`AGENTS.md` is the authoritative repository guide (external-system approval rules, conventions, validation rules) and must be followed.
This file adds the commands and cross-module architecture needed to work quickly.
Most project docs (`README.md`, `docs/`) are written in Vietnamese.

## Project

Lexora is a thesis-scale RAG pilot for Vietnamese labor law built on an evidence-backed legal knowledge base.
Every claim must be traceable to an exact quote with Unicode character offsets and a SHA-256 of the normalized source text.
Extracted norms and candidates are review-only (`needs_review`) until a human approves them; never present outputs as verified legal facts.
The four-condition research pipeline (DK1-DK4: fixed chunks, structural chunks, LLM KB before validation, LLM KB after validation) runs on the 94-article experiment scope (`configs/experiment-scope-v1.json`): retrieval for all four conditions (BM25, local BGE-M3 dense, hybrid), the DK3/DK4 knowledge base from one Opus extraction run, cited answers with blinded grading, planted-error validation (RQ2) and the extraction gold set (RQ1); see `docs/planning/progress-2026-11-08.md`.

Direction since 2026-11-06 (decided; web, UI and graph migration done 07/11, PostgreSQL deferred until after the MVP freeze on 27/11): the product targets real users (corporate legal and HR staff: reviewers and readers), runs on a local machine first, and the tech migration comes before the DK1-DK4 pipeline.
Target stack: the core pipeline stays standard-library Python for reproducibility; the web layer moves to FastAPI + Pydantic, storage stays SQLite for the first steps, PostgreSQL (pgvector when needed) later, the UI to Svelte 5 + SvelteKit (static SPA served by FastAPI, TypeScript, typed dictionaries for i18n), graphs to Cytoscape.js; LLM calls go through Claude Code (Opus 5.5 for DK3 extraction and answers, Sonnet 5.5 as the supplementary judge) or the 9Router provider, one fixed model per run; no LangChain, LlamaIndex or graph database.
Read `docs/planning/target-stack-2026-11-06.md` (layers, migration steps, open decisions) and `docs/planning/progress-2026-11-08.md` (what is done, what comes next) before larger work, and get user approval before installing any dependency.

## Commands

The core runs on Python 3.11+ with the standard library only; the web layer, PDF reader and catalog builder need `.venv` (below).
Run from the workspace root in PowerShell:

```powershell
$env:PYTHONPATH = 'src'                                   # needed for the CLI
python -m unittest discover -s tests -v                   # all offline tests
python -m unittest tests.test_review_chat -v              # one module
python -m unittest tests.test_review_chat.ReviewChatTests.test_only_approved_sentence_not_full_unit_retrieved   # one test
python -m legal_ai.cli --help                             # snapshot, parse, validate, build-pilot, search, graph-build, run-retrieval
python -m legal_ai.cli build-pilot --config configs/sources-full-v1.json --output data/normalized/<new>   # whole-document corpus from pinned snapshots
python -m legal_ai.cli catalog-search data/catalog/catalog-v1.sqlite 'bo luat lao dong'   # offline, accents ignored; build with catalog-build (needs .venv catalog extra)
python -m legal_ai.cli vbpl-fetch <vbpl.vn link or ID>      # ONE approved vbpl.vn document -> data/raw/vbpl/<id>/<sha>/
python -m legal_ai.cli run-retrieval data/normalized/full-v1 --condition configs/experiments/dk2.json --output experiments/runs/<new>   # DK1-DK4 Recall@K; --shared configs/experiments/shared.json for hybrid (needs .venv embeddings extra)
python -m legal_ai.cli corpus-scope --store <store.sqlite> --actor <user>            # experiment-scope corpus from pinned local snapshots
python -m legal_ai.cli kb-extract <bundle> --output experiments/runs/<new> --dry-run   # DK3/DK4 extraction plan; real run adds --max-calls N --approve-claude
python -m legal_ai.cli kb-materialize <kb run>                                       # rebuild dk3/dk4/validation offline; kb-inject <kb run> --output <new> for RQ2
python -m legal_ai.cli gold-score <gold.jsonl> --bundle <bundle> --predictions rules   # RQ1 P/R/F1 (or a dk3.jsonl/dk4.jsonl)
python -m legal_ai.cli answer-run <retrieval run> --questions <q.json> --output <new> --max-calls N --approve-claude   # then answer-score, answer-sheet, answer-grades, answer-judge
python -m legal_ai.cli preflight --retrieval <DK1..DK4 runs> --answers <answer runs>   # fairness checks before reporting RQ3; exits 1 on failure
python -m legal_ai.cli kb-compare                                                    # extraction-model comparison -> docs/results/extraction-models.{md,json}
python -m legal_ai.cli kb-audit-sheet <kb runs> --sheet <csv> --key <json>            # blinded sample of rejected/accepted claims to label; kb-audit-score <csv> --key <json> [--compare <csv>]
python -m legal_ai.cli demo-build --store data/kb/demo-<date>.sqlite                  # fresh demo store (admin, reviewer, reader and dev accounts with printed passwords, frozen scope corpus); see docs/demo-runbook.md
python -m legal_ai.cli search data/normalized/pilot-v2 'Tiền lương thử việc ít nhất bao nhiêu phần trăm?' --top-k 2
python -m legal_ai.cli graph-build data/normalized/graph-pilot-v1 --config configs/entity-graph.json --output data/kb/new-entity-graph
```

Web app (FastAPI + SvelteKit; needs the project virtualenv):

```powershell
python -m venv .venv; .venv\Scripts\python -m pip install -e ".[web,web-test,catalog,embeddings]"   # once; installs from PyPI (approved 2026-11-06, pypdf/pyarrow 2026-11-07, embeddings 2026-11-08; BGE-M3 weights go to models/bge-m3)
.venv\Scripts\python -m unittest discover -s tests -v                          # full suite incl. tests/test_web_api.py
.venv\Scripts\python -m legal_ai.web --store data/kb/app-new.sqlite --seed data/kb/entity-relation-review/graph.json --port 8766  # --frontend <build dir>, --source-catalog, opt-in 9Router flags
```

Frontend (SvelteKit 3, Svelte 5, TypeScript; npm packages approved 2026-11-06):

```powershell
cd frontend; npm install; npm run build; cd ..                          # static SPA into frontend/build
.venv\Scripts\python -m legal_ai.auth create-admin --store <store.sqlite> --username admin   # first admin, prompts for a password
.venv\Scripts\python -m legal_ai.web --store <store.sqlite> --port 8766  # serves frontend/build with the POST token injected
cd frontend; npx svelte-check --tsconfig ./tsconfig.json; cd ..          # types and Svelte a11y warnings
node scripts/check_app_browser.cjs http://127.0.0.1:<port> <screenshot-dir>   # real-browser E2E; needs a NEW store seeded with admin/phapche/nhansu (see the script header)
```

Kit 3 notes: options go to `sveltekit({...})` in `vite.config.ts` (no svelte.config.js); `$lib` is replaced by the `#lib` subpath import from `package.json`, and TypeScript modules are imported with a `.js` suffix (`#lib/api.js`). Interface strings live in `frontend/src/lib/i18n/vi.ts` (source of keys) and `en.ts` (typed `Record<MessageKey, string>`, so a missing key fails the build); Paraglide was rejected because its build fetches and runs a plugin from a CDN. A variable must not be named `state` in a component (it collides with the `$state` rune).
Question sets live under `frontend/src/routes/research/questions` (list and pack import, `[id]` workspace with proposal-mode choice, `LabelForm`, batched model proposals, drafts and exchange, `[id]/compare` adjudication and freeze); model calls need `--proposal-model <model> --approve-claude` and a `ConfirmDialog` per batch. Research corpora live under `frontend/src/routes/research` (list, `[id]` with catalog search, vbpl.vn link and file upload, `[id]/document/[row]` parser review); a vbpl.vn fetch always goes through the confirmation dialog and needs the server flag `--allow-vbpl`, the catalog needs `--catalog` or `data/catalog/catalog-v1.sqlite`. The knowledge graph is the in-app route `frontend/src/routes/kb/[id]/graph` (Cytoscape.js via `lib/components/GraphCanvas.svelte`, element builders in `lib/graph.ts`, data from `GET /api/kb/graph`); in Cytoscape font strings, quote family names containing digits (`'Source Serif 4 Variable'`) or the canvas silently falls back to 10px. The standalone `kb/*viewer.html` pages remain only for `cli graph-build` exports.
`legal_ai.web` without a build answers 503 with build instructions; `tests/test_web_api.py` skips without FastAPI.
Test files insert `src/` into `sys.path` themselves, so tests run without `PYTHONPATH`.
There is no linter or formatter.
Optional Node DOM smokes (no npm deps): `scripts/check_graph_viewer.cjs`, `scripts/check_entity_graph_viewer.cjs`.
Always write graph/app outputs to a new directory or new SQLite store; an existing store keeps its data and ignores `--seed`.

Network rules: only `cli snapshot`, `cli vbpl-fetch`, the web flag `--allow-vbpl` (one confirmed vbpl.vn document per request), the opt-in 9Router flags (`--router-model`, `--extract-model`, `--embedding-model`, each requiring `--approve-router`) and the Claude Code flags (`--extract-claude-model`, `--proposal-model`, each requiring `--approve-claude`) touch the network or a model.
All require explicit user approval of endpoint, model, data and scope first, per `AGENTS.md`; vbpl.vn's own search pages are never automated.
Router settings (`9ROUTER_URL`, `9ROUTER_KEY`, `MODEL_*` aliases) are read only from Lexora's `.env` (see `.env.example`), never from the shell environment; only HTTPS or loopback endpoints are accepted.

## Architecture

Pipeline (all in `src/legal_ai/`):

1. `ingestion/vbpl_api.py` fetches one explicitly requested vbpl.vn document from the public JSON gateway the site uses (`/api/qtdc/public/doc/{id}`, undocumented; links or IDs, HTTPS gateway host only, no redirects, 2 s between calls) as an immutable `document.json` snapshot with official metadata incl. effect status; the site's search is behind bot protection and must never be automated. `ingestion/catalog.py` is the offline search catalog (`catalog-v1`, SQLite FTS5 over accent-folded titles and numbers, in-force first) built from th1nhng0/vietnamese-legal-documents (CC BY 4.0) and undertheseanlp/UTS_VLC (MIT), whose IDs are vbpl.vn IDs; its effect status is the dataset's, so prefer the fetched one. `ingestion/files.py` reads TXT, HTML, DOCX and text-layer PDF (pypdf) uploads. `ingestion/snapshot.py` fetches immutable VBPL HTML snapshots with checksums; `vbpl_html.py` + `parser.py` split text into Chapter/Article/Clause/Point units; `pilot.py` builds the pilot bundle from `configs/sources-pilot.json` (pinned snapshots and scoped articles).
2. `normalization/text.py` produces the normalized text that all evidence offsets anchor to. Any normalization change invalidates old offsets and must create a new version.
3. `schemas/contract.py` defines the `1.0.0-pilot` JSONL contract (documents, units, evidence, claims). `validation/` checks schema, references and evidence (quote must equal `unit.text[start:end]`, hash must match). Synthetic examples live in `tests/fixtures/contract-v1/`; see `docs/data-contracts.md` and `docs/planning/schema-v1-migration.md`.
4. `retrieval/bm25.py` holds the shared `BM25` ranker (k1/b explicit, ties broken by document order) and the review `search` over leaf units; it returns exact source passages, not generated answers. `indexing/records.py` builds DK1 fixed-token chunks and DK2 leaf-unit records, each an exact source span mapped to canonical unit IDs (`index-record-v1`, tokenizer `lexora-syllable-v1`); `evaluation/retrieval_run.py` ranks them per question and writes manifest, records, predictions, Recall@K and context-token metrics to a new run directory. `pilot.py` accepts `"article_ids": "all"` for a whole-document corpus (`configs/sources-full-v1.json`).
5. `extraction/candidates.py` (unit cues) and `extraction/norms.py` (`norm-rules-v2`: typed norm components, each slot with its own evidence; unmatched sentences with a normative cue become `cue-sentence` candidates) produce review-only candidates. `extraction/llm_norms.py` (`norm-llm-v1`) asks a model for verbatim slot values on sentences the rules did not structure and keeps only values it can locate exactly in the sentence; providers with `structured()` (Claude Code, enabled by `--extract-claude-model <model> --approve-claude`, exclusive with the 9Router `--extract-model`) get its JSON `SCHEMA`. Modality cue words accepted as evidence live in `schemas/contract.py` `MODALITY_CUES`.
6. `kb/graph.py` builds JSON + SQLite graphs and embeds them into self-contained HTML viewers (`viewer.html`, `entity-viewer.html` via `viewer.py`). `kb/references.py` resolves cross-references using document aliases in `configs/knowledge-graph.json`; unresolved/external references stay explicit, never invented. `configs/entity-graph.json` selects the `evidence-graph-v2` norm-centered export.

Reviewed-KB web app (current work, see `docs/features/reviewed-kb-chat.md`):

- `auth.py` `AccountStore` (stdlib) keeps accounts, scrypt password hashes, SHA-256-digested session tokens with expiry, lockout after 5 failures, and chat ownership in the workspace SQLite file; roles `admin`, `reviewer`, `reader`; no self sign-up (`python -m legal_ai.auth create-admin`).
- `web/app.py` `create_app` is the FastAPI layer (it replaced the legacy stdlib `demo.py`, removed 2026-11-07): loopback gates (POST token, Host/Origin, size limit, CSP, no request logging) plus HttpOnly SameSite=Strict session cookies and per-route role checks (readers see published bases and only their own chats; publish records the signed-in reviewer), Pydantic request models, SPA serving of a SvelteKit build with the token injected and a fallback that never leaves the build. `web/setup.py` holds the stdlib CLI flags, opt-in 9Router providers and background extraction.
- `kb/import_review.py` `ReviewStore` (SQLite, `kb-store-v1`) holds several knowledge bases, each a chain of immutable revisions. A draft targets a new KB or pins one KB's current revision; review decisions (incl. batch per article and curated slot/modality edits anchored to exact source quotes) are saved incrementally; every claim must be decided before publish; stale drafts raise `Conflict` (HTTP 409). Old single-chain stores migrate into a default KB. Entity merges are `REVIEWED_ENTITY_LINK` edges within one KB, not global canonicalization. Every leaf sentence without a claim is a coverage gap that must get a reviewer-added claim (`manual-v1`) or a `no_norm` decision before publish. Drafts with `extraction=llm` (public KBs only) run AI extraction in a background thread of the web app (`start_extraction`/`finish_extraction`; restart marks it `interrupted`).
- `ingestion/source_library.py` `SourceLibrary` reads a local `source-library-v1` catalog, blocks path traversal and verifies SHA-256 before creating a draft.
- `rag/review_chat.py` `ChatService` binds each session to the current revisions of 1-5 KBs (deduplicating identical quotes across KBs) and retrieves only evidence of claims with `human_review.decision=approved` (not whole units that may contain rejected sentences), with accent-insensitive BM25, optionally fused (RRF) with cached dense similarities from `rag/dense.py` when the user enables semantic search and every bound KB is public. Default mode is extractive; LLM mode validates JSON statements and rejects citations outside the provided bundle.
- `glossary.py` (+ `glossary_en.py`, served bilingual at `/api/glossary`) is the single source of the hover explanations (definition, cue words, illustrative example) for review vocabulary such as Chủ thể, Tính quy phạm, Bên thụ hưởng; `embed_terms` inlines it with `term-tip.js`/`term-tip.css` at the `<!--LEXORA_TERMS-->` marker of both graph viewers; the SvelteKit UI loads it from `/api/glossary` (`Term.svelte`, `GlossaryTip.svelte`). Any element with `data-term="<key>"` shows its entry; `tests/test_glossary.py` fails if a key used in the UI has no entry.
- `research/corpus.py` `CorpusStore` (`corpus-store-v1`, workspace SQLite) keeps research corpora: immutable document rows (source bytes, normalized text, units, parser report) from vbpl.vn snapshots or files, frozen numbered versions with a bundle hash, `export_version` (contract bundle for `run-retrieval`) and `version_payload`/`import_version` to move a version between machines. `research/questions.py` `QuestionStore` (`questions-store-v1`) binds question sets to a frozen version: questions with origin (human/model) and paraphrase families, a once-chosen proposal mode per annotator, labels (type, expected answer/refuse, unit IDs, note) recording kept/changed proposal fields, packs and label files across machines, Cohen's kappa and Dice comparison, adjudication, and freezing with family-level dev/held-out splits (stratified, seeded). `research/proposals.py` asks a structured provider for label proposals (BM25 candidates over DK2 records, unit IDs constrained by an enum schema) and question drafts, with prompts in `prompts/` and every call logged. `providers/claude_code.py` `ClaudeCodeProvider` runs `claude -p --safe-mode` with Lexora's system prompt file, no tools, a JSON schema, no session, in an empty temp dir; one model/effort, call budget, no retry, explicit approval. See `docs/features/question-annotation.md`.
- `providers/router.py` `RouterProvider` (chat) and `RouterEmbeddings` enforce one exact model per instance, a call budget, no retry/fallback, no redirects, `stream=false` and a bounded timeout.

Data layout: `data/raw/`, `data/normalized/`, `data/kb/` hold local artifacts excluded from Git and must be rebuilt locally on a fresh clone. `.my_docs/` is the user's private local demo pack. `docs/planning/local-pilot-review-2026-11-02.md` lists verified review commands and artifact paths.
