"""Convert the canonical VN script into an auditable provider-neutral TTS script."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from living_narrative.export_replay.vn_script import VNScript
from living_narrative.state.models import WorldStateBundle

RIGHTS_NOTICE = (
    "音声の生成・公開前に、声の権利と本人の同意、利用するproviderの規約・"
    "ライセンス・公開条件を確認してください。"
)


class TTSScriptError(Exception):
    """The canonical input could not be converted safely."""


class TTSVoiceProfile(BaseModel):
    """Strict artifact copy of provider-neutral state voice direction."""

    model_config = ConfigDict(extra="forbid", strict=True)

    quality: str = Field(min_length=1)
    pace: float = Field(default=1.0, gt=0)
    pitch: str | None = None
    notes: list[str] = Field(default_factory=list)


class TTSSegment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    turn: int = Field(ge=1)
    sequence: int = Field(ge=1)
    kind: Literal["dialogue", "narration"]
    text: str = Field(min_length=1)
    speaker: str | None = Field(default=None, min_length=1)
    voice: Literal["character", "narrator", "default"]
    profile: TTSVoiceProfile

    @field_validator("text")
    @classmethod
    def _reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("spoken text must not be blank")
        return value

    @field_validator("speaker")
    @classmethod
    def _reject_blank_speaker(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("speaker must not be blank")
        return value

    @model_validator(mode="after")
    def _validate_speaker_voice_contract(self) -> TTSSegment:
        if self.kind == "dialogue":
            if self.speaker is None:
                raise ValueError("dialogue requires speaker")
            if self.voice != "character":
                raise ValueError("dialogue requires character voice")
        else:
            if self.speaker is not None:
                raise ValueError("narration does not accept speaker")
            if self.voice not in {"narrator", "default"}:
                raise ValueError("narration requires narrator or default voice")
        return self


class TTSMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    rights_notice: Literal[RIGHTS_NOTICE]


class TTSScript(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    format: Literal["living-narrative-tts-script-v1"] = "living-narrative-tts-script-v1"
    metadata: TTSMetadata
    warnings: list[str] = Field(default_factory=list)
    segments: list[TTSSegment] = Field(default_factory=list)


def load_vn_script(path: Path) -> VNScript:
    if not path.exists():
        raise TTSScriptError(
            f"canonical VN script not found: {path} (run `export vn-script` first)"
        )
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TTSScriptError(f"invalid canonical VN script YAML: {exc}") from exc
    try:
        return VNScript.model_validate(raw)
    except ValidationError as exc:
        raise TTSScriptError(f"invalid canonical VN script schema: {exc}") from exc


def build_tts_script(script: VNScript, state: WorldStateBundle) -> TTSScript:
    """Keep only spoken commands, preserving order and refusing implicit voice fallback."""
    character_ids = {character.id for character in state.characters}
    profiles = {profile.character_id: profile for profile in state.voice_profiles.characters}
    segments: list[TTSSegment] = []
    warnings: list[str] = []
    sequence = 0
    for turn in script.turns:
        for command_number, command in enumerate(turn.commands, start=1):
            if command.kind not in {"dialogue", "narration"}:
                continue
            text = command.text
            if not text:
                continue
            if command.kind == "dialogue":
                speaker = command.character_id
                if speaker not in character_ids:
                    warnings.append(
                        f"turn {turn.turn} command {command_number}: unknown speaker {speaker!r}; "
                        "segment omitted"
                    )
                    continue
                profile = profiles.get(speaker)
                if profile is None:
                    warnings.append(
                        f"turn {turn.turn} command {command_number}: voice profile missing for "
                        f"speaker {speaker!r}; segment omitted"
                    )
                    continue
                voice = "character"
            else:
                speaker = None
                profile = state.voice_profiles.narrator
                voice = "narrator"
                if profile is None:
                    profile = state.voice_profiles.default
                    voice = "default"
                if profile is None:
                    warnings.append(
                        f"turn {turn.turn} command {command_number}: narrator/default voice "
                        "profile missing; segment omitted"
                    )
                    continue
            sequence += 1
            segments.append(
                TTSSegment(
                    turn=turn.turn,
                    sequence=sequence,
                    kind=command.kind,
                    text=text,
                    speaker=speaker,
                    voice=voice,
                    profile=TTSVoiceProfile(
                        quality=profile.quality,
                        pace=profile.pace,
                        pitch=profile.pitch,
                        notes=profile.notes,
                    ),
                )
            )
    return TTSScript(
        metadata=TTSMetadata(rights_notice=RIGHTS_NOTICE),
        warnings=warnings,
        segments=segments,
    )


def render_tts_script_markdown(script: TTSScript) -> str:
    lines = ["# TTS台本", "", f"> {RIGHTS_NOTICE}", ""]
    if script.warnings:
        lines.extend(("## warnings", ""))
        lines.extend(f"- {warning}" for warning in script.warnings)
        lines.append("")
    for segment in script.segments:
        label = segment.speaker or "narrator"
        lines.extend(
            (
                f"## {segment.sequence:04d} / turn {segment.turn} / {label}",
                "",
                segment.text,
                "",
                f"- voice: {segment.voice}",
                f"- quality: {segment.profile.quality}",
                f"- pace: {segment.profile.pace}",
            )
        )
        if segment.profile.pitch is not None:
            lines.append(f"- pitch: {segment.profile.pitch}")
        lines.extend(f"- note: {note}" for note in segment.profile.notes)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_tts_script_exports(output_dir: Path, script: TTSScript) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = output_dir / "tts_script.yaml"
    markdown_path = output_dir / "tts_script.md"
    _atomic_write(
        yaml_path,
        yaml.safe_dump(script.model_dump(mode="json"), allow_unicode=True, sort_keys=False),
    )
    _atomic_write(markdown_path, render_tts_script_markdown(script))
    return yaml_path, markdown_path


def _atomic_write(path: Path, content: str) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


__all__ = [
    "RIGHTS_NOTICE",
    "TTSScript",
    "TTSScriptError",
    "TTSSegment",
    "TTSMetadata",
    "TTSVoiceProfile",
    "build_tts_script",
    "load_vn_script",
    "render_tts_script_markdown",
    "write_tts_script_exports",
]
