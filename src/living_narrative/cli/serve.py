"""``living-narrative serve``: FastAPI web UI over a directory of projects (docs/issues/020).

``fastapi``/``uvicorn`` are optional (``uv sync --extra web``) and imported lazily inside the
command body — never at module scope — so importing ``living_narrative.cli`` (and therefore the
whole CLI/core test suite) never requires the ``web`` extra to be installed.
"""

from pathlib import Path

import typer

from living_narrative.cli._common import usage_error


def serve(
    project_root: Path = typer.Option(
        ..., "--project-root", help="Directory to scan for */project.yaml"
    ),
    port: int = typer.Option(8765, "--port", help="Port to bind (host is always 127.0.0.1)"),
) -> None:
    """Serve the web UI over ``--project-root``. Binds to 127.0.0.1 only (no host override)."""
    try:
        from living_narrative.web.server import run_server
    except ImportError:
        usage_error("the 'web' extra is not installed — run `uv sync --extra web` to use `serve`")

    if not project_root.is_dir():
        usage_error(f"project root not found: {project_root}")

    run_server(project_root, port=port)
