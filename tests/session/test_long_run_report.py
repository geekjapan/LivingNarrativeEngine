from __future__ import annotations

import json

from living_narrative.session.long_run_report import LongRunObservation, write_long_run_report
from living_narrative.session.metrics import (
    ChecksMetrics,
    GameMetrics,
    MemoryMetrics,
    PacingMetrics,
    ProjectMetrics,
    ReplayMetrics,
    SceneMetrics,
    ThreadsMetrics,
    TurnsMetrics,
)


def _metrics() -> ProjectMetrics:
    return ProjectMetrics(
        turns=TurnsMetrics(
            total=12,
            timeline_entries=12,
            by_status={"applied": 12},
            discarded=0,
            rolledback=1,
        ),
        emotions=[],
        pacing=PacingMetrics(stall_event_count=0, max_consecutive_stall_turns=0),
        threads=ThreadsMetrics(
            opened=4,
            advanced=4,
            resolved=3,
            max_open_turns=3,
            resolved_ratio=0.75,
        ),
        threats=[],
        scenes=SceneMetrics(
            transition_count=1,
            final_active_count=1,
            final_active_scene_ids=["scene_002"],
            final_statuses={"scene_001": "ended", "scene_002": "active"},
        ),
        checks=ChecksMetrics(by_source={"leak": 0}, by_severity={}, leak_by_severity={}),
        memory=MemoryMetrics(summary_count=2),
        game=GameMetrics(
            combat_count=1,
            quest_opened=1,
            quest_advanced=1,
            quest_resolved=0,
            applied_pc_action_count=2,
            encounter_count=3,
            skill_check_successes=2,
            skill_check_total=2,
            skill_check_success_rate=1.0,
        ),
        replay=ReplayMetrics(matched_turns=12, evaluated_turns=12, match_rate=1.0),
    )


def test_write_long_run_report_serializes_only_public_comparison_data(tmp_path):
    observation = LongRunObservation(
        name="journey-a",
        turn_count=12,
        elapsed_seconds=1.25,
        workspace_artifact_bytes=456,
        replay_bytes=123,
        run_fingerprint="5b9133bcbbe29f8b0cb7a37d56fbd044ab1d7c31dcb68c2e7b9eb1c2b599c6d4",
        metrics=_metrics(),
    )

    output = write_long_run_report(tmp_path / "report.json", [observation])

    assert output == tmp_path / "report.json"
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload == {
        "schema_version": 1,
        "journeys": [
            {
                "name": "journey-a",
                "turn_count": 12,
                "elapsed_seconds": 1.25,
                "workspace_artifact_bytes": 456,
                "replay_bytes": 123,
                "run_fingerprint": (
                    "5b9133bcbbe29f8b0cb7a37d56fbd044ab1d7c31dcb68c2e7b9eb1c2b599c6d4"
                ),
                "metrics": _metrics().model_dump(mode="json"),
            }
        ],
    }
    serialized = output.read_text(encoding="utf-8")
    assert "tmp_path" not in serialized
    assert "OPENAI_API_KEY" not in serialized


def test_write_long_run_report_rejects_duplicate_journey_names(tmp_path):
    observation = LongRunObservation(
        name="journey-a",
        turn_count=1,
        elapsed_seconds=0.0,
        workspace_artifact_bytes=0,
        replay_bytes=0,
        run_fingerprint="0" * 64,
        metrics=_metrics(),
    )

    try:
        write_long_run_report(tmp_path / "report.json", [observation, observation])
    except ValueError as error:
        assert str(error) == "journey names must be unique"
    else:
        raise AssertionError("duplicate long-run journey names must be rejected")
