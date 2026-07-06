"""Shared fixtures for turn-pipeline / narration tests."""

from pathlib import Path
from typing import Any

import pytest
import yaml

from living_narrative.workspace.init import create_project


def _build_project(
    tmp_path: Path,
    *,
    title: str = "Test Project",
    reader_visible_facts: list[str] | None = None,
    hidden_facts: list[dict[str, Any]] | None = None,
    character_status: str = "alive",
    scene_status: str = "active",
    scene_summary: str = "",
    threats: list[dict[str, Any]] | None = None,
    emotions: dict[str, int] | None = None,
    emotions_baseline: dict[str, int] | None = None,
    emotion_decay_per_turn: int = 0,
) -> Path:
    """A minimal workspace with one character and one scene."""
    project_dir = tmp_path / "project"
    project_path = create_project(project_dir, title=title)
    state_dir = project_dir / "workspace" / "state"

    character = {"id": "char_001", "name": "Aoi", "role": "detective", "status": character_status}
    if emotions is not None:
        character["emotions"] = emotions
    if emotions_baseline is not None:
        character["emotions_baseline"] = emotions_baseline
    (state_dir / "characters" / "char_001.yaml").write_text(
        yaml.safe_dump(character, allow_unicode=True), encoding="utf-8"
    )

    scene = {
        "id": "scene_001",
        "location": "駅",
        "time": "夜",
        "active_characters": ["char_001"],
        "mood": "静寂",
        "status": scene_status,
        "summary": scene_summary,
        "reader_visible_facts": reader_visible_facts or [],
        "hidden_facts": hidden_facts or [],
    }
    (state_dir / "scenes" / "scene_001.yaml").write_text(
        yaml.safe_dump(scene, allow_unicode=True), encoding="utf-8"
    )

    world = {"id": "world_001", "name": "Test World", "summary": "A quiet test world."}
    if threats is not None:
        world["threats"] = threats
    if emotion_decay_per_turn:
        world["emotion_decay_per_turn"] = emotion_decay_per_turn
    (state_dir / "world.yaml").write_text(
        yaml.safe_dump(world, allow_unicode=True), encoding="utf-8"
    )

    return project_path


@pytest.fixture
def build_project():
    return _build_project
