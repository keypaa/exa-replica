# Contributing (D98 / D102)

## Workflow

- Conventional commits; every commit carries a `Signed-off-by` line (DCO).
- One logical change per PR; PR ≤400 lines.
- `make check` green before merge: ruff + mypy --strict + import-linter +
  pytest + gitleaks + pip-audit.
- Every code choice cites the `Dxx` decision it implements.

## Ground rules

- Read `AGENTS.md` first (governance source of truth; `CLAUDE.md` is a pointer).
- `domain/` is pure and imports no web/ML framework; `import-linter` blocks
  violations (D96).
- The canonical entrypoint is `SearchService.run`; do not introduce a parallel
  public name for the pipeline.
- No product code before planning is complete (D47); amend a decision with the
  measured value + source + date instead of inventing one.

## Dev box

- Python 3.12 (`uv python pin 3.12`), `uv sync`, then `make check`.
- Heavy work (ingest/embed/index, cargo build) runs on the reference box or
  Modal, never the laptop (D39).