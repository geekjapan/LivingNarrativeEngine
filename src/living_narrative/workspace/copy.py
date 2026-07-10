"""Safe directory-copy primitives shared by branch, backup, and restore."""

from __future__ import annotations

import shutil
import uuid
from collections.abc import Callable
from pathlib import Path


class WorkspaceCopyError(ValueError):
    """A workspace copy cannot be completed safely."""


def paths_overlap(first: Path, second: Path) -> bool:
    """Return whether two normalized paths are equal or contain one another."""
    first_resolved = first.resolve()
    second_resolved = second.resolve()
    return (
        first_resolved == second_resolved
        or first_resolved in second_resolved.parents
        or second_resolved in first_resolved.parents
    )


def publish_directory_atomic(destination: Path, populate: Callable[[Path], None]) -> Path:
    """Populate a temporary sibling and atomically publish it as ``destination``.

    The final destination must not exist. Any failed copy removes its temporary tree,
    so callers never observe a partial final destination.
    """
    destination = destination.resolve()
    if destination.exists():
        raise WorkspaceCopyError(f"copy destination already exists: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp-{uuid.uuid4().hex}")
    try:
        temporary.mkdir()
        populate(temporary)
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return destination


def copy_directory_atomic(source: Path, destination: Path) -> Path:
    """Copy ``source`` through a temporary sibling and atomically publish it."""
    source = source.resolve()
    destination = destination.resolve()
    if paths_overlap(source, destination):
        raise WorkspaceCopyError(
            f"copy source and destination must not contain one another: {source}, {destination}"
        )

    def populate(temporary: Path) -> None:
        copy_directory_into(source, temporary)

    return publish_directory_atomic(destination, populate)


def copy_directory_into(source: Path, destination: Path) -> Path:
    """Copy a source directory into an existing staging directory."""
    shutil.copytree(source, destination, dirs_exist_ok=True)
    return destination


__all__ = [
    "WorkspaceCopyError",
    "copy_directory_atomic",
    "copy_directory_into",
    "paths_overlap",
    "publish_directory_atomic",
]
