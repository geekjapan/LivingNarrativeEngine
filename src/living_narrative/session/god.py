"""God-mode edits still produce state diffs and review artifacts."""

from pathlib import Path

from living_narrative.pipeline.status import TurnStatus
from living_narrative.session.review import write_artifact_diff, write_review_yaml
from living_narrative.state.diff import StateDiff, apply_state_diff, save_apply_artifacts
from living_narrative.state.models import UserMode, WorldStateBundle


def apply_god_edit(bundle: WorldStateBundle, diff: StateDiff, turn_dir: Path) -> WorldStateBundle:
    result = apply_state_diff(bundle, diff)
    write_artifact_diff(turn_dir, diff, applied=True)
    save_apply_artifacts(result, turn_dir)
    write_review_yaml(
        turn_dir,
        turn=diff.turn,
        decision="accept_all",
        decided_by=UserMode.GOD,
        resulting_turn_status=TurnStatus.APPLIED,
        auto_applied=True,
    )
    return result.bundle
