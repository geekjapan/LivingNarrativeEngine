import logging

import pytest
import yaml
from pydantic import ValidationError

from living_narrative.state.diff import (
    InverseStateDiff,
    StateDiff,
    StateDiffChange,
    StateDiffError,
    apply_state_diff,
    rollback,
)
from living_narrative.state.models import (
    CanonEntry,
    CharacterState,
    CharacterStatus,
    Event,
    GmVaultEntry,
    HiddenFact,
    RelationshipState,
    SceneState,
    SceneStatus,
    Visibility,
    WorldState,
    WorldStateBundle,
)
from living_narrative.state.schema_export import export_state_schemas
from living_narrative.state.store import StateLoadError, StateStore


def bundle() -> WorldStateBundle:
    return WorldStateBundle(
        world=WorldState(
            id="world_001",
            name="Mist Station",
            summary="A quiet station.",
            laws=[],
            parameters={"danger_level": 40},
        ),
        characters=[
            CharacterState(
                id="char_001",
                name="Aoi",
                role="detective",
                emotions={"fear": 95},
            )
        ],
        relationships=[
            RelationshipState(
                **{
                    "from": "char_001",
                    "to": "char_002",
                    "trust": 10,
                    "affection": 20,
                    "tension": 30,
                    "suspicion": 40,
                }
            )
        ],
        scenes=[
            SceneState(
                id="scene_001",
                location="Platform",
                time="night",
                hidden_facts=[
                    HiddenFact(
                        id="fact_001",
                        text="The caller is nearby.",
                        visibility=Visibility.CHARACTER,
                        known_by=["char_001"],
                    )
                ],
            )
        ],
        canon=[
            CanonEntry(
                id="canon_001",
                text="The station exists.",
                established_turn=1,
                source_event="event_0001",
            )
        ],
        gm_vault=[GmVaultEntry(id="gm_vault_001", text="The station is a trap.")],
    )


def test_state_models_validate_ids_ranges_status_and_event_conflicts():
    assert CharacterState(id="char_001", name="Aoi", role="lead").status == CharacterStatus.ALIVE
    assert SceneState(id="scene_001", location="x", time="y").status == SceneStatus.ACTIVE
    with pytest.raises(ValidationError):
        CharacterState(id="char1", name="Aoi", role="lead")
    with pytest.raises(ValidationError):
        WorldState(id="world_001", name="x", summary="y", parameters={"danger": 101})
    with pytest.raises(ValidationError):
        RelationshipState(
            **{
                "from": "char_001",
                "to": "char_001",
                "trust": 1,
                "affection": 1,
                "tension": 1,
                "suspicion": 1,
            }
        )
    with pytest.raises(ValidationError):
        Event(
            id="event_0001",
            turn=1,
            type="discovery",
            text="",
            visibility=Visibility.SCENE,
        )
    with pytest.raises(ValidationError):
        Event(
            id="event_0001",
            turn=1,
            type="discovery",
            text="A",
            visibility=Visibility.CHARACTER,
            known_by=["char_001"],
            hidden_from=["char_001"],
        )
    StateDiffChange(
        target="relationship",
        id="char_001__char_002",
        op="delta",
        path="trust",
        value=1,
        visibility=Visibility.CANON,
    )
    with pytest.raises(ValidationError):
        StateDiffChange(
            target="relationship",
            id="char_001-char_002",
            op="delta",
            path="trust",
            value=1,
            visibility=Visibility.CANON,
        )


def test_state_store_roundtrip_missing_empty_lenient_unknown_and_aggregate(tmp_path, caplog):
    state_dir = tmp_path / "state"
    StateStore.save(bundle(), state_dir)
    first = {path.name: path.read_bytes() for path in state_dir.glob("*.yaml")}
    loaded = StateStore.load(state_dir)
    StateStore.save(loaded, state_dir)
    assert first == {path.name: path.read_bytes() for path in state_dir.glob("*.yaml")}
    assert StateStore.load(state_dir).model_dump(mode="json") == loaded.model_dump(mode="json")

    (state_dir / "characters").rename(state_dir / "characters_gone")
    assert StateStore.load(state_dir).characters == []
    (state_dir / "characters_gone").rename(state_dir / "characters")
    (state_dir / "gm_vault.yaml").write_text("[]\n", encoding="utf-8")
    assert StateStore.load(state_dir).gm_vault == []
    (state_dir / "gm_vault.yaml").unlink()
    with pytest.raises(StateLoadError) as missing:
        StateStore.load(state_dir)
    assert missing.value.issues[0].file_path.name == "gm_vault.yaml"

    StateStore.save(bundle(), state_dir)
    character_path = state_dir / "characters" / "char_001.yaml"
    character = yaml.safe_load(character_path.read_text(encoding="utf-8"))
    character["favorite_color"] = "blue"
    character["emotions"]["fear"] = 200
    character_path.write_text(yaml.safe_dump(character, sort_keys=False), encoding="utf-8")
    scene_path = state_dir / "scenes" / "scene_001.yaml"
    scene = yaml.safe_load(scene_path.read_text(encoding="utf-8"))
    scene["active_characters"] = ["bad-id"]
    scene_path.write_text(yaml.safe_dump(scene, sort_keys=False), encoding="utf-8")
    with pytest.raises(StateLoadError) as aggregated:
        StateStore.load(state_dir)
    assert {issue.file_path.name for issue in aggregated.value.issues} == {
        "char_001.yaml",
        "scene_001.yaml",
    }

    character["emotions"]["fear"] = 50
    character_path.write_text(yaml.safe_dump(character, sort_keys=False), encoding="utf-8")
    scene["active_characters"] = ["char_001"]
    scene_path.write_text(yaml.safe_dump(scene, sort_keys=False), encoding="utf-8")
    caplog.set_level(logging.WARNING)
    loaded = StateStore.load(state_dir)
    assert any("favorite_color" in record.message for record in caplog.records)
    StateStore.save(loaded, state_dir)
    assert "favorite_color" in yaml.safe_load(character_path.read_text(encoding="utf-8"))


