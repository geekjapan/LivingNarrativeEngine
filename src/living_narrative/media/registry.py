"""Built-in image provider registry。"""

from collections.abc import Callable

from living_narrative.media.errors import ImageProviderRegistryError
from living_narrative.media.mock import MockImageProvider
from living_narrative.media.protocol import ImageProvider

ImageProviderFactory = Callable[[], ImageProvider]

_PROVIDERS: dict[str, ImageProviderFactory] = {"mock": MockImageProvider}


def registered_image_providers() -> list[str]:
    return sorted(_PROVIDERS)


def create_image_provider(name: str) -> ImageProvider:
    try:
        factory = _PROVIDERS[name]
    except KeyError as exc:
        raise ImageProviderRegistryError(
            f"Unknown image provider {name!r}; available providers: "
            f"{', '.join(registered_image_providers())}"
        ) from exc
    return factory()
