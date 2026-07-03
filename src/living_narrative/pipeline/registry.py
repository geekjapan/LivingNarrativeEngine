"""Name-keyed slot registry (D108/D113): TurnPipeline never imports a slot implementation."""

from typing import Any

SLOT_NAMES = ("simulate", "act", "resolve", "build_diff", "check")


class SlotRegistry:
    def __init__(self) -> None:
        self._slots: dict[str, Any] = {}

    def register(self, name: str, slot: Any) -> None:
        self._slots[name] = slot

    def get(self, name: str) -> Any:
        try:
            return self._slots[name]
        except KeyError as exc:
            raise KeyError(f"no slot registered for {name!r}") from exc


def default_registry() -> SlotRegistry:
    """A fresh registry pre-loaded with the built-in minimal slots."""
    from living_narrative.pipeline.builtin_slots import register_builtin_slots

    registry = SlotRegistry()
    register_builtin_slots(registry)
    return registry
