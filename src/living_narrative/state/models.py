"""Pydantic v2 models for ``project.yaml`` (spec-foundation.md D105)."""

import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator

AutonomyLevel = Literal["manual", "assist", "auto", "watch", "god"]
UserMode = Literal["watcher", "assistant_gm", "full_gm", "author", "player_character", "god"]
PromptRecording = Literal["full", "hash_only"]

_BINDING_KEY_FIXED = {
    "narrator",
    "world_simulator",
    "conflict_resolver",
    "state_manager",
    "checker",
    "interpreter",
    "character_default",
}
_BINDING_KEY_CHARACTER_RE = re.compile(r"^character:char_\d+$")


def _is_valid_binding_key(key: str) -> bool:
    return key in _BINDING_KEY_FIXED or bool(_BINDING_KEY_CHARACTER_RE.match(key))


class LLMConfig(BaseModel):
    provider: str
    model: str
    base_url: str | None = None
    timeout_seconds: int = Field(default=30, gt=0)
    prompt_recording: PromptRecording = "full"


class WorkspaceConfig(BaseModel):
    root: str
    state: str
    runs: str
    exports: str


class ProjectConfig(BaseModel):
    model_config = {"extra": "allow"}

    id: str
    title: str
    genre: str
    tone: str
    language: str = "ja"
    autonomy_level: AutonomyLevel
    user_mode: UserMode
    random_seed: str
    renderer: str
    llm: LLMConfig
    workspace: WorkspaceConfig
    llm_profiles: dict[str, LLMConfig] = Field(default_factory=dict)
    llm_bindings: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_llm_bindings(self) -> "ProjectConfig":
        for key, profile_name in self.llm_bindings.items():
            if not _is_valid_binding_key(key):
                raise ValueError(
                    f"llm_bindings key {key!r} is not a valid binding key "
                    "(expected one of "
                    f"{sorted(_BINDING_KEY_FIXED)} or 'character:char_<n>')"
                )
            if profile_name not in self.llm_profiles:
                raise ValueError(
                    f"llm_bindings[{key!r}] references undefined llm_profiles "
                    f"entry {profile_name!r}"
                )
        return self
