# Repository Guidelines

## External Systems and Clarification

- Before interacting with external systems such as GitHub or Jira, always inform the user of the intended actions, ask for explicit approval, and wait for agreement. This includes read-only queries as well as creating, editing, committing, pushing, publishing, or changing statuses through those systems. Approval covers only the actions and scope described; ask again for a new scope.
- Do not treat an earlier task request or newly available permissions/network access as approval to resume external actions without asking first.
- Ask the user when requirements are unclear or a workflow appears inconsistent. For example, if a parent task is In Review while its subtasks remain in Backlog, explain the mismatch and ask what should happen before changing statuses. Do not silently infer completion or synchronize statuses.
- Local preparation may continue where it does not depend on the unresolved question or external approval.

## Project Structure & Module Organization

This workspace contains a Python pilot and project documentation. `src/legal_ai/` holds schema contracts, ingestion, normalization, technical validation, provider boundary and CPU lexical retrieval. `tests/` contains offline tests; `tests/fixtures/` contains synthetic contract data and draft pilot questions. `configs/sources-pilot.json` pins two VBPL snapshots and scoped articles. `data/raw/` and `data/normalized/` hold local artifacts excluded from Git. `docs/` holds the original proposal, plans, migration notes and review reports.

Current focus is the evidence-backed knowledge graph. `src/legal_ai/kb/` builds JSON/SQLite graphs and a self-contained viewer; `src/legal_ai/extraction/candidates.py` produces review-only unit candidates. `configs/sources-graph.json` adds Article 21 from the existing snapshot for reference resolution; `configs/knowledge-graph.json` pins explicit document aliases. Graph outputs live in `data/kb/` and remain excluded from Git.

The current entity/relation view uses `src/legal_ai/extraction/norms.py` and `configs/entity-graph.json`. It extracts review-only typed norm components with per-slot evidence, exports `evidence-graph-v2`, and opens a norm-centered viewer plus a separate structure view. Unsupported source text stays in the extraction report; do not treat these outputs as independently verified legal facts.

Keep project documents in `docs/`. Avoid introducing empty scaffolding without a concrete need. Keep draft research configurations separate from the CPU retrieval pilot; the full RAG/model pipeline is not implemented yet.

## Build, Test, and Development Commands

Runtime requires Python 3.11+ and uses the standard library only (verified on Python 3.14.8). No package install is required. On 2026-11-06 the user approved a target stack for real users (FastAPI, PostgreSQL, TypeScript + Vite, Cytoscape.js) while the core pipeline stays standard-library Python; it is not implemented yet, and adding any dependency still needs explicit user approval. See `docs/planning/target-stack-2026-11-06.md`. From the workspace root in PowerShell:

- `python -m unittest discover -s tests -v`: offline tests, no network/model calls.
- `.venv\Scripts\python -m pip install -e ".[web,web-test]"` then `.venv\Scripts\python -m legal_ai.web --store <new.sqlite> --port 8766`: FastAPI web layer (migration step 1); `tests/test_web_api.py` runs only inside `.venv`.
- `cd frontend; npm install; npm run build` then `.venv\Scripts\python -m legal_ai.auth create-admin --store <store> --username admin`: SvelteKit frontend and the first admin account; `node scripts/check_app_browser.cjs http://127.0.0.1:<port> <dir>` is its real-browser E2E (new store with the three accounts the script header names).
- `python scripts/build_fixture.py`: rebuild synthetic JSONL fixture.
- `$env:PYTHONPATH = 'src'`: enable the source package for this shell.
- `python -m legal_ai.cli --help`: list snapshot, parse, build-pilot, validate and search commands.
- `python -m legal_ai.cli graph-build data/normalized/graph-pilot-v1 --output data/kb/new-graph`: build graph and viewer into a new output directory.
- `node scripts/check_graph_viewer.cjs data/kb/knowledge-graph-review/index.html`: optional DOM unit smoke (Node 24 verified, no npm dependencies); does not replace real-browser visual QA.
- `python -m legal_ai.cli graph-build data/normalized/graph-pilot-v1 --config configs/entity-graph.json --output data/kb/new-entity-graph`: build the entity/relation view in a new output directory.
- `node scripts/check_entity_graph_viewer.cjs data/kb/entity-relation-review/index.html`: optional DOM unit smoke for the norm-centered view.

See `docs/planning/local-pilot-review-2026-11-02.md` for verified review commands and artifact paths. Only the explicit `snapshot` command contacts the network; follow the external-system approval rules before using it. The setuptools build backend is optional packaging metadata; installation/build is unverified and not required for review.

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
