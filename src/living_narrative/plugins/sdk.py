"""Project-local, allowlist-gated plugin runtime."""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from importlib import metadata
from typing import TYPE_CHECKING, Any, Literal, Protocol

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from living_narrative.llm.registry import ProviderFactory
    from living_narrative.media.registry import ImageProviderFactory
    from living_narrative.media.voice_registry import VoiceProviderFactory
    from living_narrative.narration.renderers import RendererFunc, RendererRegistry
    from living_narrative.pipeline.registry import SlotRegistry
    from living_narrative.safety.registry import Checker
    from living_narrative.state.models import LLMConfig, ProjectConfig

ENTRY_POINT_GROUP = "living_narrative.plugins"
logger = logging.getLogger(__name__)


class PluginDeclaration(Protocol):
    def register(self, sdk: PluginSDK) -> None: ...


PluginFunction = Callable[["PluginSDK"], None]


class PluginLoadError(BaseModel):
    name: str
    stage: Literal["discovery", "missing", "load", "register"]
    message: str
    reason: Literal[
        "ambiguous",
        "not_installed",
        "load_failed",
        "registration_failed",
        "collision",
    ]
    exception_type: str | None = None


class PluginLoadResult(BaseModel):
    loaded: list[str] = Field(default_factory=list)
    errors: list[PluginLoadError] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


class PluginCollisionError(ValueError):
    pass


@dataclass
class PluginRuntime:
    """One project's isolated clone of every built-in registry."""

    llm_providers: dict[str, ProviderFactory]
    checkers: dict[str, Checker]
    renderers: RendererRegistry
    slots: SlotRegistry
    image_providers: dict[str, ImageProviderFactory]
    voice_providers: dict[str, VoiceProviderFactory]
    load_result: PluginLoadResult = field(default_factory=PluginLoadResult)
    baseline_checkers: frozenset[str] = field(default_factory=frozenset)

    def clone(self) -> PluginRuntime:
        return PluginRuntime(
            llm_providers=self.llm_providers.copy(),
            checkers=self.checkers.copy(),
            renderers=self.renderers.copy(),
            slots=self.slots.copy(),
            image_providers=self.image_providers.copy(),
            voice_providers=self.voice_providers.copy(),
            baseline_checkers=self.baseline_checkers,
        )

    def adopt(self, staged: PluginRuntime) -> None:
        self.llm_providers = staged.llm_providers
        self.checkers = staged.checkers
        self.renderers = staged.renderers
        self.slots = staged.slots
        self.image_providers = staged.image_providers
        self.voice_providers = staged.voice_providers

    def create_llm_provider(self, config: LLMConfig, **kwargs: object):
        from living_narrative.llm.errors import ProviderRegistryError

        try:
            factory = self.llm_providers[config.provider]
        except KeyError as exc:
            raise ProviderRegistryError(
                f"Unknown LLM provider {config.provider!r}; available providers: "
                f"{', '.join(sorted(self.llm_providers))}"
            ) from exc
        return factory(config, **kwargs)

    def create_image_provider(self, name: str):
        from living_narrative.media.errors import ImageProviderRegistryError

        try:
            return self.image_providers[name]()
        except KeyError as exc:
            raise ImageProviderRegistryError(
                f"Unknown image provider {name!r}; available providers: "
                f"{', '.join(sorted(self.image_providers))}"
            ) from exc

    def create_voice_provider(self, name: str):
        from living_narrative.media.errors import VoiceProviderRegistryError

        try:
            return self.voice_providers[name]()
        except KeyError as exc:
            raise VoiceProviderRegistryError(
                f"Unknown voice provider {name!r}; available providers: "
                f"{', '.join(sorted(self.voice_providers))}"
            ) from exc

    def run_checkers(self, context, narration_text, resolved_events, diff_candidate):
        from living_narrative.pipeline.models import CheckResult

        results = []
        for checker in self.checkers.values():
            findings = checker(context, narration_text, resolved_events, diff_candidate)
            results.extend(
                CheckResult(
                    severity=finding.severity,
                    message=finding.message,
                    source=finding.checker,
                    related_ids=finding.related_ids,
                )
                for finding in findings
            )
        return results


