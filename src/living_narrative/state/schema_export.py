"""Export JSON Schema from state Pydantic models."""

from pathlib import Path

import typer
import yaml

from living_narrative.state import models

SCHEMA_MODELS = [
    models.WorldState,
    models.FactionState,
    models.CharacterState,
    models.InventoryItem,
    models.CharacterVisualProfile,
    models.BackgroundVisualProfile,
    models.EncounterThreatCondition,
    models.EncounterEntry,
    models.StyleLockProfile,
    models.VisualProfilesState,
    models.VoiceProfile,
    models.CharacterVoiceProfile,
    models.VoiceProfilesState,
    models.RelationshipState,
    models.HiddenFact,
    models.SceneState,
    models.CanonEntry,
    models.ReaderStateEntry,
    models.GmVaultEntry,
    models.TimelineEntry,
    models.UnresolvedThread,
    models.Quest,
    models.Event,
    models.WorldStateBundle,
]


def export_state_schemas(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for model in SCHEMA_MODELS:
        path = output_dir / f"{model.__name__}.schema.yaml"
        path.write_text(
            yaml.safe_dump(model.model_json_schema(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )


def _main(output: Path) -> None:
    export_state_schemas(output)
    typer.echo(f"Exported state schemas to {output}")


def main() -> None:
    typer.run(_main)


__all__ = ["SCHEMA_MODELS", "export_state_schemas"]
