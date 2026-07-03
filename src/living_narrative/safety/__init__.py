"""Consistency checker framework."""

from living_narrative.safety.registry import (
    CheckRunResult,
    Finding,
    register_checker,
    run_checkers,
    write_checks_yaml,
)

__all__ = [
    "CheckRunResult",
    "Finding",
    "register_checker",
    "run_checkers",
    "write_checks_yaml",
]