class PluginSDK:
    """Registration-only view of a staged project runtime."""

    def __init__(self, runtime: PluginRuntime) -> None:
        self._runtime = runtime

    @staticmethod
    def _register(registry: dict[str, Any], kind: str, name: str, value: Any) -> None:
        if name in registry:
            raise PluginCollisionError(f"{kind} name {name!r} is already registered")
        registry[name] = value

    def register_llm_provider(self, name: str, factory: ProviderFactory) -> None:
        self._register(self._runtime.llm_providers, "LLM provider", name, factory)

    def register_checker(self, name: str, checker: Checker) -> None:
        self._register(self._runtime.checkers, "checker", name, checker)

    def register_renderer(self, name: str, renderer: RendererFunc) -> None:
        if self._runtime.renderers.contains(name):
            raise PluginCollisionError("renderer name is already registered")
        self._runtime.renderers.register(name, renderer)

    def register_pipeline_slot(self, name: str, slot: Any) -> None:
        if self._runtime.slots.contains(name):
            raise PluginCollisionError("pipeline slot name is already registered")
        self._runtime.slots.register(name, slot)

    def register_image_provider(self, name: str, factory: ImageProviderFactory) -> None:
        self._register(self._runtime.image_providers, "image provider", name, factory)

    def register_voice_provider(self, name: str, factory: VoiceProviderFactory) -> None:
        self._register(self._runtime.voice_providers, "voice provider", name, factory)


def _entry_points() -> Iterable[metadata.EntryPoint]:
    return metadata.entry_points(group=ENTRY_POINT_GROUP)


def default_plugin_runtime(*, slot_registry: SlotRegistry | None = None) -> PluginRuntime:
    from living_narrative.llm.registry import _PROVIDERS as llm_providers
    from living_narrative.media.registry import _PROVIDERS as image_providers
    from living_narrative.media.voice_registry import _PROVIDERS as voice_providers
    from living_narrative.narration.renderers import default_renderer_registry
    from living_narrative.pipeline.registry import default_registry
    from living_narrative.safety.registry import CHECKERS

    return PluginRuntime(
        llm_providers=llm_providers.copy(),
        checkers=CHECKERS.copy(),
        renderers=default_renderer_registry(),
        slots=slot_registry or default_registry(),
        image_providers=image_providers.copy(),
        voice_providers=voice_providers.copy(),
        baseline_checkers=frozenset(CHECKERS),
    )


def load_plugins(
    allowlist: Iterable[str],
    runtime: PluginRuntime,
    *,
    entry_points: Iterable[metadata.EntryPoint] | None = None,
) -> PluginLoadResult:
    """Transactionally register explicitly enabled entry points into one runtime."""
    enabled = set(allowlist)
    discovered = list(_entry_points() if entry_points is None else entry_points)
    selected = [entry_point for entry_point in discovered if entry_point.name in enabled]
    result = PluginLoadResult()

    counts = Counter(entry_point.name for entry_point in selected)
    ambiguous = {name for name, count in counts.items() if count > 1}
    for name in sorted(ambiguous):
        result.errors.append(
            PluginLoadError(
                name=name,
                stage="discovery",
                reason="ambiguous",
                message="multiple installed entry points use this enabled name",
            )
        )
    selected = [entry_point for entry_point in selected if entry_point.name not in ambiguous]

    found_names = {entry_point.name for entry_point in selected} | ambiguous
    for name in sorted(enabled - found_names):
        result.errors.append(
            PluginLoadError(
                name=name,
                stage="missing",
                reason="not_installed",
                message="enabled plugin is not installed",
            )
        )

    for entry_point in selected:
        try:
            declaration = entry_point.load()
        except Exception as exc:
            result.errors.append(
                PluginLoadError(
                    name=entry_point.name,
                    stage="load",
                    reason="load_failed",
                    message=f"load failed ({type(exc).__name__})",
                    exception_type=type(exc).__name__,
                )
            )
            continue
        staged = runtime.clone()
        try:
            register = getattr(declaration, "register", None)
            if register is not None:
                register(PluginSDK(staged))
            elif callable(declaration):
                declaration(PluginSDK(staged))
            else:
                raise TypeError("plugin entry point must be callable or expose register(sdk)")
        except Exception as exc:
            result.errors.append(
                PluginLoadError(
                    name=entry_point.name,
                    stage="register",
                    reason=(
                        "collision"
                        if isinstance(exc, PluginCollisionError)
                        else "registration_failed"
                    ),
                    message=f"register failed ({type(exc).__name__})",
                    exception_type=type(exc).__name__,
                )
            )
            continue
        runtime.adopt(staged)
        result.loaded.append(entry_point.name)
    runtime.load_result = result
    return result


def create_plugin_runtime(
    project: ProjectConfig,
    *,
    slot_registry: SlotRegistry | None = None,
    entry_points: Iterable[metadata.EntryPoint] | None = None,
) -> PluginRuntime:
    runtime = default_plugin_runtime(slot_registry=slot_registry)
    result = load_plugins(project.plugins, runtime, entry_points=entry_points)
    for error in result.errors:
        logger.warning("Plugin %s failed at %s (%s)", error.name, error.stage, error.reason)
    return runtime
