# Repository Guidelines

## External Systems and Clarification

- Before interacting with external systems such as GitHub or Jira, always inform the user of the intended actions, ask for explicit approval, and wait for agreement. This includes read-only queries as well as creating, editing, committing, pushing, publishing, or changing statuses through those systems. Approval covers only the actions and scope described; ask again for a new scope.
- Do not treat an earlier task request or newly available permissions/network access as approval to resume external actions without asking first.
- Ask the user when requirements are unclear or a workflow appears inconsistent. For example, if a parent task is In Review while its subtasks remain in Backlog, explain the mismatch and ask what should happen before changing statuses. Do not silently infer completion or synchronize statuses.
- Local preparation may continue where it does not depend on the unresolved question or external approval.

## Project Structure & Module Organization

This workspace currently contains project documentation only. The `docs/` directory holds `De_cuong_DATN_Legal_AI.docx.pdf`. No source code, tests, dependency manifests, or build configuration are present.

Keep project documents in `docs/`. If implementation work begins, establish clear directories for application code, tests, and assets, and update this guide to describe their actual roles. Avoid introducing empty scaffolding without a concrete need.

## Build, Test, and Development Commands

No build, test, or local development commands are configured yet. Do not assume commands such as `npm test` or `make build` are available.

Useful inspection commands from the workspace root:

- `rg --files --hidden`: list files, including hidden configuration files.
- `Get-ChildItem -LiteralPath docs`: inspect the documentation directory in PowerShell.

When adding executable code, document its prerequisites, installation steps, and verified run and test commands alongside it.

## Documentation Style & Naming Conventions

Use descriptive Markdown headings and concise, actionable prose. Format commands and paths with backticks. Prefer descriptive filenames that identify a document's purpose; preserve existing filenames unless a rename is intentional and references are updated.

No language-specific indentation rules, formatter, or linter are configured. Establish those conventions when introducing a language or toolchain, and apply them consistently to new code.

## Validation Guidelines

No automated testing framework or coverage threshold exists. For documentation changes, check referenced paths and commands. Open changed PDFs to verify readability, page order, and layout. When adding code, include appropriate tests and document how to run them.

## Commit & Pull Request Guidelines

This workspace has no Git metadata, so historical commit conventions cannot be determined. If version control is initialized, use concise, imperative commit subjects, such as `docs: clarify project scope`.

Pull requests should explain the change, its purpose, and validation performed. Link relevant tasks when available; include before-and-after images for significant visual document changes. Avoid committing credentials or private data.
