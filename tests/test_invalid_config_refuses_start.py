import pytest
from pydantic import ValidationError

from exa_replica.bootstrap.config import Settings


def test_invalid_config_refuses_start():
    # deep is out of v1 (D15/D18); an invalid setting must refuse startup (D92/D102).
    with pytest.raises(ValidationError):
        Settings(tier="deep")


def test_valid_config_loads():
    assert Settings(tier="lite").tier == "lite"
    assert Settings().tier == "auto"