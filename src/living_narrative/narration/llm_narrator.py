"""LLM Narrator: rewrites reader-visible events into Japanese prose (issue 003, ADR-0002)."""

import json
from typing import Any

from pydantic import BaseModel, Field

from living_narrative.llm.errors import ProviderConnectionError, StructuredOutputError
from living_narrative.narration.models import (
    NarrationResult,
    NarratorContext,
    NarratorQuestUpdateCandidate,
    ThreadUpdateCandidate,
)
from living_narrative.narration.narrator import narrate
from living_narrative.narration.renderers import RendererRegistry
from living_narrative.pipeline.llm_gateway import LLMGateway
from living_narrative.state.models import ProjectConfig

NARRATOR_BINDING_KEY = "narrator"
PROMPT_TEMPLATE_NAME = "narration-narrator-v1"
PROMPT_TEXT = """\
あなたは物語のナレーターです。ユーザーメッセージのJSONで渡される読者可視情報だけを使い、\
このターンの出来事を日本語の小説の地文として書き直してください。

## 情報スコープ(厳守)
- 使ってよい情報は reader_state_facts / scene_reader_visible_facts / reader_visible_events / \
scene_summary のみ。
- 与えられていない事実・出来事・人物の内心を新たに作らない。隠された真相や事情を推測で書かない。
- 気配・音・光といった演出の肉付けはよいが、物語上の新しい事実を確定させない。

## 文体
- genre / tone / mood / tone_control に合わせた三人称の地文。
- scene_summary はこの場面のこれまでの現在状況。地文は scene_summary をそのまま繰り返して\
場面を再確立するのではなく、その状況の続きとして書く。
- reader_visible_events を時系列どおりにすべて反映する。ひとつも落とさない。
- dialogue タイプのイベントは「」の会話文として自然に組み込む。
- 1〜3段落の日本語のみ(固有名詞を除く)。箇条書き・見出し・\
メタ言及(「ターン」「イベント」等)を書かない。

## 未回収の糸(伏線)
- open_threads に、この物語でまだ回収されていない謎・伏線の一覧(id / description / \
turns_open=経過ターン数)が渡される。
- 今回の地文で新しい謎・伏線に触れたら、thread_updates に action="open" の項目を追加し、\
description にその内容を日本語で書く(reader可視情報だけを根拠にする。隠された真相を書かない)。
- 既存の糸が今回の地文で進展したら action="advance" とし、thread_id にその糸のidを指定し、\
note に進展の要約を日本語で書く。
- 糸が今回の地文で決着したら action="resolve" とし、thread_id にその糸のidを指定する。
- turns_open が大きい(長く放置されている)糸ほど、新しい謎を積むより advance か resolve を\
優先して検討する。
- 進展も決着もない糸は thread_updates に含めない。無理に埋めない。

## クエスト(明示的目標)
- open_quests は明示的な目標と達成条件であり、伏線を扱う open_threads とは区別する。
- 実際に開始・進展・達成した場合だけ quest_updates に open/advance/resolve を出す。

## 通史要約(長期記憶)
- summary_request が渡されたターンだけ、memory_summary_update に3〜5文の日本語で通史要約を書く。\
summary_request.previous_summary(あれば)を引き継ぎ、summary_request.window_events \
(直近の読者可視な出来事)を統合した、物語全体のこれまでの流れを書く。reader可視情報だけを\
根拠にする。
- summary_request が渡されないターンは memory_summary_update を null のままにする(無理に書かない)。

## 出力
- prose フィールドに完成した地文だけを入れる。
- scene_summary_update フィールドに、このターン終了時点での場面の現在状況を日本語1〜2文で書く\
(このターンで何が変わったかを含める)。reader可視情報だけを根拠にする。
- thread_updates フィールドに、上記の糸の更新をリストで入れる(0件でもよい)。
- quest_updates フィールドに、上記のクエスト更新をリストで入れる(0件でもよい)。
- memory_summary_update フィールドは、summary_request が渡されたときだけ書く。それ以外は null。
"""


