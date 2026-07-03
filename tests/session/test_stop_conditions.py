from living_narrative.pipeline.models import CheckResult
from living_narrative.random.models import Roll
from living_narrative.session.stop_conditions import StopConditionName, evaluate_stop_conditions
from living_narrative.state.diff import StateDiff, StateDiffChange
from living_narrative.state.models import ProjectConfig, Visibility


def _project(**overrides):
    data = {
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
    }
    data.update(overrides)
    return ProjectConfig.model_validate(data)


def _diff(change):
    return StateDiff(id="diff_0001", turn=1, changes=[change])


def test_character_death_uses_status_transition():
    result = evaluate_stop_conditions(
        project=_project(),
        autonomy_level="assist",
        diff=_diff(
            StateDiffChange(
                target="character",
                id="char_001",
                op="set",
                path="status",
                value="dead",
                visibility=Visibility.CANON,
            )
        ),
        checks=[],
    )

    assert [item.name for item in result] == [StopConditionName.CHARACTER_DEATH]
    assert result[0].should_stop is True


def test_heavy_roll_failure_requires_critical_failure():
    failure = Roll(
        id="roll_0001",
        turn=1,
        type="chance",
        outcome="failure",
        severity="critical",
    )
    success = failure.model_copy(update={"id": "roll_0002", "outcome": "success"})

    matched = evaluate_stop_conditions(
        project=_project(),
        autonomy_level="assist",
        diff=StateDiff(id="diff_0001", turn=1),
        checks=[],
        rolls=[failure],
    )
    not_matched = evaluate_stop_conditions(
        project=_project(),
        autonomy_level="assist",
        diff=StateDiff(id="diff_0001", turn=1),
        checks=[],
        rolls=[success],
    )

    assert matched[0].name == StopConditionName.HEAVY_ROLL_FAILURE
    assert not_matched == []


def test_scene_end_uses_status_transition():
    result = evaluate_stop_conditions(
        project=_project(),
        autonomy_level="assist",
        diff=_diff(
            StateDiffChange(
                target="scene",
                id="scene_001",
                op="set",
                path="status",
                value="ended",
                visibility=Visibility.CANON,
            )
        ),
        checks=[],
    )

    assert result[0].name == StopConditionName.SCENE_END


def test_disabled_condition_does_not_stop():
    result = evaluate_stop_conditions(
        project=_project(stop_conditions={"heavy_roll_failure": {"enabled": False}}),
        autonomy_level="assist",
        diff=StateDiff(id="diff_0001", turn=1),
        checks=[],
        rolls=[
            Roll(
                id="roll_0001",
                turn=1,
                type="chance",
                outcome="failure",
                severity="critical",
            )
        ],
    )

    assert result == []


def test_watch_logs_character_death_without_stopping_but_stops_stop_condition():
    project = _project(autonomy_level="watch")
    diff = _diff(
        StateDiffChange(
            target="character",
            id="char_001",
            op="set",
            path="status",
            value="dead",
            visibility=Visibility.CANON,
        )
    )

    results = evaluate_stop_conditions(
        project=project,
        autonomy_level="watch",
        diff=diff,
        checks=[],
        interventions=[{"type": "stop_condition"}],
    )

    by_name = {item.name: item for item in results}
    assert by_name[StopConditionName.CHARACTER_DEATH].log_only is True
    assert by_name[StopConditionName.STOP_CONDITION].should_stop is True


def test_god_stops_on_checker_error():
    result = evaluate_stop_conditions(
        project=_project(),
        autonomy_level="god",
        diff=StateDiff(id="diff_0001", turn=1),
        checks=[CheckResult(severity="error", message="boom")],
    )

    assert result[0].name == StopConditionName.CHECKER_ERROR
    assert result[0].should_stop is True
