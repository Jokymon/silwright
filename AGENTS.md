# Repository instructions

## Python development

- This project uses Python 3.14 or newer and `uv` for Python environments,
  dependency management, locking, and command execution.
- Keep dependencies in `pyproject.toml` and commit corresponding changes to
  `uv.lock`. Use `uv add` or `uv remove` instead of invoking `pip` directly.
- Synchronize an unchanged dependency set with `uv sync --locked`. Run project
  commands through `uv run`.

## Tests and quality checks

- Unit tests use pytest and live under `tests/`. Add or update tests when
  changing behavior, and run them with `uv run pytest`.
- Python linting uses Ruff. Run it with `uv run ruff check .`.
- Python type checking uses Mypy in strict mode. Run it with `uv run mypy`.
- Before completing a Python change, run all relevant tests, lint checks, and
  type checks. Report any check that could not be run.

## Changelog

- When adding a new feature, add a concise entry to the `Added` section under
  `[Unreleased]` in `CHANGELOG.md` as part of the same change.

## Documentation

- Project documentation uses MkDocs. Author documentation as Markdown under
  `docs/` and maintain its navigation in `mkdocs.yml`.
- Documentation dependencies are declared in the `docs` dependency group.
  Build the site with `uv run --group docs mkdocs build --strict`.
- Treat MkDocs warnings and broken navigation or links as issues to fix before
  completing a documentation change.

## Design decisions

- Store design decisions as Markdown files under `docs/decisions/`.
- Use these records for any significant project decision with broad or lasting
  relevance; they are not limited to purely architectural decisions.
- Keep exactly one design decision in each file.
- Name decision files `NNNN-decision-slug.md`, where `NNNN` is a zero-padded,
  monotonically increasing sequence number and `decision-slug` is a concise
  lowercase kebab-case description.
- Give each decision a single level-one heading naming the decision.
- Immediately after the title, record the decision date and status as bold
  Markdown fields:

  ```markdown
  **Date:** YYYY-MM-DD

  **Status:** in review | active | superseded
  ```

  Use the date on which the decision was made, not the date on which its file
  was last edited. Use exactly one of the listed lowercase status values.
- When a decision is superseded, add a `**Superseded by:**` field containing a
  relative Markdown link to the newer decision. Do not remove or rewrite the
  superseded decision merely to reflect the newer outcome.
- Record the decision's context and chosen approach under `## Context` and
  `## Decision` headings. When alternatives were evaluated, record them under
  `## Alternatives considered`; individual alternatives may use level-three
  headings or a list.
- Add new decisions as new numbered files. Do not combine separate decisions
  into a single document or renumber existing decision files.
- Add each decision to the Design decisions section of `mkdocs.yml`, and update
  documentation references when a decision file is added, renamed, or removed.
