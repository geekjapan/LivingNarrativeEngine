"""``TurnContext``: the in-memory output of the Load phase."""

from dataclasses import dataclass

from living_narrative.random.engine import RandomEngine
from living_narrative.state.models import ProjectConfig, WorldStateBundle
from living_narrative.workspace.loader import WorkspacePaths


@dataclass
class TurnContext:
    turn: int
    project: ProjectConfig
    paths: WorkspacePaths
    bundle: WorldStateBundle
    random_engine: RandomEngine
