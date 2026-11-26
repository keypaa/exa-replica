.PHONY: check lint type contracts test audit

check: lint type contracts test audit

lint:
	uv run ruff check src/ tests/

type:
	uv run mypy --strict src/exa_replica/

contracts:
	uv run lint-imports

test:
	uv run pytest -q

# Best-effort in the dev box; CI installs gitleaks + pip-audit and runs them for real.
audit:
	@command -v gitleaks >/dev/null 2>&1 && gitleaks detect --no-banner --redact || echo "gitleaks: skipped (not installed)"
	@command -v pip-audit >/dev/null 2>&1 && pip-audit --skip-editable || echo "pip-audit: skipped (not installed)"