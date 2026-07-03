"""Workspace directory layout (project_plan.md Appendix C, spec-foundation.md D117)."""

# The 7 state files whose absence is a fail-fast error (spec-foundation.md D117).
REQUIRED_STATE_FILES = (
    "world.yaml",
    "canon.yaml",
    "reader_state.yaml",
    "gm_vault.yaml",
    "relationships.yaml",
    "timeline.yaml",
    "unresolved_threads.yaml",
)

# Created by init, but its absence is not fail-fast (loads as an empty collection).
OPTIONAL_STATE_FILES = ("factions.yaml",)

STATE_SUBDIRS = ("scenes", "characters")

# Minimal empty-world content for init; add-cli-and-sample replaces this with real content.
MINIMAL_STATE_CONTENT: dict[str, str] = {
    "world.yaml": "{}\n",
    "canon.yaml": "[]\n",
    "reader_state.yaml": "[]\n",
    "gm_vault.yaml": "[]\n",
    "relationships.yaml": "[]\n",
    "timeline.yaml": "[]\n",
    "unresolved_threads.yaml": "[]\n",
    "factions.yaml": "[]\n",
}
