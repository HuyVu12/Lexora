# Repository Guidelines

## External Systems and Clarification

- Before interacting with external systems such as GitHub or Jira, always inform the user of the intended actions, ask for explicit approval, and wait for agreement. This includes read-only queries as well as creating, editing, committing, pushing, publishing, or changing statuses through those systems. Approval covers only the actions and scope described; ask again for a new scope.
- Do not treat an earlier task request or newly available permissions/network access as approval to resume external actions without asking first.
- Ask the user when requirements are unclear or a workflow appears inconsistent. For example, if a parent task is In Review while its subtasks remain in Backlog, explain the mismatch and ask what should happen before changing statuses. Do not silently infer completion or synchronize statuses.
- Local preparation may continue where it does not depend on the unresolved question or external approval.

## Project Structure & Module Organization

This workspace holds Lexora, a thesis-scale RAG system for Vietnamese labour law built on an evidence-backed knowledge base, and its documentation.
`src/legal_ai/` holds the standard-library core: ingestion (pinned VBPL snapshots, vbpl.vn gateway fetches, the offline catalog, file readers, article excerpts), normalization, parsing, the `1.0.0-pilot` contract, validation, rule and LLM norm extraction, BM25 retrieval, graph building and the reviewed-KB chat.
`src/legal_ai/web/` is the FastAPI layer with accounts and roles; `frontend/` is the SvelteKit UI it serves; `src/legal_ai/research/` keeps research corpora, question sets and model proposals; `src/legal_ai/indexing/` and `src/legal_ai/evaluation/` run the DK1/DK2 retrieval experiments.
`tests/` contains offline tests; `tests/fixtures/` contains synthetic contract data and draft pilot questions.
`configs/` pins sources, graph settings and the DK1-DK4 conditions; `prompts/` holds versioned prompts.
`data/`, `experiments/runs/` and `.my_docs/` hold local artifacts excluded from Git.
`docs/` holds the proposal, design, plans, decisions, guidelines and dated review reports; start with `docs/planning/progress-2026-11-07.md`.

Extracted norms and question proposals are review-only until a person accepts them; never present outputs as independently verified legal facts or legal validity.

Keep project documents in `docs/`. Avoid introducing empty scaffolding without a concrete need. Keep research configurations separate from the product knowledge bases; DK3/DK4, answer generation and answer scoring are not implemented yet.

## Build, Test, and Development Commands

The core pipeline runs on Python 3.11+ with the standard library only (verified on Python 3.14.8).
The web layer, the PDF reader and the catalog builder need the project virtualenv (`.venv`, extras `web`, `web-test`, `catalog`), and the UI needs Node; packages approved so far are recorded in `pyproject.toml`, `frontend/package.json` and `docs/decisions.md`.
Adding any other dependency still needs explicit user approval. From the workspace root in PowerShell:

- `python -m unittest discover -s tests -v`: offline tests, no network/model calls; web, catalog and PDF tests skip without their packages.
- `.venv\Scripts\python -m pip install -e ".[web,web-test,catalog]"`: the virtualenv for the web layer and the full test suite (`.venv\Scripts\python -m unittest discover -s tests -v`).
- `cd frontend; npm install; npm run build` then `.venv\Scripts\python -m legal_ai.auth create-admin --store <store> --username admin` and `.venv\Scripts\python -m legal_ai.web --store <store> --port 8766`: build the UI, create the first admin, run the app.
- `node scripts/check_app_browser.cjs http://127.0.0.1:<port> <dir>`: real-browser E2E on a NEW store with the three accounts the script header names; it makes no network or model calls.
- `cd frontend; npx svelte-check --tsconfig ./tsconfig.json`: types and accessibility warnings of the UI.
- `$env:PYTHONPATH = 'src'` then `python -m legal_ai.cli --help`: snapshot, parse, validate, build-pilot, search, graph-build, catalog-build, catalog-search, vbpl-fetch, corpus-export, run-retrieval.
- `python -m legal_ai.cli run-retrieval <bundle> --condition configs/experiments/dk2.json --output experiments/runs/<new>`: a DK1/DK2 retrieval run into a new directory.
- `python scripts/build_fixture.py`: rebuild the synthetic JSONL fixture.
- `node scripts/check_graph_viewer.cjs data/kb/knowledge-graph-review/index.html` and `node scripts/check_entity_graph_viewer.cjs data/kb/entity-relation-review/index.html`: optional DOM smokes of the standalone graph exports.

Network and model calls happen only through explicit commands or run flags, each needing the user's approval of endpoint, model, data and scope first:
`cli snapshot` and `cli vbpl-fetch`; the web flag `--allow-vbpl` (one confirmed vbpl.vn document per request); the 9Router flags (`--router-model`, `--extract-model`, `--embedding-model`, each with `--approve-router`); and the Claude Code flags (`--extract-claude-model`, `--proposal-model`, each with `--approve-claude`), which run the local `claude -p` on the user's own plan.
Never automate vbpl.vn's own search pages; they sit behind bot protection.

Useful inspection commands from the workspace root:

- `rg --files --hidden`: list files, including hidden configuration files.
- `Get-ChildItem -LiteralPath docs`: inspect the documentation directory in PowerShell.

When adding executable code, document its prerequisites, installation steps, and verified run and test commands alongside it.

## Documentation Style & Naming Conventions

Use descriptive Markdown headings and concise, actionable prose. Format commands and paths with backticks. Prefer descriptive filenames that identify a document's purpose; preserve existing filenames unless a rename is intentional and references are updated.

Python uses four-space indentation, snake_case functions/modules and standard-library unittest. JSON artifacts use UTF-8 and explicit version fields. No formatter or linter is configured.

## Validation Guidelines

Use standard-library unittest for offline invariants and failure paths. There is no coverage threshold. For documentation changes, check referenced paths and commands. Open changed PDFs to verify readability, page order, and layout. Never treat synthetic fixtures or draft pilot questions as independent legal gold.

## Commit & Pull Request Guidelines

The workspace has Git metadata and the Lexora origin. Use concise, imperative commit subjects, such as `docs: clarify project scope`. External actions, commits and pushes remain subject to the approval rules above.

Pull requests should explain the change, its purpose, and validation performed. Link relevant tasks when available; include before-and-after images for significant visual document changes. Avoid committing credentials or private data.
