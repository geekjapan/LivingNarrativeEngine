import json

import pytest

from living_narrative.llm.errors import ProviderConnectionError, StructuredOutputError
from living_narrative.narration.llm_narrator import (
    PROMPT_TEMPLATE_NAME,
    LLMNarratorOutput,
    run_narrate_phase,
)
from living_narrative.narration.models import NarratorContext, OpenThreadInfo, ThreadUpdateCandidate
from living_narrative.state.models import Event, LLMConfig, ProjectConfig, Visibility


def _project(llm_bindings: dict[str, str] | None = None) -> ProjectConfig:
    return ProjectConfig(
        id="001",
        title="テスト",
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
        llm_profiles={"prose": LLMConfig(provider="mock", model="mock-prose")},
        llm_bindings=llm_bindings or {},
    )


def _context() -> NarratorContext:
    return NarratorContext(
        turn=1,
        reader_state_facts=["既知の事実"],
        scene_reader_visible_facts=["駅は静かだ"],
        reader_visible_events=[
            Event(
                id="event_0001",
                turn=1,
                type="action",
                text="彼は歩き出した",
                visibility=Visibility.READER,
            )
        ],
    )


class FakeGateway:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
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
        if self.error is not None:
            raise self.error
        return self.result


def test_llm_narrator_used_when_narrator_binding_present():
    gateway = FakeGateway(result=LLMNarratorOutput(prose="霧の底で、彼は歩き出した。"))

    result, record = run_narrate_phase(
        gateway=gateway,
        project=_project({"narrator": "prose"}),
        context=_context(),
        style="novel",
        mood="緊張",
        tone_control=None,
    )

    assert result.text == "霧の底で、彼は歩き出した。"
    assert result.style == "novel"
    assert result.scene_summary_update is None
    assert record["mode"] == "llm"
    assert len(gateway.calls) == 1
    call = gateway.calls[0]
    assert call["binding_key"] == "narrator"
    assert call["prompt_template_name"] == PROMPT_TEMPLATE_NAME
    assert "彼は歩き出した" in call["messages"][1]["content"]


def test_llm_narrator_payload_includes_current_scene_summary():
    gateway = FakeGateway(result=LLMNarratorOutput(prose="霧の底で、彼は歩き出した。"))
    context = _context()
    context.scene_summary = "駅のホームに霧が立ち込めている。"

    run_narrate_phase(
        gateway=gateway,
        project=_project({"narrator": "prose"}),
        context=context,
        style="novel",
        mood="緊張",
        tone_control=None,
    )

    payload = json.loads(gateway.calls[0]["messages"][1]["content"])
    assert payload["scene_summary"] == "駅のホームに霧が立ち込めている。"


def test_llm_narrator_output_carries_scene_summary_update():
    gateway = FakeGateway(
        result=LLMNarratorOutput(
            prose="霧の底で、彼は歩き出した。",
            scene_summary_update="彼は霧の奥へ向かって歩き始めた。",
        )
    )

    result, record = run_narrate_phase(
        gateway=gateway,
        project=_project({"narrator": "prose"}),
        context=_context(),
        style="novel",
        mood="緊張",
        tone_control=None,
    )

    assert result.scene_summary_update == "彼は霧の奥へ向かって歩き始めた。"
    assert record["output"]["scene_summary_update"] == "彼は霧の奥へ向かって歩き始めた。"


def test_llm_narrator_blank_scene_summary_update_normalizes_to_none():
    gateway = FakeGateway(
        result=LLMNarratorOutput(prose="霧の底で、彼は歩き出した。", scene_summary_update="   ")
    )

    result, _record = run_narrate_phase(
        gateway=gateway,
        project=_project({"narrator": "prose"}),
        context=_context(),
        style="novel",
        mood="緊張",
        tone_control=None,
    )

    assert result.scene_summary_update is None


