import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _pyproject() -> dict:
    with open(ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)


def test_mcp_target_version_pinned():
    data = _pyproject()
    target = (
        data.get("tool", {}).get("exa-replica", {}).get("mcp_target_revision")
    )
    assert target == "2026-07-28", "MCP target revision must be pinned (D89)"
    deps = data["project"]["dependencies"]
    mcp_dep = [d for d in deps if d.replace(" ", "").startswith("mcp")]
    assert mcp_dep, "mcp must be a declared dependency"
    assert "2" in mcp_dep[0], f"mcp must be 2.x, got {mcp_dep[0]!r}"


def test_provenance_records_target():
    text = (ROOT / "docs" / "contracts" / "PROVENANCE.md").read_text(
        encoding="utf-8"
    )
    assert "2026-07-28" in text