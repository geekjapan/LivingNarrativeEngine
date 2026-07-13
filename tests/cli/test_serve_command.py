"""``living-narrative serve`` CLI wiring (docs/issues/020).

Does not actually start uvicorn (it blocks forever) — patches ``living_narrative.web.server
.run_server`` to capture the call instead. CLI-only tests run regardless of whether the ``web``
extra is installed; the actual server import is covered by the web matrix jobs.
"""

import re
import sys

import pytest
from typer.testing import CliRunner

from living_narrative.cli import app

runner = CliRunner()


def _normalize_help_output(output: str) -> str:
    """Strips ANSI escapes and collapses whitespace so option-name assertions survive rich's
    CI-only color + narrow-panel wrapping (GitHub Actions detection can wrap long option names
    mid-token at hyphens)."""
    no_ansi = re.sub(r"\x1b\[[0-9;]*m", "", output)
    return re.sub(r"\s+", "", no_ansi)


def test_serve_help_has_no_host_option():
    result = runner.invoke(app, ["serve", "--help"])
    normalized = _normalize_help_output(result.output)

    assert result.exit_code == 0, result.output
    assert "--host" not in normalized
    assert "--project-root" in normalized
    assert "--port" in normalized


def test_serve_rejects_missing_project_root(tmp_path):
    result = runner.invoke(
        app, ["serve", "--project-root", str(tmp_path / "does_not_exist"), "--port", "9000"]
    )

    assert result.exit_code == 2


def test_serve_delegates_to_run_server_with_no_host_override(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    pytest.importorskip("uvicorn")
    import living_narrative.web.server as server

    captured = {}

    def fake_run_server(project_root, *, port=8765):
        captured["project_root"] = project_root
        captured["port"] = port

    monkeypatch.setattr(server, "run_server", fake_run_server)

    result = runner.invoke(app, ["serve", "--project-root", str(tmp_path), "--port", "9001"])

    assert result.exit_code == 0, result.output
    assert captured == {"project_root": tmp_path, "port": 9001}


def test_serve_reports_missing_extra_cleanly(tmp_path, monkeypatch):
    # Simulate the 'web' extra not being installed: `from living_narrative.web.server import
    # run_server` inside cli.serve.serve() raises ImportError when the submodule resolves to
    # None in sys.modules (the standard "import halted" sentinel — see importlib docs).
    monkeypatch.setitem(sys.modules, "living_narrative.web.server", None)

    result = runner.invoke(app, ["serve", "--project-root", str(tmp_path), "--port", "9002"])

    assert result.exit_code == 2
    assert "web" in result.output
    assert "uv sync --extra web" in result.output
