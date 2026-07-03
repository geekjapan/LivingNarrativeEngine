import pytest
from pydantic import ValidationError

from living_narrative.intervention.interpreter import (
    InterpreterOutput,
    build_interpreter_messages,
    interpret_free_text,
)
from living_narrative.intervention.permissions import PermissionRejection
from living_narrative.llm.structured import compute_prompt_hash
from living_narrative.pipeline.llm_gateway import LLMGateway
from living_narrative.state.models import LLMConfig, ProjectConfig, WorkspaceConfig


def _project() -> ProjectConfig:
    return ProjectConfig(
        id="p",
        title="P",
        genre="g",
        tone="t",
        autonomy_level="auto",
        user_mode="assistant_gm",
        random_seed="seed",
        renderer="novel",
        llm=LLMConfig(provider="mock", model="mock"),
        workspace=WorkspaceConfig(root=".", state="state", runs="runs", exports="exports"),
    )


def _scripted_gateway(free_text: str, response: dict) -> LLMGateway:
    prompt_hash = compute_prompt_hash(build_interpreter_messages(free_text))
    return LLMGateway(
        project=_project(),
        random_seed="seed",
        scripted_responses={"InterpreterOutput": {prompt_hash: response}},
    )


def _ids():
    counter = 0

    def allocate():
        nonlocal counter
        counter += 1
        return f"int_{counter:04d}"

    return allocate


RINA_KAI_TEXT = (
    "リナにはカイの様子がおかしいことに気づかせたい。ただし、カイの秘密はまだ明かさない。"
)
RINA_KAI_RESPONSE = {
    "interventions": [
        {
            "type": "character_directive",
            "target": {"kind": "character", "id": "char_rina"},
            "content": "カイの様子がおかしいことに気づく",
            "visibility": "character",
        },
        {
            "type": "reveal_control",
            "target": {"kind": "gm_vault", "id": "gm_vault_001"},
            "content": "カイの秘密",
            "constraints": {"mode": "must-not-reveal"},
            "visibility": "gm_only",
        },
    ],
    "confidence": 0.82,
    "interpretation_summary": "リナへの気づき directive とカイの秘密の非開示を分離",
}


def test_single_free_text_decomposes_into_multiple_interventions():
    gateway = _scripted_gateway(RINA_KAI_TEXT, RINA_KAI_RESPONSE)

    result = interpret_free_text(
        gateway,
        RINA_KAI_TEXT,
        turn=4,
        user_role="assistant_gm",
        allocate_id=_ids(),
    )

    assert len(result.interventions) == 2
    types = {item.type for item in result.interventions}
    assert types == {"character_directive", "reveal_control"}
    assert result.confidence == 0.82
    assert result.interpretation_summary


def test_unclassified_fragment_falls_back_to_scene_directive():
    text = "よくわからない雰囲気の指示"
    response = {
        "interventions": [
            {
                "type": "scene_directive",
                "target": {"kind": "scene"},
                "content": text,
                "visibility": "scene",
            }
        ],
        "confidence": 0.2,
        "interpretation_summary": "分類不能のためscene_directiveへフォールバック",
    }
    gateway = _scripted_gateway(text, response)

    result = interpret_free_text(gateway, text, turn=1, user_role="watcher", allocate_id=_ids())

    assert len(result.interventions) == 1
    assert result.interventions[0].type == "scene_directive"
    assert result.interventions[0].content == text


def test_interpreter_is_deterministic_for_same_seed_and_input():
    gateway_a = _scripted_gateway(RINA_KAI_TEXT, RINA_KAI_RESPONSE)
    gateway_b = _scripted_gateway(RINA_KAI_TEXT, RINA_KAI_RESPONSE)

    first = interpret_free_text(
        gateway_a, RINA_KAI_TEXT, turn=4, user_role="assistant_gm", allocate_id=_ids()
    )
    second = interpret_free_text(
        gateway_b, RINA_KAI_TEXT, turn=4, user_role="assistant_gm", allocate_id=_ids()
    )

    assert first.interventions == second.interventions
    assert first.confidence == second.confidence
    assert first.interpretation_summary == second.interpretation_summary


def test_permission_rejection_is_surfaced_per_draft():
    text = "canon を書き換えて"
    response = {
        "interventions": [
            {
                "type": "canon_edit",
                "target": {"kind": "canon"},
                "content": "新しい真実",
                "visibility": "canon",
            }
        ],
        "confidence": 0.9,
        "interpretation_summary": "canon_edit の要求",
    }
    gateway = _scripted_gateway(text, response)

    result = interpret_free_text(gateway, text, turn=1, user_role="watcher", allocate_id=_ids())

    assert result.interventions == []
    assert len(result.rejections) == 1
    assert isinstance(result.rejections[0], PermissionRejection)


def test_interpreter_output_schema_rejects_unknown_type():
    with pytest.raises(ValidationError):
        InterpreterOutput.model_validate(
            {
                "interventions": [
                    {
                        "type": "not_a_type",
                        "target": {"kind": "world"},
                        "content": "x",
                        "visibility": "reader",
                    }
                ],
                "confidence": 0.5,
                "interpretation_summary": "s",
            }
        )
