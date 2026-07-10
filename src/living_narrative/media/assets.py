"""画像asset cacheと厳密なYAML manifest。"""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
)

from living_narrative.media.errors import AssetManifestError, UnknownAssetError
from living_narrative.media.protocol import ImageProvider

RIGHTS_NOTICE = "生成物の権利・利用条件および入力データの保持・学習利用はproviderに依存します。"
AssetId = Annotated[str, StringConstraints(pattern=r"^asset_[0-9a-f]{32}$", strict=True)]
Hash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$", strict=True)]


class AssetEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: AssetId
    prompt_hash: Hash
    provider: Annotated[str, StringConstraints(min_length=1, strict=True)]
    profile: Annotated[str, StringConstraints(min_length=1, strict=True)]
    path: Annotated[str, StringConstraints(min_length=1, strict=True)]
    generated_at: datetime
    status: Literal["pending", "accepted", "discarded"] = "pending"
    rights_notice: Annotated[str, StringConstraints(min_length=1, strict=True)]

    @field_validator("path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or "." in path.parts or "\\" in value:
            raise ValueError("path must be a normalized relative POSIX path")
        return value


class AssetManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    rights_notice: Annotated[str, StringConstraints(min_length=1, strict=True)] = RIGHTS_NOTICE
    assets: list[AssetEntry] = Field(default_factory=list)

    @field_validator("assets")
    @classmethod
    def unique_assets(cls, assets: list[AssetEntry]) -> list[AssetEntry]:
        ids = [asset.id for asset in assets]
        paths = [asset.path for asset in assets]
        if len(ids) != len(set(ids)):
            raise ValueError("asset ids must be unique")
        if len(paths) != len(set(paths)):
            raise ValueError("asset paths must be unique")
        return assets


def prompt_content_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def load_asset_manifest(assets_dir: Path) -> AssetManifest:
    _reject_unsafe_assets_dir(assets_dir)
    path = assets_dir / "assets.yaml"
    if path.is_symlink():
        raise AssetManifestError(f"asset manifest must not be a symlink: {path}")
    if not path.exists():
        return AssetManifest()
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        return AssetManifest.model_validate(payload)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise AssetManifestError(f"invalid asset manifest {path}: {exc}") from exc


def generate_cached_asset(
    assets_dir: Path,
    *,
    prompt: str,
    provider_name: str,
    profile: str,
    provider: ImageProvider,
    now: datetime | None = None,
) -> AssetEntry:
    manifest = load_asset_manifest(assets_dir)
    prompt_hash = prompt_content_hash(prompt)
    key_hash = hashlib.sha256(f"{prompt_hash}\0{provider_name}\0{profile}".encode()).hexdigest()
    asset_id = f"asset_{key_hash[:32]}"
    for asset in manifest.assets:
        if (asset.prompt_hash, asset.provider, asset.profile) == (
            prompt_hash,
            provider_name,
            profile,
        ):
            _resolve_asset_path(assets_dir, asset.path, must_exist=True)
            return asset
        if asset.id == asset_id:
            raise AssetManifestError(f"asset id collision: {asset_id}")

    relative_path = f"files/{asset_id}.svg"
    destination = _resolve_asset_path(assets_dir, relative_path)
    if destination.exists() or destination.is_symlink():
        raise AssetManifestError(f"asset path collision: {relative_path}")
    output = provider.generate(prompt, profile)
    data = output if isinstance(output, bytes) else _read_provider_path(output)
    entry = AssetEntry(
        id=asset_id,
        prompt_hash=prompt_hash,
        provider=provider_name,
        profile=profile,
        path=relative_path,
        generated_at=now or datetime.now(UTC),
        rights_notice=RIGHTS_NOTICE,
    )
    _atomic_write_bytes(destination, data)
    updated = manifest.model_copy(update={"assets": [*manifest.assets, entry]})
    try:
        save_asset_manifest(assets_dir, updated)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return entry


def update_asset_status(
    assets_dir: Path, asset_id: str, status: Literal["accepted", "discarded"]
) -> AssetEntry:
    manifest = load_asset_manifest(assets_dir)
    matches = [index for index, asset in enumerate(manifest.assets) if asset.id == asset_id]
    if not matches:
        raise UnknownAssetError(f"unknown asset: {asset_id}")
    index = matches[0]
    existing = manifest.assets[index]
    _resolve_asset_path(assets_dir, existing.path, must_exist=True)
    updated_entry = existing.model_copy(update={"status": status})
    assets = [*manifest.assets]
    assets[index] = updated_entry
    save_asset_manifest(assets_dir, manifest.model_copy(update={"assets": assets}))
    return updated_entry


def save_asset_manifest(assets_dir: Path, manifest: AssetManifest) -> Path:
    _reject_unsafe_assets_dir(assets_dir)
    validated = AssetManifest.model_validate(manifest.model_dump(mode="python"))
    path = assets_dir / "assets.yaml"
    if path.is_symlink():
        raise AssetManifestError(f"asset manifest must not be a symlink: {path}")
    text = yaml.safe_dump(validated.model_dump(mode="python"), allow_unicode=True, sort_keys=False)
    _atomic_write_bytes(path, text.encode("utf-8"))
    return path


def resolve_assets_directory(exports_dir: Path) -> Path:
    """exports配下の非symlinkなassets directoryだけを許可する。"""
    exports_root = exports_dir.resolve()
    assets_dir = exports_dir / "assets"
    if assets_dir.is_symlink():
        raise AssetManifestError(f"assets directory must not be a symlink: {assets_dir}")
    resolved = assets_dir.resolve()
    if not resolved.is_relative_to(exports_root):
        raise AssetManifestError(f"assets directory escapes exports directory: {assets_dir}")
    return assets_dir


def _resolve_asset_path(assets_dir: Path, relative_path: str, *, must_exist: bool = False) -> Path:
    _reject_unsafe_assets_dir(assets_dir)
    AssetEntry.validate_relative_path(relative_path)
    root = assets_dir.resolve()
    candidate = (root / relative_path).resolve()
    if not candidate.is_relative_to(root):
        raise AssetManifestError(f"asset path escapes assets directory: {relative_path}")
    if must_exist and (not candidate.is_file() or candidate.is_symlink()):
        raise AssetManifestError(f"asset file is missing or unsafe: {relative_path}")
    return candidate


def _reject_unsafe_assets_dir(assets_dir: Path) -> None:
    if assets_dir.is_symlink():
        raise AssetManifestError(f"assets directory must not be a symlink: {assets_dir}")


def _read_provider_path(path: Path) -> bytes:
    try:
        if not path.is_file() or path.is_symlink():
            raise AssetManifestError("provider returned a missing or unsafe path")
        return path.read_bytes()
    except OSError as exc:
        raise AssetManifestError(f"cannot read provider output: {exc}") from exc


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
