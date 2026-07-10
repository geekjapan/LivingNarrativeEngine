"""Auditable, scene-level image prompt export (docs/issues/040).

This module prepares prompts only.  It deliberately has no image-provider, cache, or asset
generation behavior; those belong to Issue 041.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from living_narrative.export_replay.reconstruction import SessionReconstruction
from living_narrative.llm.errors import ProviderConnectionError, StructuredOutputError
from living_narrative.pipeline.llm_gateway import LLMGateway
from living_narrative.state.models import (
    BackgroundVisualProfile,
    CharacterState,
    SceneState,
    StyleLockProfile,
    WorldStateBundle,
)

DEFAULT_IMAGE_PROMPT_PROFILE = "narrator"
PROMPT_TEMPLATE_NAME = "export-image-prompt-v1"
RIGHTS_NOTICE = "生成画像の権利・利用条件はproviderに依存します。"

SYSTEM_PROMPT = """\
あなたは物語のシーンを画像生成用プロンプトへ変換する編集者です。
入力されたsceneとvisual profileだけを使用し、素材にない人物・物・設定を追加しないでください。

## 出力
- japanese_description: 読者向けの簡潔な日本語シーン説明。
- english_prompt: 画像生成providerへ渡す、具体的な英語のシーン描写。

character_appearance_lock、background_lock、style_lockはカット間の一貫性を保つ固定条件です。
英語promptには全固定条件を反映してください。隠し設定の推測や画像生成は行わないでください。
"""


class ImagePromptError(RuntimeError):
    """Image-prompt export input or generation failed."""


class MissingVisualProfileError(ImagePromptError):
    """A scene cannot be rendered consistently because a required profile is absent."""


class EmptySceneError(ImagePromptError):
    """The reconstruction contains no scene to export."""


class ImagePromptLLMOutput(BaseModel):
    model_config = {"str_strip_whitespace": True}

    japanese_description: str = Field(min_length=1)
    english_prompt: str = Field(min_length=1)


class CharacterAppearanceLock(BaseModel):
    id: str
    name: str
    profile: dict[str, Any]


class SceneImagePrompt(BaseModel):
    scene_id: str
    japanese_description: str
    english_prompt: str
    character_appearance_lock: list[CharacterAppearanceLock]
    background_lock: dict[str, Any]
    style_lock: dict[str, Any]


class ImagePromptExport(BaseModel):
    notice: str = RIGHTS_NOTICE
    prompts: list[SceneImagePrompt] = Field(default_factory=list)


def generate_image_prompts(
    reconstruction: SessionReconstruction,
    state: WorldStateBundle,
    gateway: LLMGateway,
    profile: str = DEFAULT_IMAGE_PROMPT_PROFILE,
) -> ImagePromptExport:
    """Generate one Japanese description and English prompt per reconstructed scene."""
    if not reconstruction.scenes:
        raise EmptySceneError("reconstructed session contains no scenes")
    if state.visual_profiles.style_lock is None:
        raise MissingVisualProfileError("style_lock profile is missing")

    scenes = {scene.id: scene for scene in state.scenes}
    characters = {character.id: character for character in state.characters}
    prompts: list[SceneImagePrompt] = []
    for record in reconstruction.scenes:
        scene = scenes.get(record.id)
        if scene is None:
            raise MissingVisualProfileError(f"scene state is missing for {record.id}")
        background = _background_for_scene(scene, state.visual_profiles.backgrounds)
        character_locks = _character_locks(scene, characters)
        style_lock = state.visual_profiles.style_lock
        payload = _scene_payload(
            record.model_dump(mode="json"), scene, character_locks, background, style_lock
        )
        try:
            output = gateway.complete(
                profile,
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                ImagePromptLLMOutput,
                prompt_template_name=PROMPT_TEMPLATE_NAME,
            )
        except StructuredOutputError as exc:
            raise ImagePromptError(f"LLM schema error for scene {record.id}: {exc}") from exc
        except ProviderConnectionError as exc:
            raise ImagePromptError(f"LLM request failed for scene {record.id}: {exc}") from exc
        if not isinstance(output, ImagePromptLLMOutput):
            raise ImagePromptError(
                f"LLM schema error for scene {record.id}: expected ImagePromptLLMOutput"
            )
        prompts.append(
            SceneImagePrompt(
                scene_id=record.id,
                japanese_description=output.japanese_description.strip(),
                english_prompt=output.english_prompt.strip(),
                character_appearance_lock=character_locks,
                background_lock=background.model_dump(mode="json"),
                style_lock=style_lock.model_dump(mode="json"),
            )
        )
    return ImagePromptExport(prompts=prompts)


def render_image_prompts_markdown(result: ImagePromptExport) -> str:
    lines = ["# シーン画像プロンプト", "", f"> {result.notice}", ""]
    for prompt in result.prompts:
        lines.extend(
            [
                f"## {prompt.scene_id}",
                "",
                "### 日本語シーン説明",
                "",
                prompt.japanese_description,
                "",
                "### English prompt",
                "",
                prompt.english_prompt,
                "",
                "### Consistency locks",
                "",
                "```yaml",
                yaml.safe_dump(
                    {
                        "character_appearance_lock": [
                            lock.model_dump(mode="json")
                            for lock in prompt.character_appearance_lock
                        ],
                        "background_lock": prompt.background_lock,
                        "style_lock": prompt.style_lock,
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ).rstrip(),
                "```",
                "",
            ]
        )
    return "\n".join(lines).rstrip("\n") + "\n"


def write_image_prompt_exports(output_dir: Path, result: ImagePromptExport) -> tuple[Path, Path]:
    """Atomically publish the YAML and Markdown artifacts using existing writer semantics."""
    output_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = output_dir / "image_prompts.yaml"
    markdown_path = output_dir / "image_prompts.md"
    yaml_text = yaml.safe_dump(result.model_dump(mode="json"), allow_unicode=True, sort_keys=False)
    _atomic_write_text(yaml_path, yaml_text)
    _atomic_write_text(markdown_path, render_image_prompts_markdown(result))
    return yaml_path, markdown_path


def _background_for_scene(
    scene: SceneState, backgrounds: list[BackgroundVisualProfile]
) -> BackgroundVisualProfile:
    if not backgrounds:
        raise MissingVisualProfileError(f"background profile is missing for scene {scene.id}")
    location_key = _location_key(scene.location)
    matches = [
        background
        for background in backgrounds
        if location_key in _location_key(background.name)
        or _location_key(background.name) in location_key
    ]
    if len(matches) == 1:
        return matches[0]
    if len(backgrounds) == 1:
        return backgrounds[0]
    raise MissingVisualProfileError(
        f"background profile matching location {scene.location!r} is missing for scene {scene.id}"
    )


def _character_locks(
    scene: SceneState, characters: dict[str, CharacterState]
) -> list[CharacterAppearanceLock]:
    locks: list[CharacterAppearanceLock] = []
    for character_id in scene.active_characters:
        character = characters.get(character_id)
        if character is None:
            raise MissingVisualProfileError(
                f"character state {character_id} is missing for scene {scene.id}"
            )
        if character.visual_profile is None:
            raise MissingVisualProfileError(
                f"visual profile for character {character_id} is missing in scene {scene.id}"
            )
        locks.append(
            CharacterAppearanceLock(
                id=character.id,
                name=character.name,
                profile=character.visual_profile.model_dump(mode="json"),
            )
        )
    return locks


def _scene_payload(
    record: dict[str, Any],
    scene: SceneState,
    character_locks: list[CharacterAppearanceLock],
    background: BackgroundVisualProfile,
    style_lock: StyleLockProfile,
) -> dict[str, Any]:
    return {
        "scene": record,
        "time": scene.time,
        "stakes": scene.stakes,
        "reader_visible_facts": scene.reader_visible_facts,
        "character_appearance_lock": [lock.model_dump(mode="json") for lock in character_locks],
        "background_lock": background.model_dump(mode="json"),
        "style_lock": style_lock.model_dump(mode="json"),
    }


def _location_key(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _atomic_write_text(path: Path, content: str) -> None:
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)
