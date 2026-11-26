from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_make_check_exists():
    makefile = ROOT / "Makefile"
    assert makefile.exists(), "Makefile must exist (D102)"
    assert "check:" in makefile.read_text(encoding="utf-8")


def test_governance_files_exist():
    for name in ("SECURITY.md", "CONTRIBUTING.md"):
        assert (ROOT / name).exists(), f"{name} must exist (D98/D91)"
    ci = ROOT / ".github" / "workflows" / "ci.yml"
    assert ci.exists(), "CI workflow must exist (D17 5e)"