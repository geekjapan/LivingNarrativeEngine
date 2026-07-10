"""Deterministic, reader-only VN script export (Issue 042).

Only the published ``narration.md`` body and its canonical adoption metadata
(``meta.yaml``/``review.yaml``) are loaded. Project state, character files, and ``gm_vault``
are deliberately outside this module's input boundary.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from living_narrative.llm.errors import ProviderConnectionError, StructuredOutputError
from living_narrative.pipeline.llm_gateway import LLMGateway
from living_narrative.state.models import WorldStateBundle

_COMMENT_DIRECTIVE = re.compile(r"^#\s*(BACKGROUND|BGM|SFX|SPRITE):\s*(.+)$")
_DIALOGUE = re.compile(r"^(char_[A-Za-z0-9_-]+|UNKNOWN):\s*(.+)$")
_NARRATOR = re.compile(r"^NARRATOR:\s*(.*)$")
_TURN_DIR = re.compile(r"^turn_(\d+)$")
_CHARACTER_ID = re.compile(r"^char_\d+$")

DEFAULT_VN_PROFILE = "narrator"
PROMPT_TEMPLATE_NAME = "export-vn-script-v1"
SYSTEM_PROMPT = """\
あなたはreader可視の小説本文をビジュアルノベル台本へ構造化する編集者です。
入力のnarrationにない事実・人物・台詞・演出を発明してはいけません。
speakerとspriteはallowed_character_ids、backgroundはallowed_background_idsにあるIDだけを使い、
本文から判断できない値はnullにしてください。typeはdialogue、narration、directionのいずれかです。
"""


class VNScriptError(RuntimeError):
    """The run contains no reader-visible narration to export."""


class VNCommand(BaseModel):
    kind: Literal["background", "bgm", "sfx", "sprite", "dialogue", "narration", "direction"]
    text: str | None = None
    character_id: str | None = None

    @model_validator(mode="after")
    def _require_kind_value(self) -> VNCommand:
        if self.kind in {"sprite", "dialogue"} and not self.character_id:
            raise ValueError(f"{self.kind} requires character_id")
        if self.character_id is not None and not _CHARACTER_ID.fullmatch(self.character_id):
            raise ValueError("character_id must match char_NNN")
        if self.kind != "sprite" and not self.text:
            raise ValueError(f"{self.kind} requires text")
        if self.kind == "sprite" and self.text is not None:
            raise ValueError("sprite does not accept text")
        if self.kind not in {"sprite", "dialogue"} and self.character_id is not None:
            raise ValueError(f"{self.kind} does not accept character_id")
        return self


class VNTurn(BaseModel):
    turn: int
    commands: list[VNCommand] = Field(default_factory=list)


class VNScript(BaseModel):
    format: Literal["living-narrative-vn-script-v1"] = "living-narrative-vn-script-v1"
    warnings: list[str] = Field(default_factory=list)
    turns: list[VNTurn] = Field(default_factory=list)


class VNLineOutput(BaseModel):
    type: Literal["dialogue", "narration", "direction"]
    speaker: str | None = None
    text: str = Field(min_length=1)
    sprite: str | None = None
    background: str | None = None


class VNTurnOutput(BaseModel):
    lines: list[VNLineOutput] = Field(min_length=1)


def build_vn_script(records: list[tuple[int, str]]) -> VNScript:
    """Extract structure from reader-visible narrator bodies without consulting state."""
    turns = [VNTurn(turn=turn, commands=_parse_narration(body)) for turn, body in records if body]
    if not turns:
        raise VNScriptError("no reader-visible narration exists yet — run `turn`/`auto` first")
    return VNScript(turns=turns)


def export_vn_script(runs_dir: Path, output_dir: Path) -> tuple[Path, Path]:
    result = build_vn_script(load_reader_narrations(runs_dir))
    output_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = output_dir / "script.yaml"
    markdown_path = output_dir / "script.md"
    _atomic_write(
        yaml_path,
        yaml.safe_dump(result.model_dump(mode="json"), allow_unicode=True, sort_keys=False),
    )
    _atomic_write(markdown_path, render_vn_script_markdown(result))
    return yaml_path, markdown_path


def generate_vn_script(
    records: list[tuple[int, str]],
    gateway: LLMGateway,
    *,
    allowed_character_ids: set[str],
    allowed_background_ids: set[str],
    profile: str = DEFAULT_VN_PROFILE,
) -> VNScript:
    """Use an export-only LLM pass, then enforce reference allowlists deterministically."""
    turns: list[VNTurn] = []
    warnings: list[str] = []
    for turn, narration in records:
        payload = {
            "turn": turn,
            "narration": narration,
            "allowed_character_ids": sorted(allowed_character_ids),
            "allowed_background_ids": sorted(allowed_background_ids),
        }
        try:
            output = gateway.complete(
                profile,
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                VNTurnOutput,
                prompt_template_name=PROMPT_TEMPLATE_NAME,
            )
        except (ProviderConnectionError, StructuredOutputError) as exc:
            raise VNScriptError(f"VN script LLM formatting failed for turn {turn}: {exc}") from exc
        if not isinstance(output, VNTurnOutput):
            raise VNScriptError(
                f"VN script LLM formatting failed for turn {turn}: expected VNTurnOutput"
            )
        commands: list[VNCommand] = []
        for line_number, line in enumerate(output.lines, start=1):
            prefix = f"turn {turn} line {line_number}"
            if line.background is not None:
                if line.background in allowed_background_ids:
                    commands.append(VNCommand(kind="background", text=line.background))
                else:
                    warnings.append(f"{prefix}: unknown background {line.background!r} removed")
            if line.sprite is not None:
                if line.sprite in allowed_character_ids:
                    commands.append(VNCommand(kind="sprite", character_id=line.sprite))
                else:
                    warnings.append(f"{prefix}: unavailable sprite {line.sprite!r} removed")
            if line.type == "dialogue":
                if line.speaker in allowed_character_ids:
                    commands.append(
                        VNCommand(kind="dialogue", character_id=line.speaker, text=line.text)
                    )
                else:
                    warnings.append(f"{prefix}: unknown speaker {line.speaker!r}; used narration")
                    commands.append(VNCommand(kind="narration", text=line.text))
            else:
                commands.append(VNCommand(kind=line.type, text=line.text))
        turns.append(VNTurn(turn=turn, commands=commands))
    if not turns:
        raise VNScriptError("no reader-visible narration exists yet — run `turn`/`auto` first")
    return VNScript(turns=turns, warnings=warnings)


def visual_reference_allowlists(state: WorldStateBundle) -> tuple[set[str], set[str]]:
    """Reduce state to opaque IDs before any value crosses the LLM boundary."""
    characters = {
        character.id
        for character in state.characters
        if character.visual_profile is not None and _CHARACTER_ID.fullmatch(character.id)
    }
    backgrounds = {background.id for background in state.visual_profiles.backgrounds}
    return characters, backgrounds


def write_vn_script_exports(output_dir: Path, result: VNScript) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = output_dir / "script.yaml"
    markdown_path = output_dir / "script.md"
    _atomic_write(
        yaml_path,
        yaml.safe_dump(result.model_dump(mode="json"), allow_unicode=True, sort_keys=False),
    )
    _atomic_write(markdown_path, render_vn_script_markdown(result))
    return yaml_path, markdown_path


def load_reader_narrations(runs_dir: Path) -> list[tuple[int, str]]:
    """Read reader-visible narration for canonical applied, non-rejected body turns."""
    if not runs_dir.exists():
        return []
    records: list[tuple[int, str]] = []
    for turn_dir in runs_dir.iterdir():
        match = _TURN_DIR.match(turn_dir.name)
        narration_path = turn_dir / "narration.md"
        if not match or not turn_dir.is_dir() or not narration_path.exists():
            continue
        meta = _load_yaml_mapping(turn_dir / "meta.yaml")
        review = _load_yaml_mapping(turn_dir / "review.yaml")
        if meta.get("status") != "applied" or review.get("decision") == "reject_all":
            continue
        raw = narration_path.read_text(encoding="utf-8")
        header, separator, body = raw.partition("---\n\n")
        if not separator or "visibility: reader" not in header.splitlines():
            continue
        records.append((int(match.group(1)), body.rstrip("\n")))
    return sorted(records)


def _load_yaml_mapping(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def render_vn_script_markdown(script: VNScript) -> str:
    lines = ["# VN台本", ""]
    if script.warnings:
        lines.extend(("## warnings", ""))
        lines.extend(f"- {warning}" for warning in script.warnings)
        lines.append("")
    for turn in script.turns:
        lines.extend((f"## ターン {turn.turn}", ""))
        for command in turn.commands:
            if command.kind == "dialogue":
                lines.append(f"**{command.character_id}**: {command.text}")
            elif command.kind == "narration":
                lines.append(command.text or "")
            elif command.kind == "sprite":
                lines.append(f"<!-- SPRITE: {command.character_id} -->")
            else:
                lines.append(f"<!-- {command.kind.upper()}: {command.text} -->")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _parse_narration(body: str) -> list[VNCommand]:
    commands: list[VNCommand] = []
    narrative_lines: list[str] = []

    def flush_narration() -> None:
        if narrative_lines:
            commands.append(VNCommand(kind="narration", text="\n".join(narrative_lines)))
            narrative_lines.clear()

    for line in body.splitlines():
        if match := _COMMENT_DIRECTIVE.match(line):
            flush_narration()
            name, value = match.groups()
            if name == "SPRITE":
                commands.append(VNCommand(kind="sprite", character_id=value))
            else:
                commands.append(VNCommand(kind=name.lower(), text=value))
        elif match := _DIALOGUE.match(line):
            flush_narration()
            commands.append(
                VNCommand(kind="dialogue", character_id=match.group(1), text=match.group(2))
            )
        elif match := _NARRATOR.match(line):
            narrative_lines.append(match.group(1))
        else:
            narrative_lines.append(line)
    flush_narration()
    return commands


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)
