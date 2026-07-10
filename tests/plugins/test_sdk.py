from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import Any

import pytest
import yaml

from living_narrative.plugins import create_plugin_runtime, default_plugin_runtime, load_plugins


@dataclass
class FakeEntryPoint:
    name: str
    declaration: Any = None
    error: Exception | None = None
    load_calls: int = 0

    def load(self) -> Any:
        self.load_calls += 1
        if self.error is not None:
            raise self.error
        return self.declaration


@pytest.fixture
def runtime():
    return default_plugin_runtime()


def test_default_plugin_runtime_imports_in_fresh_process():
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from living_narrative.plugins import default_plugin_runtime; "
            "assert default_plugin_runtime().llm_providers",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_empty_allowlist_clones_builtins_without_global_mutation(runtime):
    other = default_plugin_runtime()

    result = load_plugins([], runtime, entry_points=[])

    assert result.ok
    assert runtime.llm_providers == other.llm_providers
    assert runtime.llm_providers is not other.llm_providers
    assert runtime.checkers == other.checkers
    assert runtime.checkers is not other.checkers


def test_unallowlisted_entry_point_is_never_loaded(runtime):
    disabled = FakeEntryPoint("disabled", lambda sdk: None)

    result = load_plugins([], runtime, entry_points=[disabled])

    assert disabled.load_calls == 0
    assert result.loaded == []


def test_duplicate_allowlisted_name_is_rejected_before_any_load(runtime):
    first = FakeEntryPoint("duplicate", lambda api: None)
    second = FakeEntryPoint("duplicate", lambda api: None)
    unique = FakeEntryPoint("unique", lambda api: api.register_renderer("unique", object()))

    result = load_plugins(["duplicate", "unique"], runtime, entry_points=[first, unique, second])

    assert first.load_calls == second.load_calls == 0
    assert unique.load_calls == 1
    assert result.loaded == ["unique"]
    assert len(result.errors) == 1
    assert result.errors[0].reason == "ambiguous"


def test_only_allowlisted_plugin_registers(runtime):
    enabled = FakeEntryPoint("enabled", lambda api: api.register_renderer("external", object()))
    disabled = FakeEntryPoint("disabled", lambda api: api.register_renderer("bad", object()))

    result = load_plugins(["enabled"], runtime, entry_points=[disabled, enabled])

    assert result.loaded == ["enabled"]
    assert enabled.load_calls == 1
    assert disabled.load_calls == 0
    assert runtime.renderers.get("external") is not None
    with pytest.raises(KeyError):
        runtime.renderers.get("bad")


def test_missing_and_load_failure_are_structured_and_later_plugin_continues(runtime):
    entries = [
        FakeEntryPoint("bad-import", error=ImportError("dependency missing")),
        FakeEntryPoint("good", lambda api: api.register_renderer("good", object())),
    ]
    result = load_plugins(["not-installed", "bad-import", "good"], runtime, entry_points=entries)

    assert result.loaded == ["good"]
    assert [(error.name, error.stage, error.reason) for error in result.errors] == [
        ("not-installed", "missing", "not_installed"),
        ("bad-import", "load", "load_failed"),
    ]


def test_plugin_exception_text_is_never_exposed_or_logged(runtime, caplog):
    secret = "API_KEY=super-secret /Users/private/key.txt"
    entry = FakeEntryPoint("secret-failure", error=RuntimeError(secret))

    with caplog.at_level("WARNING"):
        result = load_plugins(["secret-failure"], runtime, entry_points=[entry])

    error = result.errors[0]
    assert error.message == "load failed (RuntimeError)"
    assert error.exception_type == "RuntimeError"
    assert secret not in error.model_dump_json()
    assert secret not in caplog.text


def test_collision_rejects_plugin_without_overwriting_builtin(runtime):
    original = runtime.llm_providers["mock"]
    collision = FakeEntryPoint("collision", lambda api: api.register_llm_provider("mock", object()))

    result = load_plugins(["collision"], runtime, entry_points=[collision])

    assert result.errors[0].reason == "collision"
    assert runtime.llm_providers["mock"] is original


def test_register_then_raise_rolls_back_and_later_plugin_continues(runtime):
    def partial(api):
        api.register_renderer("rolled-back", object())
        raise RuntimeError("after registration")

    entries = [
        FakeEntryPoint("partial", partial),
        FakeEntryPoint("good", lambda api: api.register_renderer("committed", object())),
    ]

    result = load_plugins(["partial", "good"], runtime, entry_points=entries)

    assert result.loaded == ["good"]
    assert result.errors[0].reason == "registration_failed"
    with pytest.raises(KeyError):
        runtime.renderers.get("rolled-back")
    assert runtime.renderers.get("committed") is not None


