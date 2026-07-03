"""Character Agent slot implementation."""

from typing import Any

from living_narrative.agents.context_builder import build_character_context
from living_narrative.agents.models import CharacterAgentOutput
from living_narrative.intervention.router import character_directives_for
from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.llm_gateway import LLMGateway
from living_narrative.pipeline.models import ActionCandidate as PipelineActionCandidate
from living_narrative.pipeline.models import ActRecord, WorldEventCandidate
from living_narrative.state.models import CharacterStatus

PROMPT_TEMPLATE_NAME = "agent-runtime-character-v1"
PROMPT_TEXT = (
    "Act only on the scoped context. Preserve knowledge and secret consistency: "
    "do not use GM vault facts, other characters' private minds, or unknown events."
)


def run_character_agent(
    context: TurnContext,
    world_events: list[WorldEventCandidate],
    gateway: LLMGateway,
    interventions: list[dict[str, Any]] = (),
) -> tuple[list[PipelineActionCandidate], list[ActRecord]]:
    del world_events
    actions: list[PipelineActionCandidate] = []
    records: list[ActRecord] = []
    active_ids = _active_character_ids(context)
    for character in context.bundle.characters:
        if character.status != CharacterStatus.ALIVE or character.id not in active_ids:
            continue
        directives = character_directives_for(interventions, character.id, context.bundle)
        scoped = build_character_context(context.bundle, character.id, directives=directives)
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


def _active_character_ids(context: TurnContext) -> set[str]:
    for scene in context.bundle.scenes:
        if scene.status == "active":
            return set(scene.active_characters)
    return set()
