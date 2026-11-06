# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`AGENTS.md` is the authoritative repository guide (external-system approval rules, conventions, validation rules) and must be followed.
This file adds the commands and cross-module architecture needed to work quickly.
Most project docs (`README.md`, `docs/`) are written in Vietnamese.

## Project

Lexora is a thesis-scale RAG pilot for Vietnamese labor law built on an evidence-backed legal knowledge base.
Every claim must be traceable to an exact quote with Unicode character offsets and a SHA-256 of the normalized source text.
Extracted norms and candidates are review-only (`needs_review`) until a human approves them; never present outputs as verified legal facts.
The planned four-condition research pipeline (DK1-DK4: fixed chunks, structural chunks, LLM KB before validation, LLM KB after validation) is not implemented yet; the only LLM extraction today is the demo's opt-in `norm-llm-v1` (`extraction/llm_norms.py`).

Direction since 2026-11-06 (decided, migration in progress): the product targets real users (corporate legal and HR staff: reviewers and readers), runs on a local machine first, and the tech migration comes before the DK1-DK4 pipeline.
Target stack: the core pipeline stays standard-library Python for reproducibility; the web layer moves to FastAPI + Pydantic, storage stays SQLite for the first steps, PostgreSQL (pgvector when needed) later, the UI to Svelte 5 + SvelteKit (static SPA served by FastAPI, TypeScript, Paraglide i18n), graphs to Cytoscape.js; LLM calls stay behind the 9Router provider; no LangChain, LlamaIndex or graph database.
Read `docs/planning/target-stack-2026-11-06.md` (layers, migration steps, open decisions) before starting migration work, and get user approval before installing any dependency.
Until a migration step lands, the current code below is the truth: standard library only, nothing to install.

## Commands

Python 3.11+, standard library only; nothing to install.
Run from the workspace root in PowerShell:

```powershell
$env:PYTHONPATH = 'src'                                   # needed for the CLI and demo
python -m unittest discover -s tests -v                   # all offline tests
python -m unittest tests.test_review_chat -v              # one module
python -m unittest tests.test_review_chat.ReviewChatTests.test_only_approved_sentence_not_full_unit_retrieved   # one test
python -m legal_ai.cli --help                             # snapshot, parse, validate, build-pilot, search, graph-build
python -m legal_ai.cli search data/normalized/pilot-v2 'Tiền lương thử việc ít nhất bao nhiêu phần trăm?' --top-k 2
python -m legal_ai.cli graph-build data/normalized/graph-pilot-v1 --config configs/entity-graph.json --output data/kb/new-entity-graph
python -m legal_ai.demo --store data/kb/demo-new.sqlite --seed data/kb/entity-relation-review/graph.json --port 8766
```

Web layer (FastAPI, migration step 1; needs the project virtualenv):

```powershell
python -m venv .venv; .venv\Scripts\python -m pip install -e ".[web,web-test]"   # once; installs from PyPI (approved 2026-11-06)
.venv\Scripts\python -m unittest discover -s tests -v                          # full suite incl. tests/test_web_api.py
.venv\Scripts\python -m legal_ai.web --store data/kb/demo-new.sqlite --port 8766  # same flags as legal_ai.demo, plus --frontend <build dir>
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
`legal_ai.web` without a build answers 503 with build instructions; `tests/test_web_api.py` skips without FastAPI.
Test files insert `src/` into `sys.path` themselves, so tests run without `PYTHONPATH`.
There is no linter or formatter.
Optional Node DOM smokes (no npm deps): `scripts/check_graph_viewer.cjs`, `scripts/check_entity_graph_viewer.cjs`.
Real-browser E2E for the demo (headless Chrome/Edge over DevTools, synthetic data, screenshots, fails on console errors): start the demo on a new store, then `node scripts/check_demo_browser.cjs http://127.0.0.1:<port> <screenshot-dir>`.
Always write graph/demo outputs to a new directory or new SQLite store; an existing demo store keeps its data and ignores `--seed`.

Network rules: only `cli snapshot` and the demo's opt-in 9Router flags (`--router-model`, `--extract-model`, `--embedding-model`, each requiring `--approve-router`) touch the network.
Both require explicit user approval of endpoint, model, data and scope first, per `AGENTS.md`.
Router settings (`9ROUTER_URL`, `9ROUTER_KEY`, `MODEL_*` aliases) are read only from Lexora's `.env` (see `.env.example`), never from the shell environment; only HTTPS or loopback endpoints are accepted.

## Architecture

Pipeline (all in `src/legal_ai/`):

