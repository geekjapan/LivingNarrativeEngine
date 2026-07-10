"""In-memory migrations for project configuration dictionaries."""

from collections.abc import Callable, Mapping
from copy import deepcopy
from typing import Any

CURRENT_SCHEMA_VERSION = 1

ProjectData = dict[str, Any]
Migration = Callable[[ProjectData], ProjectData]
MigrationRegistry = dict[int, Migration]


class SchemaMigrationError(ValueError):
    """Base error for an invalid or unsupported project schema migration."""


class InvalidSchemaVersionError(SchemaMigrationError):
    """Raised when ``schema_version`` is not a positive integer."""


class FutureSchemaVersionError(SchemaMigrationError):
    """Raised when a project uses a schema newer than this engine supports."""


class MissingMigrationError(SchemaMigrationError):
    """Raised when a required consecutive migration is not registered."""


class DuplicateMigrationError(SchemaMigrationError):
    """Raised when two migrations are registered for the same source version."""


MIGRATIONS: MigrationRegistry = {}


def register_migration(
    registry: MigrationRegistry, from_version: int, migration: Migration
) -> None:
    """Register one ``from_version`` → ``from_version + 1`` transformation."""
    if isinstance(from_version, bool) or not isinstance(from_version, int) or from_version < 1:
        raise InvalidSchemaVersionError(
            f"migration source version must be a positive integer, got {from_version!r}"
        )
    if from_version in registry:
        raise DuplicateMigrationError(
            f"migration from schema version {from_version} is already registered"
        )
    registry[from_version] = migration


def migrate_project_data(
    raw: Mapping[str, Any],
    *,
    registry: Mapping[int, Migration] = MIGRATIONS,
    current_version: int = CURRENT_SCHEMA_VERSION,
) -> ProjectData:
    """Copy and migrate project data to ``current_version`` without touching disk."""
    version = raw.get("schema_version", 1)
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise InvalidSchemaVersionError(
            f"schema_version must be a positive integer, got {version!r}"
        )
    if version > current_version:
        raise FutureSchemaVersionError(
            f"project schema version {version} is newer than supported version {current_version}"
        )

    migrated = deepcopy(dict(raw))
    while version < current_version:
        migration = registry.get(version)
        if migration is None:
            raise MissingMigrationError(
                f"missing migration from schema version {version} to {version + 1}"
            )
        migrated = migration(deepcopy(migrated))
        if not isinstance(migrated, dict):
            raise SchemaMigrationError(
                f"migration from schema version {version} must return a dict"
            )
        expected = version + 1
        if migrated.get("schema_version") != expected:
            raise SchemaMigrationError(
                f"migration from schema version {version} must set schema_version to {expected}"
            )
        version = expected

    migrated.setdefault("schema_version", version)
    return migrated
