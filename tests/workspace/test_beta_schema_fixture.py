from copy import deepcopy
from pathlib import Path

import yaml

from living_narrative.state.validation import load_project_config
from living_narrative.workspace.migrations import CURRENT_SCHEMA_VERSION, migrate_project_data

FIXTURE = Path(__file__).parents[1] / "fixtures" / "beta-schema-v1" / "project.yaml"


def test_beta_schema_v1_fixture_loads_and_migrates_without_data_loss():
    raw = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    assert raw["schema_version"] == 1  # beta-schema-v1 freeze (ADR-0011)
    migrated = migrate_project_data(raw)

    legacy = deepcopy(raw)
    del legacy["schema_version"]
    assert migrate_project_data(legacy) == migrated

    report = load_project_config(FIXTURE)
    assert report.is_valid
    assert report.config is not None
    assert report.config.schema_version == CURRENT_SCHEMA_VERSION
