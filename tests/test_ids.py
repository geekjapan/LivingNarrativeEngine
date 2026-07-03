"""Regression tests for prefixed ID validation (issue #15)."""

import pytest

from living_narrative.state.ids import validate_prefixed_id


@pytest.mark.parametrize("value", ["char_001", "char_1000", "roll_1000", "roll_042"])
def test_validate_prefixed_id_accepts_valid_ids(value: str) -> None:
    prefix = value.split("_", 1)[0]
    assert validate_prefixed_id(prefix, value) == value


@pytest.mark.parametrize("value", ["char_1", "char_01", "char_abc", "char_"])
def test_validate_prefixed_id_rejects_invalid_ids(value: str) -> None:
    with pytest.raises(ValueError):
        validate_prefixed_id("char", value)
