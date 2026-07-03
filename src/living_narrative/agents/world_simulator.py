"""World Simulator slot implementation."""

from typing import Any

from living_narrative.agents.models import BackgroundEventCandidate, WorldSimulatorOutput
from living_narrative.pipeline.context import TurnContext
from living_narrative.pipeline.models import WorldEventCandidate
from living_narrative.random.tables import WeightedEntry
from living_narrative.state.models import Visibility


def simulate_world(
    context: TurnContext,
    interventions: list[dict[str, Any]],
) -> list[WorldEventCandidate]:
    del interventions
    entries = [
        WeightedEntry(name="静かな時間が流れる", weight=3),
        WeightedEntry(name="遠くで不穏な物音がする", weight=1),
    ]
    roll = context.random_engine.select_from_table(
        entries,
        turn=context.turn,
        table_name="background_events",
        label="world_simulator.background_event",
    )
    output = WorldSimulatorOutput(
        time_advance="one_turn",
        background_events=[
            BackgroundEventCandidate(
                description=str(roll.result),
                roll_id=roll.id,
                visibility=Visibility.READER,
                effects={"_roll": roll.model_dump(mode="json")},
            )
        ],
    )
    return [
        WorldEventCandidate(
            type="background_event",
            cause="world_simulator",
            text=event.description,
            visibility=event.visibility,
            effects=event.effects,
            target_id=event.target_id,
        )
        for event in output.background_events
    ]
