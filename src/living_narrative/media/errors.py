"""Media境界で利用する型付きerror。"""


class MediaError(RuntimeError):
    """Image asset操作に失敗した。"""


class ImageProviderRegistryError(MediaError, ValueError):
    """未知の画像providerが指定された。"""


class AssetManifestError(MediaError, ValueError):
    """Asset manifestまたはその参照が不正。"""


class UnknownAssetError(AssetManifestError):
    """指定されたasset idがmanifestに存在しない。"""
