"""Built-in provider registry."""

from collections.abc import Callable

from living_narrative.llm.errors import ProviderRegistryError
from living_narrative.llm.mock import MockProvider
from living_narrative.llm.openai_compatible import OpenAICompatibleProvider
from living_narrative.llm.protocol import Provider
from living_narrative.state.models import LLMConfig

ProviderFactory = Callable[..., Provider]

_PROVIDERS: dict[str, ProviderFactory] = {
    "mock": MockProvider,
    "openai-compatible": OpenAICompatibleProvider,
    "openai": OpenAICompatibleProvider,
}


def registered_providers() -> list[str]:
    return sorted(_PROVIDERS)


def create_provider(config: LLMConfig, **kwargs: object) -> Provider:
    try:
        factory = _PROVIDERS[config.provider]
    except KeyError as exc:
        raise ProviderRegistryError(
            f"Unknown LLM provider {config.provider!r}; available providers: "
            f"{', '.join(registered_providers())}"
        ) from exc
    return factory(config, **kwargs)
