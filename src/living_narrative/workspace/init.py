"""``living-narrative init``: create a new project + workspace from a template.

The full ``--genre``/``--tone``/``--template``/``--output`` contract (cli/spec.md,
project-workspace/spec.md MODIFIED Requirement) replaces add-project-foundation's
``--title``-only version.
"""

import re
import shutil
import uuid
from pathlib import Path

import yaml

from living_narrative.state.models import ProjectConfig
from living_narrative.templates.registry import UnknownTemplateError, template_state_dir
from living_narrative.workspace.layout import STATE_SUBDIRS
from living_narrative.workspace.migrations import CURRENT_SCHEMA_VERSION

__all__ = ["InitDestinationExistsError", "UnknownTemplateError", "create_project"]


class InitDestinationExistsError(Exception):
    """Raised when the init output directory already exists and is not empty."""


def _slugify(title: str) -> str:
    ascii_title = title.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_title).strip("-").lower()
    return slug or "project"


def create_project(
    output_dir: Path,
    title: str,
    *,
    genre: str = "",
    tone: str = "",
    template: str = "minimal",
) -> Path:
    """Create a new project at ``output_dir`` from the named ``--template``.

    Returns the path to the generated ``project.yaml``. Raises ``UnknownTemplateError``
    for an unregistered template name (no silent fallback to ``minimal``).
    """
    template_dir = template_state_dir(template)  # raises UnknownTemplateError first (fail fast)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise InitDestinationExistsError(f"{output_dir} already exists and is not empty")

    project_data = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "id": _slugify(title),
        "title": title,
        "genre": genre,
        "tone": tone,
        "autonomy_level": "manual",
        "user_mode": "assistant_gm",
        "random_seed": uuid.uuid4().hex,
        "renderer": "novel",
        "llm": {"provider": "mock", "model": "mock-v1"},
        "workspace": {
            "root": "workspace",
            "state": "workspace/state",
            "runs": "workspace/runs",
            "exports": "workspace/exports",
        },
    }
    ProjectConfig.model_validate(project_data)

    output_dir.mkdir(parents=True, exist_ok=True)
    project_path = output_dir / "project.yaml"
    project_path.write_text(
        yaml.safe_dump(project_data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    state_dir = output_dir / "workspace" / "state"
    for subdir in STATE_SUBDIRS:
        (state_dir / subdir).mkdir(parents=True, exist_ok=True)
    shutil.copytree(template_dir, state_dir, dirs_exist_ok=True)
    # project-workspace/spec.md (add-project-foundation): factions.yaml is always
    # generated with an empty list, regardless of template (a template may still ship
    # its own non-empty factions.yaml, which wins here).
    factions_path = state_dir / "factions.yaml"
    if not factions_path.exists():
        factions_path.write_text("[]\n", encoding="utf-8")

    (output_dir / "workspace" / "runs").mkdir(parents=True, exist_ok=True)
    (output_dir / "workspace" / "exports").mkdir(parents=True, exist_ok=True)

    return project_path