1. `ingestion/snapshot.py` fetches immutable VBPL HTML snapshots with checksums; `vbpl_html.py` + `parser.py` split text into Chapter/Article/Clause/Point units; `pilot.py` builds the pilot bundle from `configs/sources-pilot.json` (pinned snapshots and scoped articles).
2. `normalization/text.py` produces the normalized text that all evidence offsets anchor to. Any normalization change invalidates old offsets and must create a new version.
3. `schemas/contract.py` defines the `1.0.0-pilot` JSONL contract (documents, units, evidence, claims). `validation/` checks schema, references and evidence (quote must equal `unit.text[start:end]`, hash must match). Synthetic examples live in `tests/fixtures/contract-v1/`; see `docs/data-contracts.md` and `docs/planning/schema-v1-migration.md`.
4. `retrieval/bm25.py` is CPU lexical retrieval returning exact source passages, not generated answers.
5. `extraction/candidates.py` (unit cues) and `extraction/norms.py` (`norm-rules-v2`: typed norm components, each slot with its own evidence; unmatched sentences with a normative cue become `cue-sentence` candidates) produce review-only candidates. `extraction/llm_norms.py` (`norm-llm-v1`) asks a model for verbatim slot values on sentences the rules did not structure and keeps only values it can locate exactly in the sentence. Modality cue words accepted as evidence live in `schemas/contract.py` `MODALITY_CUES`.
6. `kb/graph.py` builds JSON + SQLite graphs and embeds them into self-contained HTML viewers (`viewer.html`, `entity-viewer.html` via `viewer.py`). `kb/references.py` resolves cross-references using document aliases in `configs/knowledge-graph.json`; unresolved/external references stay explicit, never invented. `configs/entity-graph.json` selects the `evidence-graph-v2` norm-centered export.

Reviewed-KB demo (current work, see `docs/features/reviewed-kb-chat.md`):

- `auth.py` `AccountStore` (stdlib) keeps accounts, scrypt password hashes, SHA-256-digested session tokens with expiry, lockout after 5 failures, and chat ownership in the workspace SQLite file; roles `admin`, `reviewer`, `reader`; no self sign-up (`python -m legal_ai.auth create-admin`).
- `web/app.py` `create_app` is the FastAPI layer replacing `demo.py`: same paths, JSON shapes, status codes and gates (POST token, Host/Origin, size limit, CSP, no request logging) plus HttpOnly SameSite=Strict session cookies and per-route role checks (readers see published bases and only their own chats; publish records the signed-in reviewer), Pydantic request models, SPA serving of a SvelteKit build with the token injected and a fallback that never leaves the build. `web/setup.py` holds the stdlib CLI flags, opt-in 9Router providers and background extraction shared with `demo.py`.
- `demo.py` (legacy, removed once the SvelteKit UI lands) is a loopback-only single-user `ThreadingHTTPServer` serving `demo.html` + `demo.css` + `demo-app.js` (hash-routed workspace: KB list, 3-step import, annotated-statute review, preview, multi-KB chat), with a per-process POST token and Host/Origin checks. It intentionally does not log requests or uploads.
- `kb/import_review.py` `ReviewStore` (SQLite, `kb-store-v1`) holds several knowledge bases, each a chain of immutable revisions. A draft targets a new KB or pins one KB's current revision; review decisions (incl. batch per article and curated slot/modality edits anchored to exact source quotes) are saved incrementally; every claim must be decided before publish; stale drafts raise `Conflict` (HTTP 409). Old single-chain stores migrate into a default KB. Entity merges are `REVIEWED_ENTITY_LINK` edges within one KB, not global canonicalization. Every leaf sentence without a claim is a coverage gap that must get a reviewer-added claim (`manual-v1`) or a `no_norm` decision before publish. Drafts with `extraction=llm` (public KBs only) run AI extraction in a background thread of the demo (`start_extraction`/`finish_extraction`; restart marks it `interrupted`).
- `ingestion/source_library.py` `SourceLibrary` reads a local `source-library-v1` catalog, blocks path traversal and verifies SHA-256 before creating a draft.
- `rag/review_chat.py` `ChatService` binds each session to the current revisions of 1-5 KBs (deduplicating identical quotes across KBs) and retrieves only evidence of claims with `human_review.decision=approved` (not whole units that may contain rejected sentences), with accent-insensitive BM25, optionally fused (RRF) with cached dense similarities from `rag/dense.py` when the user enables semantic search and every bound KB is public. Default mode is extractive; LLM mode validates JSON statements and rejects citations outside the provided bundle.
- `glossary.py` (+ `glossary_en.py`, served bilingual at `/api/glossary`) is the single source of the hover explanations (definition, cue words, illustrative example) for review vocabulary such as Chủ thể, Tính quy phạm, Bên thụ hưởng; `embed_terms` inlines it with `term-tip.js`/`term-tip.css` at the `<!--LEXORA_TERMS-->` marker of `demo.html` and both graph viewers. Any element with `data-term="<key>"` shows its entry; `tests/test_glossary.py` fails if a key used in the UI has no entry.
- `providers/router.py` `RouterProvider` (chat) and `RouterEmbeddings` enforce one exact model per instance, a call budget, no retry/fallback, no redirects, `stream=false` and a bounded timeout.

Data layout: `data/raw/`, `data/normalized/`, `data/kb/` hold local artifacts excluded from Git and must be rebuilt locally on a fresh clone. `.my_docs/` is the user's private local demo pack. `docs/planning/local-pilot-review-2026-11-02.md` lists verified review commands and artifact paths.
