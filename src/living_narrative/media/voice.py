"""Provider boundary for optional voice asset generation."""

from pathlib import Path
from typing import Protocol

import yaml

from living_narrative.state.models import VoiceProfile


class VoiceProvider(Protocol):
    def generate(self, text: str, profile: VoiceProfile) -> bytes | Path:
        """Generate one asset from reader-visible speech and explicit voice direction."""


class MockVoiceProvider:
    """Deterministic audit provider that returns a UTF-8 text asset, never audio."""

    def generate(self, text: str, profile: VoiceProfile) -> bytes:
        payload = {
            "format": "living-narrative-mock-voice-asset-v1",
            "text": text,
            "profile": profile.model_dump(mode="json"),
        }
        return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False).encode()


__all__ = ["MockVoiceProvider", "VoiceProvider"]
