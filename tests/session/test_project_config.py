import pytest
from pydantic import ValidationError

from living_narrative.state.models import ProjectConfig


def _project(**overrides):
    data = {
        "id": "project",
        "title": "Title",
        "genre": "mystery",
        "tone": "quiet",
        "autonomy_level": "assist",
        "user_mode": "assistant_gm",
        "random_seed": "seed",
        "renderer": "novel",
        "llm": {"provider": "mock", "model": "mock-v1"},
        "workspace": {
            "root": "workspace",
            "state": "workspace/state",
            "runs": "workspace/runs",
            "exports": "workspace/exports",
        },
    }
    data.update(overrides)
    return data


def test_stop_conditions_valid_settings_load():
    config = ProjectConfig.model_validate(
        _project(
            stop_conditions={
                "heavy_roll_failure": {"enabled": False},
                "relationship_threshold_crossing": {"threshold": 30},
            }
        )
    )

    assert config.stop_conditions["heavy_roll_failure"].enabled is False
    assert config.stop_conditions["relationship_threshold_crossing"].threshold == 30


def test_stop_condition_key_is_rejected():
    with pytest.raises(ValidationError, match="stop_condition cannot be disabled"):
        ProjectConfig.model_validate(
            _project(stop_conditions={"stop_condition": {"enabled": False}})
        )


def test_player_character_requires_player_char_id():
    with pytest.raises(ValidationError, match="player_char_id is required"):
        ProjectConfig.model_validate(_project(user_mode="player_character"))


def test_player_char_id_is_rejected_for_other_modes():
    with pytest.raises(ValidationError, match="only valid"):
        ProjectConfig.model_validate(_project(player_char_id="char_001"))
