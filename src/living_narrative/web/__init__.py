"""Thin FastAPI web UI over the existing engine (docs/issues/020, Track B).

Not imported from ``living_narrative.cli`` at module scope — see ``cli.serve`` for the lazy
import that keeps the optional ``web`` extra (fastapi/uvicorn) out of the core import path.
"""
