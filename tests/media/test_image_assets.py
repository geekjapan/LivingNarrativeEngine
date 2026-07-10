from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from living_narrative.media import (
    AssetManifestError,
    ImageProviderRegistryError,
    MockImageProvider,
    create_image_provider,
    generate_cached_asset,
    load_asset_manifest,
    update_asset_status,
)


class CountingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str, profile: str) -> bytes:
        self.calls += 1
        return f"{prompt}:{profile}".encode()


def test_registry_contains_only_deterministic_mock() -> None:
    provider = create_image_provider("mock")

    assert isinstance(provider, MockImageProvider)
    assert provider.generate("scene", "draft") == provider.generate("scene", "draft")
    with pytest.raises(ImageProviderRegistryError, match="Unknown image provider"):
        create_image_provider("real-api")


def test_cache_hit_skips_provider_and_preserves_status_history(tmp_path: Path) -> None:
    provider = CountingProvider()
    generated_at = datetime(2026, 7, 11, tzinfo=UTC)

    first = generate_cached_asset(
        tmp_path,
        prompt="a quiet station",
        provider_name="mock",
        profile="draft",
        provider=provider,
        now=generated_at,
    )
    accepted = update_asset_status(tmp_path, first.id, "accepted")
    second = generate_cached_asset(
        tmp_path,
        prompt="a quiet station",
        provider_name="mock",
        profile="draft",
        provider=provider,
    )

    assert provider.calls == 1
    assert second == accepted
    assert second.status == "accepted"
    assert len(load_asset_manifest(tmp_path).assets) == 1


def test_provider_and_profile_are_part_of_cache_key(tmp_path: Path) -> None:
    provider = CountingProvider()

    first = generate_cached_asset(
        tmp_path, prompt="scene", provider_name="mock", profile="a", provider=provider
    )
    second = generate_cached_asset(
        tmp_path, prompt="scene", provider_name="mock", profile="b", provider=provider
    )

    assert provider.calls == 2
    assert first.id != second.id
    assert len(load_asset_manifest(tmp_path).assets) == 2


@pytest.mark.parametrize(
    "bad_path",
    ["../secret.svg", "/tmp/secret.svg", "files/../../secret.svg", r"files\secret.svg"],
)
def test_manifest_rejects_path_traversal_and_non_posix_paths(tmp_path: Path, bad_path: str) -> None:
    (tmp_path / "assets.yaml").write_text(
        yaml.safe_dump(
            {
                "rights_notice": "notice",
                "assets": [
                    {
                        "id": "asset_0123456789abcdef0123456789abcdef",
                        "prompt_hash": "0" * 64,
                        "provider": "mock",
                        "profile": "default",
                        "path": bad_path,
                        "generated_at": datetime(2026, 7, 11, tzinfo=UTC),
                        "status": "pending",
                        "rights_notice": "notice",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(AssetManifestError, match="invalid asset manifest"):
        load_asset_manifest(tmp_path)


def test_manifest_rejects_extra_fields_and_wrong_types(tmp_path: Path) -> None:
    (tmp_path / "assets.yaml").write_text(
        yaml.safe_dump({"rights_notice": "notice", "assets": "not-a-list", "extra": True}),
        encoding="utf-8",
    )

    with pytest.raises(AssetManifestError, match="invalid asset manifest"):
        load_asset_manifest(tmp_path)


def test_manifest_replace_failure_keeps_previous_history(tmp_path: Path, monkeypatch) -> None:
    provider = CountingProvider()
    first = generate_cached_asset(
        tmp_path, prompt="first", provider_name="mock", profile="default", provider=provider
    )
    original = (tmp_path / "assets.yaml").read_bytes()
    import living_narrative.media.assets as assets_module

    real_replace = assets_module.os.replace

    def fail_manifest_replace(source: Path, destination: Path) -> None:
        if destination.name == "assets.yaml":
            raise OSError("simulated manifest replace failure")
        real_replace(source, destination)

    monkeypatch.setattr(assets_module.os, "replace", fail_manifest_replace)

    with pytest.raises(OSError, match="simulated"):
        generate_cached_asset(
            tmp_path, prompt="second", provider_name="mock", profile="default", provider=provider
        )

    assert (tmp_path / "assets.yaml").read_bytes() == original
    assert [asset.id for asset in load_asset_manifest(tmp_path).assets] == [first.id]
    assert not list((tmp_path / "files").glob(".*.tmp"))
