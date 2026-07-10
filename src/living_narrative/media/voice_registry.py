"""Built-in voice provider factory registry。"""

from collections.abc import Callable

from living_narrative.media.errors import VoiceProviderRegistryError
from living_narrative.media.voice import MockVoiceProvider, VoiceProvider

VoiceProviderFactory = Callable[[], VoiceProvider]

_PROVIDERS: dict[str, VoiceProviderFactory] = {"mock": MockVoiceProvider}


def registered_voice_providers() -> list[str]:
    return sorted(_PROVIDERS)


def create_voice_provider(name: str) -> VoiceProvider:
    try:
        factory = _PROVIDERS[name]
    except KeyError as exc:
        raise VoiceProviderRegistryError(
            f"Unknown voice provider {name!r}; available providers: "
            f"{', '.join(registered_voice_providers())}"
        ) from exc
    return factory()