def test_llm_narrator_output_carries_thread_updates():
    gateway = FakeGateway(
        result=LLMNarratorOutput(
            prose="霧の底で、彼は歩き出した。",
            thread_updates=[
                ThreadUpdateCandidate(action="open", description="お守りの由来は謎のままだ。"),
                ThreadUpdateCandidate(action="advance", thread_id="thread_000101", note="進展した"),
                ThreadUpdateCandidate(action="resolve", thread_id="thread_000102"),
            ],
        )
    )

    result, record = run_narrate_phase(
        gateway=gateway,
        project=_project({"narrator": "prose"}),
        context=_context(),
        style="novel",
        mood="緊張",
        tone_control=None,
    )

    assert [update.action for update in result.thread_updates] == ["open", "advance", "resolve"]
    assert result.thread_updates[0].description == "お守りの由来は謎のままだ。"
    assert result.thread_updates[1].thread_id == "thread_000101"
    assert record["output"]["thread_updates"][2]["thread_id"] == "thread_000102"


def test_llm_narrator_defaults_to_no_thread_updates():
    gateway = FakeGateway(result=LLMNarratorOutput(prose="霧の底で、彼は歩き出した。"))

    result, _record = run_narrate_phase(
        gateway=gateway,
        project=_project({"narrator": "prose"}),
        context=_context(),
        style="novel",
        mood="緊張",
        tone_control=None,
    )

    assert result.thread_updates == []


def test_llm_narrator_payload_includes_open_threads_with_turns_open():
    gateway = FakeGateway(result=LLMNarratorOutput(prose="霧の底で、彼は歩き出した。"))
    context = _context()
    context.turn = 4
    context.open_threads = [
        OpenThreadInfo(id="thread_000101", description="お守りの由来", opened_turn=1),
        OpenThreadInfo(id="thread_000201", description="turnなし糸", opened_turn=None),
    ]

    run_narrate_phase(
        gateway=gateway,
        project=_project({"narrator": "prose"}),
        context=context,
        style="novel",
        mood="緊張",
        tone_control=None,
    )

    payload = json.loads(gateway.calls[0]["messages"][1]["content"])
    assert payload["open_threads"] == [
        {"id": "thread_000101", "description": "お守りの由来", "turns_open": 3},
        {"id": "thread_000201", "description": "turnなし糸", "turns_open": None},
    ]


def test_mechanical_renderer_used_without_narrator_binding():
    gateway = FakeGateway()

    result, record = run_narrate_phase(
        gateway=gateway,
        project=_project(),
        context=_context(),
        style="novel",
        mood="",
        tone_control=None,
    )

    assert gateway.calls == []
    assert record["mode"] == "renderer"
    assert "彼は歩き出した" in result.text
    assert result.scene_summary_update is None
    assert result.thread_updates == []


def test_log_style_stays_mechanical_even_with_binding():
    gateway = FakeGateway()

    result, record = run_narrate_phase(
        gateway=gateway,
        project=_project({"narrator": "prose"}),
        context=_context(),
        style="log",
        mood="",
        tone_control=None,
    )

    assert gateway.calls == []
    assert record["mode"] == "renderer"
    assert result.style == "log"
    assert result.text.startswith("# turn 1")


def test_empty_context_skips_llm_to_avoid_invention():
    gateway = FakeGateway()

    result, record = run_narrate_phase(
        gateway=gateway,
        project=_project({"narrator": "prose"}),
        context=NarratorContext(turn=2),
        style="novel",
        mood="",
        tone_control=None,
    )

    assert gateway.calls == []
    assert record["mode"] == "renderer"
    assert result.text


@pytest.mark.parametrize(
    "error",
    [
        ProviderConnectionError(provider_name="openai-compatible", model="m", error="down"),
        StructuredOutputError(
            provider_name="openai-compatible",
            model="m",
            schema_name="LLMNarratorOutput",
            last_error="bad json",
        ),
    ],
)
def test_llm_failure_falls_back_to_mechanical_renderer(error):
    gateway = FakeGateway(error=error)

    result, record = run_narrate_phase(
        gateway=gateway,
        project=_project({"narrator": "prose"}),
        context=_context(),
        style="novel",
        mood="緊張",
        tone_control=None,
    )

    assert record["mode"] == "renderer_fallback"
    assert record["error"]["type"] == type(error).__name__
    assert "彼は歩き出した" in result.text
    assert result.style == "novel"
    assert result.scene_summary_update is None
    assert result.thread_updates == []
