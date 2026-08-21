from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from living_narrative.book.benchmark import benchmark_book
from living_narrative.workspace.loader import load_project


def test_benchmark_fixture_generator_creates_a_deterministic_nine_chapter_project(tmp_path):
    script = Path(__file__).parents[2] / "scripts" / "create_benchmark_fixture.py"
    first_output = tmp_path / "first"
    second_output = tmp_path / "second"

    for output in (first_output, second_output):
        result = subprocess.run(
            [sys.executable, str(script), "--output", str(output)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == str(output / "project.yaml")

    first = benchmark_book(load_project(first_output / "project.yaml").paths, name="ci-nine")
    second = benchmark_book(load_project(second_output / "project.yaml").paths, name="ci-nine")

    assert first.planned_chapters == 9
    assert first.production_run_count == 0
    assert first.benchmark_fingerprint == second.benchmark_fingerprint


def test_nine_chapter_fixture_matches_the_versioned_benchmark_baseline(tmp_path):
    script = Path(__file__).parents[2] / "scripts" / "create_benchmark_fixture.py"
    output = tmp_path / "fixture"
    baseline_path = Path(__file__).parents[1] / "fixtures" / "benchmark-v2-baseline.json"
    subprocess.run(
        [sys.executable, str(script), "--output", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )

    observed = benchmark_book(load_project(output / "project.yaml").paths, name="ci-nine")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    assert baseline["schema_version"] == 2
    assert baseline["fixture"] == "ci-nine"
    assert observed.benchmark_fingerprint == baseline["benchmark_fingerprint"]
    assert observed.artifact_fingerprint == baseline["artifact_fingerprint"]
    assert observed.production_run_fingerprint == baseline["production_run_fingerprint"]
    assert str(output) not in baseline_path.read_text(encoding="utf-8")
