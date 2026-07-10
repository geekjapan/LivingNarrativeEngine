"""Resolves llm-provider profiles by binding key and records call metadata (D122)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from living_narrative.llm.metadata import CallMetadata
from living_narrative.llm.profiles import resolve_llm_profile
from living_narrative.state.models import ProjectConfig

if TYPE_CHECKING:
    from living_narrative.plugins import PluginRuntime


@dataclass
class LLMGateway:
    project: ProjectConfig
    random_seed: str = ""
    calls: list[CallMetadata] = field(default_factory=list)
    scripted_responses: dict[str, Any] = field(default_factory=dict)
    runtime: PluginRuntime | None = None

    def __post_init__(self) -> None:
        if self.runtime is None:
            from living_narrative.plugins import create_plugin_runtime

            self.runtime = create_plugin_runtime(self.project)

    def complete(
        self,
        binding_key: str,
        messages: list[dict[str, Any]],
        response_schema: type[BaseModel],
        prompt_template_name: str,
    ) -> BaseModel:
        profile = resolve_llm_profile(self.project, binding_key)
        kwargs: dict[str, Any] = {"profile_name": profile.name}
        if profile.config.provider == "mock":
            kwargs["random_seed"] = self.random_seed
            kwargs["scripted_responses"] = self.scripted_responses

        def _record(metadata: CallMetadata) -> None:
            self.calls.append(metadata.model_copy(update={"binding_key": binding_key}))

        assert self.runtime is not None
        provider = self.runtime.create_llm_provider(profile.config, recorder=_record, **kwargs)
        return provider.complete(
            messages, response_schema, prompt_template_name=prompt_template_name
        )
