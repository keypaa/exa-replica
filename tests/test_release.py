import tomllib
from pathlib import Path

import pytest

import exa_replica

ROOT = Path(__file__).resolve().parent.parent


def test_version_0_1_0():
    with open(ROOT / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    assert data["project"]["version"] == "0.1.0"
    assert exa_replica.__version__ == "0.1.0"


def test_public_name():
    pytest.skip("public name is neutral and chosen by the owner before first public push (D97)")