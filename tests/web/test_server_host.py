"""``serve`` must bind to 127.0.0.1 only — no configurable host (docs/issues/020, security floor).

Skips entirely when the optional ``web`` extra is not installed.
"""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("uvicorn")

from living_narrative.web import server  # noqa: E402


def test_host_constant_is_loopback_only():
    assert server.HOST == "127.0.0.1"


def test_run_server_always_binds_loopback(tmp_path, monkeypatch):
    captured = {}

    def fake_run(app, *, host, port):
        captured["host"] = host
        captured["port"] = port

    monkeypatch.setattr(server.uvicorn, "run", fake_run)

    server.run_server(tmp_path, port=9999)

    assert captured == {"host": "127.0.0.1", "port": 9999}