def test_state_diff_apply_reject_partial_clamp_and_inverse_roundtrip():
    original = bundle()
    diff = StateDiff(
        id="diff_001",
        turn=1,
        changes=[
            StateDiffChange(
                target="character",
                id="char_001",
                op="set",
                path="status",
                value="dead",
                visibility=Visibility.CANON,
            ),
            StateDiffChange(
                target="scene",
                id="scene_001",
                op="set",
                path="status",
                value="ended",
                visibility=Visibility.CANON,
            ),
            StateDiffChange(
                target="character",
                id="char_001",
                op="delta",
                path="emotions.fear",
                value=20,
                visibility=Visibility.CHARACTER,
            ),
            StateDiffChange(
                target="canon",
                id="canon_001",
                op="remove",
                visibility=Visibility.CANON,
            ),
        ],
    )

    partial = apply_state_diff(original, diff, selected_change_indexes={0, 1})
    assert partial.bundle.characters[0].status == "dead"
    assert partial.bundle.scenes[0].status == "ended"
    assert partial.bundle.characters[0].emotions["fear"] == 95

    result = apply_state_diff(original, diff)
    assert result.bundle.characters[0].emotions["fear"] == 100
    assert result.applied_changes[2].clamped
    assert result.applied_changes[2].computed_value == 115
    assert result.inverse_diff.changes[0].op == "add"
    assert result.inverse_diff.changes[0].value["id"] == "canon_001"
    restored = apply_state_diff(result.bundle, result.inverse_diff).bundle
    assert restored.model_dump(mode="json") == original.model_dump(mode="json")

    bad = StateDiff(
        id="diff_002",
        turn=2,
        changes=[
            StateDiffChange(
                target="character",
                id="char_001",
                op="set",
                path="status",
                value="dead",
                visibility=Visibility.CANON,
            ),
            StateDiffChange(
                target="canon",
                id="canon_099",
                op="remove",
                visibility=Visibility.CANON,
            ),
        ],
    )
    with pytest.raises(StateDiffError):
        apply_state_diff(original, bad)
    assert original.characters[0].status == CharacterStatus.ALIVE


def test_multi_turn_rollback_and_schema_export(tmp_path):
    start = bundle()
    diff1 = StateDiff(
        id="diff_001",
        turn=1,
        changes=[
            StateDiffChange(
                target="world",
                op="delta",
                path="parameters.danger_level",
                value=10,
                visibility=Visibility.CANON,
            )
        ],
    )
    diff2 = StateDiff(
        id="diff_002",
        turn=2,
        changes=[
            StateDiffChange(
                target="relationship",
                id="char_001__char_002",
                op="delta",
                path="trust",
                value=5,
                visibility=Visibility.CANON,
            )
        ],
    )
    diff3 = StateDiff(
        id="diff_003",
        turn=3,
        changes=[
            StateDiffChange(
                target="character",
                id="char_001",
                op="add",
                path="knowledge.knows",
                value="New clue",
                visibility=Visibility.CHARACTER,
            )
        ],
    )

    one = apply_state_diff(start, diff1)
    two = apply_state_diff(one.bundle, diff2)
    three = apply_state_diff(two.bundle, diff3)
    inverses = [
        InverseStateDiff.model_validate(one.inverse_diff.model_dump()),
        InverseStateDiff.model_validate(two.inverse_diff.model_dump()),
        InverseStateDiff.model_validate(three.inverse_diff.model_dump()),
    ]
    assert rollback(three.bundle, inverses).model_dump(mode="json") == start.model_dump(mode="json")

    export_state_schemas(tmp_path / "schemas")
    assert (tmp_path / "schemas" / "WorldState.schema.yaml").exists()
