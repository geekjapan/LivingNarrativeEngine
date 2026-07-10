"""``init --template`` registry (cli/spec.md, project-workspace/spec.md MODIFIED Requirement).

Each template is a directory containing a ``state/`` subtree that is copied verbatim into
the new project's ``workspace/state/`` (project.yaml itself is always generated fresh by
``workspace.init.create_project``, never templated, since it needs per-invocation fields
like ``id``/``random_seed``).
"""

from pathlib import Path

_TEMPLATES_ROOT = Path(__file__).parent

TEMPLATE_NAMES = ("minimal", "mist_station", "orbital_echo")


class UnknownTemplateError(Exception):
    """Raised for an ``--template`` name outside ``TEMPLATE_NAMES`` (no silent fallback)."""


def template_state_dir(name: str) -> Path:
    if name not in TEMPLATE_NAMES:
        raise UnknownTemplateError(
            f"unknown template {name!r} (available: {', '.join(TEMPLATE_NAMES)})"
        )
    return _TEMPLATES_ROOT / name / "state"
