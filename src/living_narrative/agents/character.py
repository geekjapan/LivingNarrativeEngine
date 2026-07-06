"""Character Agent slot implementation."""

from typing import Any

from living_narrative.agents.context_builder import build_character_context
from living_narrative.agents.models import CharacterAgentOutput
from living_narrative.intervention.router import character_directives_for
from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.llm_gateway import LLMGateway
from living_narrative.pipeline.models import ActionCandidate as PipelineActionCandidate
from living_narrative.pipeline.models import ActRecord, WorldEventCandidate
from living_narrative.state.models import CharacterStatus, Event

PROMPT_TEMPLATE_NAME = "agent-runtime-character-v4"
PROMPT_TEXT = """\
あなたは物語のキャラクターエージェントです。ユーザーメッセージのJSONで渡される \
scoped_state に記述されたキャラクター本人として、このターンの行動を生成してください。

## 情報スコープ(厳守)
- 与えられたスコープ済みコンテキストのみに基づいて行動する。
- GM vault の事実、他キャラクターの private_mind、このキャラクターが知らない出来事は \
存在しないものとして扱う(knowledge にないことを知っていてはならない)。
- 自分の secrets は行動や台詞で不用意に明かさない。

## 出力言語
- すべての content は必ず日本語で書く。英語や他言語を混ぜない(固有名詞を除く)。

## ペルソナ
- scoped_state の name / role / traits / goals / emotions / private_mind を反映し、\
その人物らしい口調・判断・感情で書く。
- dialogue は「」で括った自然な話し言葉。action は三人称の簡潔な描写文。
- scoped_state.speech.first_person が設定されている場合、台詞の一人称は必ずそれを使う。\
scoped_state.speech.forbidden_terms に列挙された語は台詞に使わない。

## action_candidates の作法
- kind は action(行動)/ dialogue(台詞)/ inner_reaction(内心)を使い分ける。
- 1〜3件。行動か台詞を中心に、必要なら内心を1件だけ添える。
- content は1〜2文の描写。思考の羅列や箇条書きにしない。

## visibility 規則
- inner_reaction は必ず "character"(本人だけの内心。読者には開示されない)。
- 他の登場人物からも見える行動・台詞は "reader"。
- 人目を忍んで行う行動は "scene" または "character"。

## 感情の更新
- emotion_deltas は出来事に応じて -20〜+20 の範囲で出す。上昇だけでなく下降も出す。
- 安堵・解決・空振り・休息など、緊張が緩む出来事では負のdeltaを出す。
- 更新できるのは scoped_state.emotions に既に存在するキーのみ。存在しないキーは追加しない。

## 高感情の行動
- いずれかの感情が90以上のとき、その感情が行動を支配する。例えばfearが90以上なら \
逃走・回避・判断力の乱れ、curiosityが90以上なら危険を顧みない接近など、その感情に \
支配された行動・台詞・内心を書く。
"""


def run_character_agent(
    context: TurnContext,
    world_events: list[WorldEventCandidate],
    gateway: LLMGateway,
    interventions: list[dict[str, Any]] = (),
    past_events: list[Event] | None = None,
) -> tuple[list[PipelineActionCandidate], list[ActRecord]]:
    current_events = [
        _candidate_as_event(candidate, context.turn, index)
        for index, candidate in enumerate(world_events)
    ]
    events = [*(past_events or []), *current_events]
    actions: list[PipelineActionCandidate] = []
    records: list[ActRecord] = []
    active_ids = _active_character_ids(context)
    for character in context.bundle.characters:
        if character.status != CharacterStatus.ALIVE or character.id not in active_ids:
            continue
        directives = character_directives_for(interventions, character.id, context.bundle)
        scoped = build_character_context(
            context.bundle, character.id, events=events, directives=directives
        )
        messages = [
            {"role": "system", "content": PROMPT_TEXT},
            {"role": "user", "content": scoped.model_dump_json()},
        ]
        output = gateway.complete(
            f"character:{character.id}",
            messages,
            CharacterAgentOutput,
            prompt_template_name=PROMPT_TEMPLATE_NAME,
        )
        assert isinstance(output, CharacterAgentOutput)
        for index, candidate in enumerate(output.action_candidates):
            actions.append(
                PipelineActionCandidate(
                    character_id=character.id,
                    action_text=candidate.content,
                    kind=candidate.kind,
                    visibility=candidate.visibility,
                    target_id=candidate.target_id,
                    effects=candidate.effects,
                    source_index=index,
                )
            )
        records.append(
            ActRecord(
                character_id=character.id,
                prompt_template_name=PROMPT_TEMPLATE_NAME,
                request=messages,
                response=output.model_dump(mode="json"),
                input_context=scoped.model_dump(mode="json"),
            )
        )
    return actions, records


def _candidate_as_event(candidate: WorldEventCandidate, turn: int, index: int) -> Event:
    # Simulate-phase candidates have no event_NNNN id yet (Resolve assigns real ones);
    # this id is only for the visibility filter and is never persisted.
    return Event(
        id=f"event_9{index:03d}",
        turn=turn,
        type=candidate.type,
        cause=candidate.cause,
        text=candidate.text,
        visibility=candidate.visibility,
        known_by=candidate.known_by,
        hidden_from=candidate.hidden_from,
        effects=candidate.effects,
    )


def _active_character_ids(context: TurnContext) -> set[str]:
    for scene in context.bundle.scenes:
        if scene.status == "active":
            return set(scene.active_characters)
    return set()
