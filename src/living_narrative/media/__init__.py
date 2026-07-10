"""画像provider、asset manifest、cacheの公開API。"""

from living_narrative.media.assets import (
    RIGHTS_NOTICE,
    AssetEntry,
    AssetManifest,
    generate_cached_asset,
    load_asset_manifest,
    resolve_assets_directory,
    save_asset_manifest,
    update_asset_status,
)
from living_narrative.media.errors import (
    AssetManifestError,
    ImageProviderRegistryError,
    MediaError,
    UnknownAssetError,
)
from living_narrative.media.mock import MockImageProvider
from living_narrative.media.protocol import ImageProvider
from living_narrative.media.registry import create_image_provider, registered_image_providers

__all__ = [
    "RIGHTS_NOTICE",
    "AssetEntry",
    "AssetManifest",
    "AssetManifestError",
    "ImageProvider",
    "ImageProviderRegistryError",
    "MediaError",
    "MockImageProvider",
    "UnknownAssetError",
    "create_image_provider",
    "generate_cached_asset",
    "load_asset_manifest",
    "registered_image_providers",
    "resolve_assets_directory",
    "save_asset_manifest",
    "update_asset_status",
]
