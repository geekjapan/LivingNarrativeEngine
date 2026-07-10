from copy import deepcopy

import pytest

from living_narrative.workspace.migrations import (
    DuplicateMigrationError,
    FutureSchemaVersionError,
    InvalidSchemaVersionError,
    MissingMigrationError,
    migrate_project_data,
    register_migration,
)


def test_missing_schema_version_is_treated_as_version_one():
    raw = {"title": "legacy"}

    assert migrate_project_data(raw) == {"schema_version": 1, "title": "legacy"}
    assert raw == {"title": "legacy"}


@pytest.mark.parametrize("version", [0, -1, True, "1", 1.0, None])
def test_invalid_schema_version_is_rejected(version):
    with pytest.raises(InvalidSchemaVersionError, match="positive integer"):
        migrate_project_data({"schema_version": version})


def test_future_schema_version_is_rejected():
    with pytest.raises(FutureSchemaVersionError, match="newer than supported"):
        migrate_project_data({"schema_version": 2})


def test_migrations_are_applied_in_order_without_mutating_input():
    raw = {"schema_version": 1, "steps": []}
    original = deepcopy(raw)
    registry = {
        1: lambda data: {**data, "schema_version": 2, "steps": [*data["steps"], "1-2"]},
        2: lambda data: {**data, "schema_version": 3, "steps": [*data["steps"], "2-3"]},
    }

    migrated = migrate_project_data(raw, registry=registry, current_version=3)

    assert migrated == {"schema_version": 3, "steps": ["1-2", "2-3"]}
    assert raw == original


def test_missing_migration_step_is_rejected():
    with pytest.raises(MissingMigrationError, match="version 2 to 3"):
        migrate_project_data(
            {"schema_version": 1},
            registry={1: lambda data: {**data, "schema_version": 2}},
            current_version=3,
        )


def test_duplicate_migration_registration_is_rejected():
    registry = {}
    register_migration(registry, 1, lambda data: data)

    with pytest.raises(DuplicateMigrationError, match="already registered"):
        register_migration(registry, 1, lambda data: data)
