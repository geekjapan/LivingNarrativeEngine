"""LLM profile resolution."""

from dataclasses import dataclass

from living_narrative.state.models import LLMConfig, ProjectConfig


@dataclass(frozen=True)
class ResolvedLLMProfile:
    name: str
    binding_key: str
    config: LLMConfig


def resolve_llm_profile(project: ProjectConfig, binding_key: str) -> ResolvedLLMProfile:
    if binding_key.startswith("character:"):
        candidates = [binding_key, "character_default"]
    else:
        candidates = [binding_key]

    for candidate in candidates:
        profile_name = project.llm_bindings.get(candidate)
        if profile_name is not None:
            return ResolvedLLMProfile(
                name=profile_name,
                binding_key=binding_key,
                config=project.llm_profiles[profile_name],
            )
    return ResolvedLLMProfile(name="default", binding_key=binding_key, config=project.llm)
