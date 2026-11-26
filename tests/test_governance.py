from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_claude_md_is_pointer():
    claude = ROOT / "CLAUDE.md"
    assert claude.exists(), "CLAUDE.md must exist as a pointer to AGENTS.md (D101)"
    assert claude.read_text(encoding="utf-8").strip() == "See AGENTS.md."


def test_agents_md_exists():
    agents = ROOT / "AGENTS.md"
    assert agents.exists(), "AGENTS.md is the governance source of truth (D101)"
    text = agents.read_text(encoding="utf-8")
    assert "SearchService.run" in text