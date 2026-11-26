import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / "docs" / "contracts"

OPENAPI_SHA256 = (
    "d625c66c6bbcdf0b5fe57ccc74bd02005ae888f0f862e16e127722ddb1af499b"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_openapi_snapshot_matches_pin():
    assert _sha256(CONTRACTS / "exa-openapi-2.0.0.yaml") == OPENAPI_SHA256


def test_tools_list_snapshot_matches_capture():
    snap = CONTRACTS / "exa-tools-list-2.0.0.json"
    capture = ROOT / "docs" / "fixtures" / "exa-mcp" / "tools.json"
    assert snap.exists(), "tools/list snapshot must be committed (D103)"
    assert snap.read_bytes() == capture.read_bytes()


def test_provenance_present():
    text = (CONTRACTS / "PROVENANCE.md").read_text(encoding="utf-8")
    assert OPENAPI_SHA256 in text