class LLMNarratorOutput(BaseModel):
    prose: str = Field(min_length=1)
    scene_summary_update: str | None = None
    thread_updates: list[ThreadUpdateCandidate] = Field(default_factory=list)
    quest_updates: list[NarratorQuestUpdateCandidate] = Field(default_factory=list)
    memory_summary_update: str | None = None


def _narrator_payload(
    context: NarratorContext, project: ProjectConfig, mood: str, tone_control: str | None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "genre": project.genre,
        "tone": project.tone,
        "mood": mood,
        "tone_control": tone_control,
        "reader_state_facts": context.reader_state_facts,
        "scene_reader_visible_facts": context.scene_reader_visible_facts,
        "scene_summary": context.scene_summary,
        "reader_visible_events": [
            {"type": event.type, "text": event.text} for event in context.reader_visible_events
        ],
        "open_threads": [
            {
                "id": thread.id,
                "description": thread.description,
                "turns_open": (
                    context.turn - thread.opened_turn if thread.opened_turn is not None else None
                ),
            }
            for thread in context.open_threads
        ],
        "open_quests": [quest.model_dump(mode="json") for quest in context.open_quests],
        "memory_summary": context.memory_summary,
    }
    # 015: summary_request is only present on turns where a memory summary is due — its
    # absence is the signal to the narrator to leave memory_summary_update null.
    if context.memory_summary_due:
        payload["summary_request"] = {
            "previous_summary": context.memory_summary,
            "window_events": context.summary_window_events,
        }
    return payload


def run_narrate_phase(
    *,
    gateway: LLMGateway,
    project: ProjectConfig,
    context: NarratorContext,
    style: str,
    mood: str,
    tone_control: str | None,
    registry: RendererRegistry | None = None,
) -> tuple[NarrationResult, dict[str, Any]]:
    """Narrate via the ``narrator``-bound LLM when eligible, else the mechanical renderer.

    LLM path requires: style ``novel``, an explicit ``narrator`` binding, and at least one
    reader-visible event or scene fact (an empty context would only invite invention).
    LLM failure falls back to the mechanical renderer instead of failing the turn (ADR-0002).
    """
    has_material = bool(context.reader_visible_events or context.scene_reader_visible_facts)
    if style != "novel" or NARRATOR_BINDING_KEY not in project.llm_bindings or not has_material:
        result = narrate(
            context, style=style, mood=mood, tone_control=tone_control, registry=registry
        )
        return result, {"mode": "renderer", "style": result.style}

    payload = _narrator_payload(context, project, mood, tone_control)
    messages = [
        {"role": "system", "content": PROMPT_TEXT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    try:
        output = gateway.complete(
            NARRATOR_BINDING_KEY,
            messages,
            LLMNarratorOutput,
            prompt_template_name=PROMPT_TEMPLATE_NAME,
        )
    except (ProviderConnectionError, StructuredOutputError) as exc:
        fallback = narrate(
            context, style=style, mood=mood, tone_control=tone_control, registry=registry
        )
        return fallback, {
            "mode": "renderer_fallback",
            "style": fallback.style,
            "prompt_template_name": PROMPT_TEMPLATE_NAME,
            "input": payload,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
    assert isinstance(output, LLMNarratorOutput)
    summary_update = output.scene_summary_update.strip() if output.scene_summary_update else None
    memory_summary_update = (
        output.memory_summary_update.strip() if output.memory_summary_update else None
    )
    result = NarrationResult(
        text=output.prose.strip(),
        style="novel",
        scene_summary_update=summary_update or None,
        thread_updates=output.thread_updates,
        quest_updates=output.quest_updates,
        memory_summary_update=memory_summary_update or None,
    )
    return result, {
        "mode": "llm",
        "style": "novel",
        "prompt_template_name": PROMPT_TEMPLATE_NAME,
        "request": messages,
        "input": payload,
        "output": output.model_dump(mode="json"),
    }
