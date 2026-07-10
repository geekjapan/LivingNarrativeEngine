import pytest
import yaml

from living_narrative.media import (
    MediaError,
    MockVoiceProvider,
    VoiceProviderRegistryError,
    create_voice_provider,
    registered_voice_providers,
)
from living_narrative.state.models import VoiceProfile


def test_mock_voice_provider_returns_deterministic_auditable_text_asset():
    provider = MockVoiceProvider()
    profile = VoiceProfile(quality="静かな声", pace=0.9, notes=["明瞭に"])

    first = provider.generate("霧が晴れた。", profile)
    second = provider.generate("霧が晴れた。", profile)

    assert first == second
    assert isinstance(first, bytes)
    payload = yaml.safe_load(first.decode())
    assert payload["text"] == "霧が晴れた。"
    assert payload["profile"] == profile.model_dump(mode="json")


def test_voice_provider_registry_lists_and_creates_mock():
    assert registered_voice_providers() == ["mock"]
    assert isinstance(create_voice_provider("mock"), MockVoiceProvider)
    assert create_voice_provider("mock") is not create_voice_provider("mock")


def test_voice_provider_registry_raises_typed_media_error_for_unknown_provider():
    with pytest.raises(VoiceProviderRegistryError, match="Unknown voice provider") as unknown:
        create_voice_provider("real-api")

    assert isinstance(unknown.value, MediaError)
