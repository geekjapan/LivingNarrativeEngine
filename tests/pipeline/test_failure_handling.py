import yaml

from living_narrative.llm.errors import StructuredOutputError
from living_narrative.pipeline import TurnPipeline, TurnStatus, default_registry


def test_unregistered_renderer_style_fails_turn_and_keeps_partial_artifacts(
    tmp_path, build_project
):
    project_path = build_project(tmp_path)

    result = TurnPipeline().run(project_path, renderer_style="script")

    assert result.status == TurnStatus.FAILED
    assert (result.turn_dir / "intervention.yaml").exists()
    assert (result.turn_dir / "events.yaml").exists()
    assert (result.turn_dir / "rolls.yaml").exists()
    assert not (result.turn_dir / "narration.md").exists()
    assert not (result.turn_dir / "checks.yaml").exists()
    assert not (result.turn_dir / "state_diff.yaml").exists()

    meta = yaml.safe_load((result.turn_dir / "meta.yaml").read_text(encoding="utf-8"))
    assert meta["status"] == "failed"
    assert meta["error"]["phase"] == "narrate"
    assert "script" in meta["error"]["message"]


def test_llm_provider_typed_exception_fails_act_phase(tmp_path, build_project):
    project_path = build_project(tmp_path)
    registry = default_registry()

    def failing_act(context, world_events, gateway, interventions=(), past_events=None):
        raise StructuredOutputError(
            provider_name="mock", model="mock-v1", schema_name="X", last_error="boom"
        )

    registry.register("act", failing_act)

    result = TurnPipeline(registry=registry).run(project_path)

    assert result.status == TurnStatus.FAILED
    meta = yaml.safe_load((result.turn_dir / "meta.yaml").read_text(encoding="utf-8"))
    assert meta["error"]["phase"] == "act"
    assert meta["error"]["exception_type"] == "StructuredOutputError"
