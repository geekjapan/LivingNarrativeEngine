import pytest
from pydantic import ValidationError

from living_narrative.state.models import LLMConfig, ProjectConfig, WorkspaceConfig

VALID_PROJECT = {
    "id": "mist_station",
    "title": "霧の駅",
    "genre": "mystery_fantasy",
    "tone": "quiet_ominous",
    "autonomy_level": "assist",
    "user_mode": "assistant_gm",
    "random_seed": "20260703-mist-station",
    "renderer": "novel",
    "llm": {"provider": "mock", "model": "mock-v1"},
    "workspace": {
        "root": "workspace",
        "state": "workspace/state",
        "runs": "workspace/runs",
        "exports": "workspace/exports",
    },
}


def test_loads_appendix_b_project():
    config = ProjectConfig.model_validate(VALID_PROJECT)
    assert config.id == "mist_station"
    assert config.language == "ja"
    assert config.llm == LLMConfig(provider="mock", model="mock-v1")
    assert config.workspace == WorkspaceConfig(**VALID_PROJECT["workspace"])


def test_language_defaults_to_ja_when_absent():
    assert "language" not in VALID_PROJECT
    config = ProjectConfig.model_validate(VALID_PROJECT)
    assert config.language == "ja"


def test_unknown_top_level_field_is_allowed():
    data = {**VALID_PROJECT, "some_future_field": "value"}
    config = ProjectConfig.model_validate(data)
    assert config.model_extra == {"some_future_field": "value"}


def test_invalid_autonomy_level_rejected():
    data = {**VALID_PROJECT, "autonomy_level": "not_a_level"}
    with pytest.raises(ValidationError):
        ProjectConfig.model_validate(data)


def test_timeout_seconds_must_be_positive():
    data = {**VALID_PROJECT, "llm": {"provider": "mock", "model": "mock-v1", "timeout_seconds": 0}}
    with pytest.raises(ValidationError):
        ProjectConfig.model_validate(data)


def test_llm_bindings_reference_defined_profile():
    data = {
        **VALID_PROJECT,
        "llm_profiles": {"fast": {"provider": "mock", "model": "mock-v1"}},
        "llm_bindings": {"narrator": "fast", "character:char_001": "fast"},
    }
    config = ProjectConfig.model_validate(data)
    assert config.llm_bindings["narrator"] == "fast"


def test_llm_bindings_undefined_profile_rejected():
    data = {**VALID_PROJECT, "llm_bindings": {"narrator": "undefined_profile"}}
    with pytest.raises(ValidationError):
        ProjectConfig.model_validate(data)


def test_llm_bindings_invalid_key_rejected():
    data = {
        **VALID_PROJECT,
        "llm_profiles": {"fast": {"provider": "mock", "model": "mock-v1"}},
        "llm_bindings": {"not_a_valid_binding_key": "fast"},
    }
    with pytest.raises(ValidationError):
        ProjectConfig.model_validate(data)
