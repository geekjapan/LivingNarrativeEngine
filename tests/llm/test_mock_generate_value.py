"""Regression: unscripted mock generation must produce valid enum values, not None.

Surfaced by add-cli-and-sample's ``turn --intervention`` (free-text) path, which calls
the Interpreter's ``InterpreterOutput`` schema (required ``StrEnum`` fields ``type``/
``visibility``) through the mock provider with no fixture.
"""

from enum import StrEnum

from pydantic import BaseModel

from living_narrative.llm.mock import generate_value


class Color(StrEnum):
    RED = "red"
    GREEN = "green"


class Sample(BaseModel):
    color: Color
    name: str


def test_generate_value_produces_a_valid_member_for_a_required_enum_field():
    value = generate_value(Color, "seed", "hash", "color")

    assert value in {member.value for member in Color}


def test_generate_value_is_deterministic_for_the_same_seed_and_prompt_hash():
    first = generate_value(Color, "seed", "hash", "color")
    second = generate_value(Color, "seed", "hash", "color")

    assert first == second


def test_generate_value_validates_through_a_model_with_a_required_enum_field():
    values = generate_value(Sample, "seed", "hash")

    Sample.model_validate(values)  # must not raise
