"""ID validators shared by state models."""

import re
from collections.abc import Callable
from typing import Annotated

from pydantic import AfterValidator


def validate_prefixed_id(prefix: str, value: str) -> str:
    if not re.fullmatch(rf"{re.escape(prefix)}_\d{{3,}}", value):
        raise ValueError(f"expected {prefix}_<zero-padded number>")
    return value


def id_type(prefix: str) -> type[str]:
    return Annotated[str, AfterValidator(lambda value: validate_prefixed_id(prefix, value))]


def make_id_validator(prefix: str) -> Callable[[str], str]:
    return lambda value: validate_prefixed_id(prefix, value)


def validate_relationship_key(value: str) -> str:
    parts = value.split("__")
    if len(parts) != 2:
        raise ValueError("relationship id must be <from_id>__<to_id>")
    for part in parts:
        validate_prefixed_id("char", part)
    if parts[0] == parts[1]:
        raise ValueError("relationship id cannot reference the same character twice")
    return value
