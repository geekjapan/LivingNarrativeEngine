"""画像生成providerの最小境界。"""

from pathlib import Path
from typing import Protocol


class ImageProvider(Protocol):
    """Promptから画像assetを生成するprovider。"""

    def generate(self, prompt: str, profile: str) -> bytes | Path:
        """生成済みbytesまたはローカルPathを返す。"""
