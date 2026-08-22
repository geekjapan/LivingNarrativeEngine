from pathlib import Path

from living_narrative.pipeline.context import TurnContext
from living_narrative.safety.narrative_quality_check import narrative_quality_checker
from living_narrative.state.diff import StateDiff
from living_narrative.state.models import (
    Event,
    ProjectConfig,
    Visibility,
    WorldState,
    WorldStateBundle,
)
from living_narrative.workspace.loader import WorkspacePaths


def _project(*, enabled: bool, minimum_narration_characters: int) -> ProjectConfig:
    return ProjectConfig.model_validate(
        {
            "id": "project",
            "title": "Title",
            "genre": "mystery",
            "tone": "quiet",
            "autonomy_level": "assist",
            "user_mode": "assistant_gm",
            "random_seed": "seed",
            "renderer": "novel",
            "llm": {"provider": "mock", "model": "mock-v1"},
            "workspace": {
                "root": "workspace",
                "state": "workspace/state",
                "runs": "workspace/runs",
                "exports": "workspace/exports",
            },
            "narrative_quality": {
                "enabled": enabled,
                "minimum_narration_characters": minimum_narration_characters,
            },
        }
    )


def _context(tmp_path: Path, *, enabled: bool, minimum_narration_characters: int) -> TurnContext:
    return TurnContext(
        turn=1,
        project=_project(
            enabled=enabled,
            minimum_narration_characters=minimum_narration_characters,
        ),
        paths=WorkspacePaths(
            root=tmp_path,
            state=tmp_path / "state",
            runs=tmp_path / "runs",
            exports=tmp_path / "exports",
        ),
        bundle=WorldStateBundle(world=WorldState(id="world_001", name="World", summary="")),
        random_engine=None,
    )


def test_narrative_quality_checker_blocks_short_prose_only_when_opted_in(tmp_path):
    opted_in = _context(tmp_path, enabled=True, minimum_narration_characters=1200)
    disabled = _context(tmp_path, enabled=False, minimum_narration_characters=1200)
    diff = StateDiff(id="diff_0001", turn=1)

    findings = narrative_quality_checker(opted_in, "あ" * 1199, [], diff)

    assert [(finding.checker, finding.severity, finding.message) for finding in findings] == [
        ("narrative_quality", "error", "narration_too_short"),
    ]
    assert narrative_quality_checker(disabled, "あ" * 476, [], diff) == []


def test_narrative_quality_checker_blocks_stalls_beyond_opted_in_limit(tmp_path):
    context = _context(tmp_path, enabled=True, minimum_narration_characters=1)
    context.turn = 3
    context.project.narrative_quality.maximum_consecutive_stall_turns = 2
    diff = StateDiff(id="diff_0003", turn=3)

    findings = narrative_quality_checker(context, "十分な本文", [], diff)

    assert [(finding.checker, finding.severity, finding.message) for finding in findings] == [
        ("narrative_quality", "error", "consecutive_stall_limit_exceeded"),
    ]


def test_narrative_quality_checker_counts_only_reader_visible_advancement(tmp_path):
    context = _context(tmp_path, enabled=True, minimum_narration_characters=1)
    context.turn = 3
    context.project.narrative_quality.maximum_consecutive_stall_turns = 2
    diff = StateDiff(id="diff_0003", turn=3)
    hidden_advancement = Event(
        id="event_0001",
        turn=3,
        type="threat_stage",
        text="hidden",
        visibility=Visibility.GM_ONLY,
    )
    reader_advancement = hidden_advancement.model_copy(
        update={"id": "event_0002", "visibility": Visibility.READER}
    )

    hidden_findings = narrative_quality_checker(context, "十分な本文", [hidden_advancement], diff)

    assert [
        (finding.checker, finding.severity, finding.message) for finding in hidden_findings
    ] == [
        ("narrative_quality", "error", "consecutive_stall_limit_exceeded"),
    ]
    assert narrative_quality_checker(context, "十分な本文", [reader_advancement], diff) == []
