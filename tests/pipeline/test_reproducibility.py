import shutil

import yaml

from living_narrative.pipeline import TurnPipeline


def test_same_seed_and_config_reproduces_events_and_meta(tmp_path, build_project):
    project_a = build_project(tmp_path / "a")
    project_b = build_project(tmp_path / "b")
    # same random_seed comes from create_project's uuid4 by default; force equality.
    seed_data = yaml.safe_load(project_a.read_text(encoding="utf-8"))
    project_b_data = yaml.safe_load(project_b.read_text(encoding="utf-8"))
    project_b_data["random_seed"] = seed_data["random_seed"]
    project_b.write_text(yaml.safe_dump(project_b_data, allow_unicode=True), encoding="utf-8")

    result_a = TurnPipeline().run(project_a)
    result_b = TurnPipeline().run(project_b)

    events_a = (result_a.turn_dir / "events.yaml").read_text(encoding="utf-8")
    events_b = (result_b.turn_dir / "events.yaml").read_text(encoding="utf-8")
    assert events_a == events_b

    narration_a = (result_a.turn_dir / "narration.md").read_text(encoding="utf-8")
    narration_b = (result_b.turn_dir / "narration.md").read_text(encoding="utf-8")
    assert narration_a == narration_b

    meta_a = yaml.safe_load((result_a.turn_dir / "meta.yaml").read_text(encoding="utf-8"))
    meta_b = yaml.safe_load((result_b.turn_dir / "meta.yaml").read_text(encoding="utf-8"))
    assert meta_a["rng_draws_consumed"] == meta_b["rng_draws_consumed"]
    assert [c["model"] for c in meta_a["llm_calls"]] == [c["model"] for c in meta_b["llm_calls"]]


def test_rerunning_same_project_dir_is_deterministic(tmp_path, build_project):
    project_path = build_project(tmp_path)
    backup = tmp_path / "backup"
    shutil.copytree(tmp_path / "project", backup)

    first = TurnPipeline().run(project_path)
    first_events = (first.turn_dir / "events.yaml").read_text(encoding="utf-8")

    shutil.rmtree(tmp_path / "project")
    shutil.copytree(backup, tmp_path / "project")

    second = TurnPipeline().run(project_path)
    second_events = (second.turn_dir / "events.yaml").read_text(encoding="utf-8")

    assert first_events == second_events
