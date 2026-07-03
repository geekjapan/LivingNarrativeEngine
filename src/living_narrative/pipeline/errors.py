"""Turn-pipeline level errors (raised before a turn directory exists)."""


class LoadError(RuntimeError):
    """Project or state failed to load; no ``turn_NNNN`` directory is created (SHALL NOT)."""


class UnresolvedTurnError(RuntimeError):
    """A prior turn is ``pending_review``/``stopped_for_review`` or has no valid ``meta.yaml``."""
