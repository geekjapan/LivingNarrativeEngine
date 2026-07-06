"""Uvicorn entry point for the web UI (docs/issues/020).

``HOST`` is hardcoded to loopback-only — this is a security floor (rules/security.md), not a
configurable option, so there is deliberately no ``host=`` parameter anywhere in this module or
in ``cli.serve``.
"""

from pathlib import Path

import uvicorn

from living_narrative.web.app import create_app

HOST = "127.0.0.1"


def run_server(project_root: Path, *, port: int = 8765) -> None:
    """Build the app for ``project_root`` and serve it on ``HOST``:``port`` (blocking)."""
    app = create_app(project_root)
    uvicorn.run(app, host=HOST, port=port)
