import yaml

from living_narrative.intervention.ids import make_intervention_id_allocator


def test_allocator_starts_at_1_for_an_empty_runs_dir(tmp_path):
    allocate = make_intervention_id_allocator(tmp_path / "runs")
    assert allocate() == "int_0001"
    assert allocate() == "int_0002"


def test_allocator_continues_from_the_highest_existing_id_across_turns(tmp_path):
    runs = tmp_path / "runs"
    turn_dir = runs / "turn_0001"
    turn_dir.mkdir(parents=True)
    (turn_dir / "intervention.yaml").write_text(
        yaml.safe_dump({"turn": 1, "interventions": [{"id": "int_0007"}, {"id": "int_0003"}]}),
        encoding="utf-8",
    )

    allocate = make_intervention_id_allocator(runs)

    assert allocate() == "int_0008"
