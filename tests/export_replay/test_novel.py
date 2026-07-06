import json

import pytest

from living_narrative.export_replay.loader import load_turn_records
from living_narrative.export_replay.novel import (
    DEFAULT_PROFILE,
    PROMPT_TEMPLATE_NAME,
    NovelChapterOutput,
    render_novel,
)
from living_narrative.export_replay.outline import build_outline, narration_by_turn_from_records
from living_narrative.export_replay.reconstruction import reconstruct_session
from living_narrative.llm.errors import ProviderConnectionError, StructuredOutputError
from living_narrative.state.models import LLMConfig, ProjectConfig


def _project() -> ProjectConfig:
    return ProjectConfig(
        id="p",
        title="霧の駅",
        genre="mystery",
        tone="quiet-eerie",
        autonomy_level="manual",
        user_mode="assistant_gm",
        random_seed="seed",
        renderer="novel",
        llm=LLMConfig(provider="mock", model="mock-model"),
        workspace={
            "root": "workspace",
            "state": "workspace/state",
            "runs": "workspace/runs",
            "exports": "workspace/exports",
        },
    )


def _chapter(index, *, text="本文", key_events=None, title=None):
    from living_narrative.export_replay.outline import Chapter

    return Chapter(
        index=index,
        title=title or f"第{index}章タイトル",
        scene_id="scene_001",
        start_turn=index,
        end_turn=index,
        key_events=key_events or [],
        narration_texts=[text],
    )


class FakeGateway:
    def __init__(self, results=None, errors=None):
        self.results = results or {}
        self.errors = errors or {}
        self.calls = []

    def complete(self, binding_key, messages, response_schema, prompt_template_name):
        self.calls.append(
            {
                "binding_key": binding_key,
                "messages": messages,
                "schema": response_schema,
                "prompt_template_name": prompt_template_name,
            }
        )
        index = len(self.calls)
        if index in self.errors:
            raise self.errors[index]
        return self.results[index]


def _payload(call):
    return json.loads(call["messages"][1]["content"])


def test_render_novel_makes_one_llm_call_per_chapter():
    from living_narrative.export_replay.outline import Outline

    outline = Outline(chapters=[_chapter(1), _chapter(2), _chapter(3)])
    gateway = FakeGateway(
        results={
            1: NovelChapterOutput(chapter_text="一章分の地文", synopsis="あらすじ1"),
            2: NovelChapterOutput(chapter_text="二章分の地文", synopsis="あらすじ2"),
            3: NovelChapterOutput(chapter_text="三章分の地文", synopsis="あらすじ3"),
        }
    )

    content = render_novel(_project(), outline, gateway)

    assert len(gateway.calls) == 3
    assert all(call["binding_key"] == DEFAULT_PROFILE for call in gateway.calls)
    assert all(call["prompt_template_name"] == PROMPT_TEMPLATE_NAME for call in gateway.calls)
    assert all(call["schema"] is NovelChapterOutput for call in gateway.calls)
    assert "霧の駅" in content
    assert "第1章" in content and "一章分の地文" in content
    assert "第2章" in content and "二章分の地文" in content
    assert "第3章" in content and "三章分の地文" in content


def test_render_novel_uses_the_given_binding_key_profile():
    from living_narrative.export_replay.outline import Outline

    outline = Outline(chapters=[_chapter(1)])
    gateway = FakeGateway(results={1: NovelChapterOutput(chapter_text="本文", synopsis="要約")})

    render_novel(_project(), outline, gateway, profile="narrator")

    assert gateway.calls[0]["binding_key"] == "narrator"


def test_render_novel_passes_sequential_synopsis_forward():
    from living_narrative.export_replay.outline import Outline

    outline = Outline(chapters=[_chapter(1), _chapter(2)])
    gateway = FakeGateway(
        results={
            1: NovelChapterOutput(chapter_text="一章", synopsis="ここまでのあらすじ"),
            2: NovelChapterOutput(chapter_text="二章", synopsis="更新後のあらすじ"),
        }
    )

    render_novel(_project(), outline, gateway)

    assert _payload(gateway.calls[0])["previous_synopsis"] == ""
    assert _payload(gateway.calls[1])["previous_synopsis"] == "ここまでのあらすじ"


def test_render_novel_falls_back_to_raw_narration_on_failed_chapter():
    from living_narrative.export_replay.outline import Outline

    outline = Outline(
        chapters=[
            _chapter(1, text="一章の生narration"),
            _chapter(2, text="二章の生narration"),
        ]
    )
    gateway = FakeGateway(
        results={2: NovelChapterOutput(chapter_text="二章の整形済み", synopsis="あらすじ")},
        errors={1: ProviderConnectionError(provider_name="mock", model="m", error="down")},
    )

    content = render_novel(_project(), outline, gateway)

    assert "一章の生narration" in content
    assert "<!-- fallback: raw narration -->" in content
    assert "二章の整形済み" in content
    # the fallback marker only appears under chapter 1's section, not chapter 2's
    chapter_2_section = content.split("第2章")[1]
    assert "<!-- fallback: raw narration -->" not in chapter_2_section


@pytest.mark.parametrize(
    "error",
    [
        ProviderConnectionError(provider_name="mock", model="m", error="down"),
        StructuredOutputError(
            provider_name="mock", model="m", schema_name="NovelChapterOutput", last_error="bad json"
        ),
    ],
)
def test_render_novel_continues_after_any_known_failure_kind(error):
    from living_narrative.export_replay.outline import Outline

    outline = Outline(chapters=[_chapter(1, text="生本文")])
    gateway = FakeGateway(errors={1: error})

    content = render_novel(_project(), outline, gateway)

    assert "生本文" in content
    assert "<!-- fallback: raw narration -->" in content


def test_novel_payload_never_includes_gm_only_key_events(tmp_path, build_project, write_turn_dir):
    project_path = build_project(tmp_path)
    runs_dir = project_path.parent / "workspace" / "runs"
    write_turn_dir(
        runs_dir,
        1,
        narration="表の地文",
        events=[
            {
                "id": "event_0001",
                "turn": 1,
                "type": "threat_stage",
                "text": "reader可視の出来事",
                "visibility": "reader",
                "effects": {"threat_id": "threat_001", "stage_at": 50},
            },
            {
                "id": "event_0002",
                "turn": 1,
                "type": "thread_update",
                "text": "GM限定の密告",
                "visibility": "gm_only",
                "effects": {"thread_id": "thread_001", "action": "open"},
            },
        ],
    )

    reconstruction = reconstruct_session(project_path)  # reader mode (the default)
    records = load_turn_records(runs_dir)
    outline = build_outline(reconstruction, narration_by_turn_from_records(records))

    gateway = FakeGateway(
        results={1: NovelChapterOutput(chapter_text="整形済み", synopsis="あらすじ")}
    )
    render_novel(_project(), outline, gateway)

    captured = json.dumps([_payload(call) for call in gateway.calls], ensure_ascii=False)
    assert "GM限定の密告" not in captured
    assert "reader可視の出来事" in captured
