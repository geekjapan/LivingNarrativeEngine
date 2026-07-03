import pytest
import yaml


def _write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def write_turn(
    runs_dir,
    turn,
    *,
    status="applied",
    narration="",
    interventions=None,
    rolls=None,
    events=None,
    diff_changes=None,
    diff_applied=True,
    review_decision=None,
):
    turn_dir = runs_dir / f"turn_{turn:04d}"
    (turn_dir / "narration.md").parent.mkdir(parents=True, exist_ok=True)
    (turn_dir / "narration.md").write_text(
        f"---\nturn: {turn}\nstyle: novel\nvisibility: reader\n---\n\n{narration}\n",
        encoding="utf-8",
    )
    _write_yaml(turn_dir / "meta.yaml", {"status": status, "turn": turn})
    _write_yaml(
        turn_dir / "intervention.yaml",
        {"turn": turn, "interventions": interventions or [], "rejections": []},
    )
    _write_yaml(turn_dir / "rolls.yaml", rolls or [])
    _write_yaml(turn_dir / "events.yaml", events or [])
    _write_yaml(
        turn_dir / "state_diff.yaml",
        {
            "diff": {"id": f"diff_{turn:04d}", "turn": turn, "changes": diff_changes or []},
            "rejected_changes": [],
            "applied": diff_applied,
        },
    )
    if review_decision is not None:
        _write_yaml(turn_dir / "review.yaml", {"turn": turn, "decision": review_decision})
    return turn_dir


@pytest.fixture
def write_turn_dir():
    return write_turn
