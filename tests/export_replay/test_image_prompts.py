import json

import pytest
from pydantic import ValidationError

from living_narrative.export_replay.image_prompts import (
    PROMPT_TEMPLATE_NAME,
    RIGHTS_NOTICE,
    EmptySceneError,
    ImagePromptError,
    ImagePromptLLMOutput,
    MissingVisualProfileError,
    generate_image_prompts,
    render_image_prompts_markdown,
    write_image_prompt_exports,
)
from living_narrative.export_replay.reconstruction import SceneRecord, SessionReconstruction
from living_narrative.llm.errors import StructuredOutputError
from living_narrative.state.models import WorldStateBundle


class FakeGateway:
    def __init__(self, output=None, error=None):
        self.output = output
        self.error = error
        self.calls = []

    def complete(self, binding_key, messages, response_schema, prompt_template_name):
        self.calls.append((binding_key, messages, response_schema, prompt_template_name))
        if self.error:
            raise self.error
        return self.output


def _state(*, character_profile=True, style_lock=True, backgrounds=True):
    return WorldStateBundle.model_validate(
        {
            "world": {"id": "world_001", "name": "世界", "summary": "概要"},
            "characters": [
                {
                    "id": "char_001",
                    "name": "葵",
                    "role": "探偵",
                    "visual_profile": (
                        {
                            "summary": "短い黒髪の若い探偵",
                            "hair": "短い黒髪",
                            "clothing": ["紺のコート"],
                        }
                        if character_profile
                        else None
                    ),
                }
            ],
            "scenes": [
                {
                    "id": "scene_001",
                    "location": "霧の駅・地下ホーム",
                    "time": "夜",
                    "active_characters": ["char_001"],
                    "mood": "静かな緊張",
                    "stakes": "足音の正体を探る",
                    "summary": "霧の中で足音を聞く",
                }
            ],
            "visual_profiles": {
                "backgrounds": (
                    [
                        {
                            "id": "background_001",
                            "name": "霧の駅ホーム",
                            "summary": "青白い霧の古い駅",
                            "lighting": "冷たい蛍光灯",
                        }
                    ]
                    if backgrounds
                    else []
                ),
                "style_lock": (
                    {
                        "art_style": "静謐なアニメ背景美術",
                        "medium": "digital painting",
                        "avoid": ["photorealism"],
                    }
                    if style_lock
                    else None
                ),
            },
        }
    )


def _reconstruction():
    return SessionReconstruction(
        scenes=[
            SceneRecord(
                id="scene_001",
                location="霧の駅・地下ホーム",
                mood="静かな緊張",
                summary="霧の中で足音を聞く",
                start_turn=1,
            )
        ]
    )


def test_generate_image_prompts_passes_all_consistency_locks_and_profile():
    gateway = FakeGateway(
        ImagePromptLLMOutput(
            japanese_description="霧の駅で葵が足音に耳を澄ませる。",
            english_prompt="A young detective listens for footsteps on a foggy station platform.",
        )
    )

    result = generate_image_prompts(_reconstruction(), _state(), gateway, profile="narrator")

    assert len(result.prompts) == 1
    prompt = result.prompts[0]
    assert prompt.japanese_description.startswith("霧の駅")
    assert prompt.english_prompt.startswith("A young detective")
    assert prompt.character_appearance_lock[0].profile["hair"] == "短い黒髪"
    assert prompt.background_lock["lighting"] == "冷たい蛍光灯"
    assert prompt.style_lock["art_style"] == "静謐なアニメ背景美術"
    assert prompt.english_prompt == (
        "A young detective listens for footsteps on a foggy station platform."
    )
    binding, messages, schema, template = gateway.calls[0]
    assert binding == "narrator"
    assert schema is ImagePromptLLMOutput
    assert template == PROMPT_TEMPLATE_NAME
    payload = json.loads(messages[1]["content"])
    assert payload["character_appearance_lock"][0]["profile"]["clothing"] == ["紺のコート"]
    assert payload["background_lock"]["summary"] == "青白い霧の古い駅"
    assert payload["style_lock"]["avoid"] == ["photorealism"]


def test_exports_include_rights_notice_and_locks_in_both_formats(tmp_path):
    gateway = FakeGateway(
        ImagePromptLLMOutput(japanese_description="説明", english_prompt="Prompt")
    )
    result = generate_image_prompts(_reconstruction(), _state(), gateway)

    yaml_path, markdown_path = write_image_prompt_exports(tmp_path, result)

    yaml_text = yaml_path.read_text(encoding="utf-8")
    markdown = markdown_path.read_text(encoding="utf-8")
    assert RIGHTS_NOTICE in yaml_text
    assert RIGHTS_NOTICE in markdown
    assert "character_appearance_lock" in yaml_text and "character_appearance_lock" in markdown
    assert "background_lock" in yaml_text and "background_lock" in markdown
    assert "style_lock" in yaml_text and "style_lock" in markdown
    assert not list(tmp_path.glob("*.tmp"))
    assert render_image_prompts_markdown(result) == markdown


@pytest.mark.parametrize(
    ("state", "message"),
    [
        (_state(character_profile=False), "character char_001"),
        (_state(style_lock=False), "style_lock"),
        (_state(backgrounds=False), "background profile"),
    ],
)
def test_missing_visual_profile_is_explicit(state, message):
    gateway = FakeGateway(
        ImagePromptLLMOutput(japanese_description="説明", english_prompt="Prompt")
    )

    with pytest.raises(MissingVisualProfileError, match=message):
        generate_image_prompts(_reconstruction(), state, gateway)


def test_empty_reconstruction_is_explicit():
    with pytest.raises(EmptySceneError, match="no scenes"):
        generate_image_prompts(SessionReconstruction(), _state(), FakeGateway())


def test_llm_schema_error_names_the_scene():
    error = StructuredOutputError(
        provider_name="mock", model="m", schema_name="ImagePromptLLMOutput", last_error="bad json"
    )

    with pytest.raises(ImagePromptError, match="LLM schema error for scene scene_001"):
        generate_image_prompts(_reconstruction(), _state(), FakeGateway(error=error))


def test_output_schema_rejects_blank_fields():
    with pytest.raises(ValidationError):
        ImagePromptLLMOutput(japanese_description="", english_prompt="")


@pytest.mark.parametrize(
    ("japanese_description", "english_prompt"),
    [(" \t\n", "Prompt"), ("説明", " \t\n")],
)
def test_output_schema_rejects_whitespace_only_fields(japanese_description, english_prompt):
    with pytest.raises(ValidationError):
        ImagePromptLLMOutput(
            japanese_description=japanese_description,
            english_prompt=english_prompt,
        )


def test_output_schema_strips_surrounding_whitespace():
    output = ImagePromptLLMOutput(
        japanese_description="  説明\n",
        english_prompt="\tEnglish prompt.  ",
    )

    assert output.japanese_description == "説明"
    assert output.english_prompt == "English prompt."
