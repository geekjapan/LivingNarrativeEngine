import yaml

from living_narrative.pipeline import TurnPipeline, TurnStatus, default_registry
from living_narrative.pipeline.models import ActionCandidate, ActRecord


def test_agent_runtime_writes_agent_io_checks_and_state_diff(tmp_path, build_project):
    project_path = build_project(tmp_path)

    result = TurnPipeline().run(project_path)

    assert result.status == TurnStatus.APPLIED
    expected_agent_io = (
        "simulate.yaml",
        "act.yaml",
        "act_candidates.yaml",
        "resolve.yaml",
        "build_diff.yaml",
        "check.yaml",
    )
    for name in expected_agent_io:
        assert (result.turn_dir / "agent_io" / name).exists()
    assert yaml.safe_load((result.turn_dir / "checks.yaml").read_text(encoding="utf-8")) == {
        "findings": []
    }
    assert (result.turn_dir / "state_diff.yaml").exists()


def test_agent_runtime_blocks_auto_apply_on_leak_and_continuity_errors(tmp_path, build_project):
    project_path = build_project(
        tmp_path,
        hidden_facts=[
            {
                "id": "fact_001",
                "text": "mock leaked secret",
                "visibility": "gm_only",
                "known_by": [],
            }
        ],
    )

    registry = default_registry()
    registry.register(
        "act",
        lambda context, world_events, gateway, interventions=(): (
            [
                ActionCandidate(
                    character_id="char_001",
                    action_text="mock leaked secret",
                    visibility="reader",
                )
            ],
            [
                ActRecord(
                    character_id="char_001",
                    prompt_template_name="test",
                    request=[],
                    response={},
                )
            ],
        ),
    )

    result = TurnPipeline(registry=registry).run(project_path)

    checks = yaml.safe_load((result.turn_dir / "checks.yaml").read_text(encoding="utf-8"))
    assert result.status == TurnStatus.STOPPED_FOR_REVIEW
    assert any(item["severity"] == "error" for item in checks["findings"])
