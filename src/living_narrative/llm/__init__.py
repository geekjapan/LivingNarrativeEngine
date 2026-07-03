"""LLM provider abstraction and built-in providers."""

from living_narrative.llm.errors import (
    FixtureResponseError,
    ProviderConnectionError,
    ProviderRegistryError,
    StructuredOutputError,
)
from living_narrative.llm.metadata import CallMetadata, PromptRecord
from living_narrative.llm.mock import MockProvider
from living_narrative.llm.openai_compatible import OpenAICompatibleProvider
from living_narrative.llm.profiles import ResolvedLLMProfile, resolve_llm_profile
from living_narrative.llm.protocol import Provider
from living_narrative.llm.registry import create_provider, registered_providers
from living_narrative.llm.structured import compute_prompt_hash

__all__ = [
    "CallMetadata",
    "FixtureResponseError",
    "MockProvider",
    "OpenAICompatibleProvider",
    "PromptRecord",
    "Provider",
    "ProviderConnectionError",
    "ProviderRegistryError",
    "ResolvedLLMProfile",
    "StructuredOutputError",
    "compute_prompt_hash",
    "create_provider",
    "registered_providers",
    "resolve_llm_profile",
]