def test_all_six_registry_kinds_are_project_local(runtime):
    other = default_plugin_runtime()
    values = {name: object() for name in ("llm", "checker", "renderer", "slot", "image", "voice")}

    def register_all(api):
        api.register_llm_provider("external", values["llm"])
        api.register_checker("external", values["checker"])
        api.register_renderer("external", values["renderer"])
        api.register_pipeline_slot("external", values["slot"])
        api.register_image_provider("external", values["image"])
        api.register_voice_provider("external", values["voice"])

    result = load_plugins(["all"], runtime, entry_points=[FakeEntryPoint("all", register_all)])

    assert result.ok
    assert runtime.llm_providers["external"] is values["llm"]
    assert runtime.checkers["external"] is values["checker"]
    assert runtime.renderers.get("external") is values["renderer"]
    assert runtime.slots.get("external") is values["slot"]
    assert runtime.image_providers["external"] is values["image"]
    assert runtime.voice_providers["external"] is values["voice"]
    assert "external" not in other.llm_providers
    assert "external" not in other.checkers
    with pytest.raises(KeyError):
        other.renderers.get("external")


def test_sdk_exposes_registration_only(runtime):
    captured = {}

    def inspect(api):
        captured["surface"] = {name for name in dir(api) if not name.startswith("_")}

    load_plugins(["inspect"], runtime, entry_points=[FakeEntryPoint("inspect", inspect)])

    assert captured["surface"] == {
        "register_checker",
        "register_image_provider",
        "register_llm_provider",
        "register_pipeline_slot",
        "register_renderer",
        "register_voice_provider",
    }


def test_turn_pipeline_consumes_project_renderer_plugin(tmp_path, build_project, monkeypatch):
    from living_narrative.pipeline import TurnPipeline, TurnStatus
    from living_narrative.plugins import sdk as sdk_module

    project_path = build_project(tmp_path)
    project = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    project.update({"plugins": ["project-renderer"], "renderer": "project-style"})
    project_path.write_text(
        yaml.safe_dump(project, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    entry_point = FakeEntryPoint(
        "project-renderer",
        lambda api: api.register_renderer(
            "project-style", lambda context, mood, tone: "PLUGIN PROJECT OUTPUT"
        ),
    )
    monkeypatch.setattr(sdk_module, "_entry_points", lambda: [entry_point])

    result = TurnPipeline().run(project_path)

    assert result.status == TurnStatus.APPLIED
    assert "PLUGIN PROJECT OUTPUT" in (result.turn_dir / "narration.md").read_text(encoding="utf-8")
    assert entry_point.load_calls == 1


@pytest.mark.parametrize("plugin_kind", ["renderer", "missing"])
def test_project_plugins_preserve_caller_custom_check_slot(
    tmp_path, build_project, monkeypatch, plugin_kind
):
    from living_narrative.pipeline import TurnPipeline, TurnStatus, default_registry
    from living_narrative.pipeline.models import CheckResult
    from living_narrative.plugins import sdk as sdk_module

    project_path = build_project(tmp_path)
    project = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    project["plugins"] = [plugin_kind]
    project_path.write_text(
        yaml.safe_dump(project, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    entries = []
    if plugin_kind == "renderer":
        entries.append(
            FakeEntryPoint("renderer", lambda api: api.register_renderer("unused-style", object()))
        )
    monkeypatch.setattr(sdk_module, "_entry_points", lambda: entries)
    registry = default_registry()
    registry.register(
        "check",
        lambda *args: [CheckResult(severity="error", message="custom", source="custom")],
    )

    result = TurnPipeline(registry=registry).run(project_path)

    assert result.status == TurnStatus.STOPPED_FOR_REVIEW


def test_project_runtime_provider_and_media_factories_are_consumed(runtime):
    llm = object()
    image = object()
    voice = object()

    def register(api):
        api.register_llm_provider("local", lambda config, **kwargs: llm)
        api.register_image_provider("local", lambda: image)
        api.register_voice_provider("local", lambda: voice)

    load_plugins(["local"], runtime, entry_points=[FakeEntryPoint("local", register)])

    from living_narrative.state.models import LLMConfig

    assert runtime.create_llm_provider(LLMConfig(provider="local", model="x")) is llm
    assert runtime.create_image_provider("local") is image
    assert runtime.create_voice_provider("local") is voice


def test_create_plugin_runtime_isolates_two_projects(tmp_path, build_project):
    """Project A enables a plugin; a second, allowlist-empty Project B must never see it
    (issue 049 problem #4: project-scoped runtimes must not leak via module globals)."""
    from living_narrative.workspace.loader import load_project

    project_a_path = build_project(tmp_path / "a")
    project_a_yaml = yaml.safe_load(project_a_path.read_text(encoding="utf-8"))
    project_a_yaml["plugins"] = ["project-a-plugin"]
    project_a_path.write_text(
        yaml.safe_dump(project_a_yaml, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    project_b_path = build_project(tmp_path / "b")

    project_a = load_project(project_a_path).config
    project_b = load_project(project_b_path).config
    assert project_b.plugins == []

    entry_point = FakeEntryPoint(
        "project-a-plugin",
        lambda api: api.register_renderer("project-a-style", object()),
    )

    runtime_a = create_plugin_runtime(project_a, entry_points=[entry_point])
    runtime_b = create_plugin_runtime(project_b, entry_points=[entry_point])

    assert runtime_a.renderers.get("project-a-style") is not None
    with pytest.raises(KeyError):
        runtime_b.renderers.get("project-a-style")
    assert entry_point.load_calls == 1  # never loaded for project B's empty allowlist
