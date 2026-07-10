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
    BackgroundVisualProfile,
    CanonEntry,
    CharacterState,
    CharacterStatus,
    CharacterVisualProfile,
    CharacterVoiceProfile,
    EncounterEntry,
    EncounterThreatCondition,
    Event,
    FactionState,
    GmVaultEntry,
    HiddenFact,
    InventoryItem,
    MemorySummary,
    Quest,
    RelationshipState,
    SceneState,
    SceneStatus,
    SpeechProfile,
    StyleLockProfile,
    ThreatStage,
    ThreatTrack,
    Visibility,
    VisualProfilesState,
    VoiceProfile,
    VoiceProfilesState,
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


def test_character_status_defaults_to_alive():
    assert CharacterState(id="char_001", name="Aoi", role="lead").status == CharacterStatus.ALIVE


def test_scene_status_defaults_to_active():
    assert SceneState(id="scene_001", location="x", time="y").status == SceneStatus.ACTIVE


def test_scene_summary_defaults_to_empty_string():
    assert SceneState(id="scene_001", location="x", time="y").summary == ""


def test_invalid_character_id_rejected():
    with pytest.raises(ValidationError):
        CharacterState(id="char1", name="Aoi", role="lead")


def test_percent_field_above_100_rejected():
    with pytest.raises(ValidationError):
        WorldState(id="world_001", name="x", summary="y", parameters={"danger": 101})


def test_relationship_self_pair_rejected():
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


def test_event_blank_text_rejected():
    with pytest.raises(ValidationError):
        Event(
            id="event_0001",
            turn=1,
            type="discovery",
            text="",
            visibility=Visibility.SCENE,
        )


def test_event_known_by_and_hidden_from_overlap_rejected():
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


def test_relationship_compound_key_accepted_for_diff_change():
    change = StateDiffChange(
        target="relationship",
        id="char_001__char_002",
        op="delta",
        path="trust",
        value=1,
        visibility=Visibility.CANON,
    )

    assert change.id == "char_001__char_002"


def test_invalid_relationship_compound_key_rejected_for_diff_change():
    with pytest.raises(ValidationError):
        StateDiffChange(
            target="relationship",
            id="char_001-char_002",
            op="delta",
            path="trust",
            value=1,
            visibility=Visibility.CANON,
        )


def test_state_store_roundtrip_preserves_content_and_bytes(tmp_path):
    state_dir = tmp_path / "state"
    StateStore.save(bundle(), state_dir)
    first = {path.name: path.read_bytes() for path in state_dir.glob("*.yaml")}

    loaded = StateStore.load(state_dir)
    StateStore.save(loaded, state_dir)

    assert first == {path.name: path.read_bytes() for path in state_dir.glob("*.yaml")}
    assert StateStore.load(state_dir).model_dump(mode="json") == loaded.model_dump(mode="json")


def test_encounter_schema_validation_and_store_roundtrip(tmp_path):
    encounter = EncounterEntry(
        id="encounter_001",
        text="霧の奥に人影が立つ",
        weight=2,
        visibility="reader",
        scene_id="scene_001",
        threat=EncounterThreatCondition(threat_id="threat_001", min_pressure=25),
    )
    state = bundle().model_copy(update={"encounters": [encounter]})

    StateStore.save(state, tmp_path / "state")
    loaded = StateStore.load(tmp_path / "state")

    assert loaded.encounters == [encounter]
    assert yaml.safe_load((tmp_path / "state" / "encounters.yaml").read_text()) == [
        encounter.model_dump(mode="json", by_alias=True)
    ]


def test_missing_encounters_file_loads_empty_for_backward_compatibility(tmp_path):
    StateStore.save(bundle(), tmp_path / "state")
    (tmp_path / "state" / "encounters.yaml").unlink()

    assert StateStore.load(tmp_path / "state").encounters == []


@pytest.mark.parametrize("weight", [0, -1, 1.5, True])
def test_encounter_weight_must_be_a_positive_integer(weight):
    with pytest.raises(ValidationError):
        EncounterEntry(id="encounter_001", text="遭遇", weight=weight, visibility="reader")


def test_encounter_threat_condition_requires_a_threshold():
    with pytest.raises(ValidationError):
        EncounterThreatCondition(threat_id="threat_001")


def test_schema_export_includes_encounter_models(tmp_path):
    export_state_schemas(tmp_path / "schemas")

    entry_schema = yaml.safe_load(
        (tmp_path / "schemas" / "EncounterEntry.schema.yaml").read_text(encoding="utf-8")
    )
    condition_schema = yaml.safe_load(
        (tmp_path / "schemas" / "EncounterThreatCondition.schema.yaml").read_text(encoding="utf-8")
    )
    assert entry_schema["required"] == ["id", "text", "weight", "visibility"]
    assert condition_schema["required"] == ["threat_id"]


def test_voice_profiles_roundtrip_and_missing_file_is_backward_compatible(tmp_path):
    state_dir = tmp_path / "state"
    value = bundle().model_copy(
        update={
            "voice_profiles": VoiceProfilesState(
                characters=[
                    CharacterVoiceProfile(character_id="char_001", quality="明るい", pace=1.1)
                ],
                narrator=VoiceProfile(quality="静かな語り", pace=0.9),
            )
        }
    )
    StateStore.save(value, state_dir)

    assert StateStore.load(state_dir).voice_profiles == value.voice_profiles
    (state_dir / "voice_profiles.yaml").unlink()
    assert StateStore.load(state_dir).voice_profiles == VoiceProfilesState()


def test_voice_profiles_reject_malformed_profile(tmp_path):
    state_dir = tmp_path / "state"
    StateStore.save(bundle(), state_dir)
    (state_dir / "voice_profiles.yaml").write_text(
        "characters:\n  - character_id: char_001\n    quality: ''\n",
        encoding="utf-8",
    )

    with pytest.raises(StateLoadError) as invalid:
        StateStore.load(state_dir)

    assert invalid.value.issues[0].file_path.name == "voice_profiles.yaml"


def test_voice_profiles_reject_duplicate_character_profiles():
    with pytest.raises(ValidationError, match="character voice profile ids must be unique"):
        VoiceProfilesState(
            characters=[
                CharacterVoiceProfile(character_id="char_001", quality="first"),
                CharacterVoiceProfile(character_id="char_001", quality="duplicate"),
            ]
        )


def test_voice_profile_schemas_are_exported(tmp_path):
    export_state_schemas(tmp_path)

    assert (tmp_path / "VoiceProfile.schema.yaml").exists()
    assert (tmp_path / "CharacterVoiceProfile.schema.yaml").exists()
    assert (tmp_path / "VoiceProfilesState.schema.yaml").exists()


def test_state_store_missing_variable_directory_loads_empty_collection(tmp_path):
    state_dir = tmp_path / "state"
    StateStore.save(bundle(), state_dir)
    (state_dir / "characters").rename(state_dir / "characters_gone")

    assert StateStore.load(state_dir).characters == []


def test_state_store_empty_fixed_collection_file_loads_empty_collection(tmp_path):
    state_dir = tmp_path / "state"
    StateStore.save(bundle(), state_dir)
    (state_dir / "gm_vault.yaml").write_text("[]\n", encoding="utf-8")

    assert StateStore.load(state_dir).gm_vault == []


def test_state_store_missing_required_file_raises_state_load_error(tmp_path):
    state_dir = tmp_path / "state"
    StateStore.save(bundle(), state_dir)
    (state_dir / "gm_vault.yaml").unlink()

    with pytest.raises(StateLoadError) as missing:
        StateStore.load(state_dir)

    assert missing.value.issues[0].file_path.name == "gm_vault.yaml"


def test_state_store_aggregates_validation_errors_across_files(tmp_path):
    state_dir = tmp_path / "state"
    StateStore.save(bundle(), state_dir)
    character_path = state_dir / "characters" / "char_001.yaml"
    character = yaml.safe_load(character_path.read_text(encoding="utf-8"))
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


def test_state_store_logs_unknown_field_warning(tmp_path, caplog):
    state_dir = tmp_path / "state"
    StateStore.save(bundle(), state_dir)
    character_path = state_dir / "characters" / "char_001.yaml"
    character = yaml.safe_load(character_path.read_text(encoding="utf-8"))
    character["favorite_color"] = "blue"
    character_path.write_text(yaml.safe_dump(character, sort_keys=False), encoding="utf-8")
    caplog.set_level(logging.WARNING)

    StateStore.load(state_dir)

    assert any("favorite_color" in record.message for record in caplog.records)


def test_memory_summary_interval_defaults_to_zero_and_rejects_negative():
    world = WorldState(id="world_001", name="x", summary="y", laws=[], parameters={})
    assert world.memory_summary_interval == 0
    with pytest.raises(ValidationError):
        WorldState(
            id="world_001",
            name="x",
            summary="y",
            laws=[],
            parameters={},
            memory_summary_interval=-1,
        )


def test_memory_summaries_round_trip_through_store(tmp_path):
    state_dir = tmp_path / "state"
    populated = bundle().model_copy(
        update={
            "memory_summaries": [MemorySummary(id="memory_0010", up_to_turn=10, text="要約その1")]
        }
    )
    StateStore.save(populated, state_dir)

    loaded = StateStore.load(state_dir)

    assert loaded.memory_summaries == populated.memory_summaries


def test_memory_summaries_yaml_missing_loads_empty_collection(tmp_path):
    state_dir = tmp_path / "state"
    StateStore.save(bundle(), state_dir)
    (state_dir / "memory_summaries.yaml").unlink()

    assert StateStore.load(state_dir).memory_summaries == []


def test_state_store_preserves_unknown_field_on_save(tmp_path):
    state_dir = tmp_path / "state"
    StateStore.save(bundle(), state_dir)
    character_path = state_dir / "characters" / "char_001.yaml"
    character = yaml.safe_load(character_path.read_text(encoding="utf-8"))
    character["favorite_color"] = "blue"
    character_path.write_text(yaml.safe_dump(character, sort_keys=False), encoding="utf-8")

    StateStore.save(StateStore.load(state_dir), state_dir)

    assert "favorite_color" in yaml.safe_load(character_path.read_text(encoding="utf-8"))


def test_partial_apply_only_applies_selected_changes():
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
        ],
    )

    partial = apply_state_diff(bundle(), diff, selected_change_indexes={0})

    assert partial.bundle.characters[0].status == "dead"
    assert partial.bundle.scenes[0].status == SceneStatus.ACTIVE


def test_state_diff_sets_character_status_to_dead():
    result = apply_state_diff(
        bundle(),
        StateDiff(
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
                )
            ],
        ),
    )

    assert result.bundle.characters[0].status == "dead"


def test_state_diff_sets_scene_status_to_ended():
    result = apply_state_diff(
        bundle(),
        StateDiff(
            id="diff_001",
            turn=1,
            changes=[
                StateDiffChange(
                    target="scene",
                    id="scene_001",
                    op="set",
                    path="status",
                    value="ended",
                    visibility=Visibility.CANON,
                )
            ],
        ),
    )

    assert result.bundle.scenes[0].status == "ended"


def test_relationship_delta_uses_directional_compound_key():
    result = apply_state_diff(
        bundle(),
        StateDiff(
            id="diff_001",
            turn=1,
            changes=[
                StateDiffChange(
                    target="relationship",
                    id="char_001__char_002",
                    op="delta",
                    path="trust",
                    value=10,
                    visibility=Visibility.CANON,
                )
            ],
        ),
    )

    assert result.bundle.relationships[0].trust == 20


def test_delta_clamps_to_100_and_reports_computed_value():
    result = apply_state_diff(
        bundle(),
        StateDiff(
            id="diff_001",
            turn=1,
            changes=[
                StateDiffChange(
                    target="character",
                    id="char_001",
                    op="delta",
                    path="emotions.fear",
                    value=20,
                    visibility=Visibility.CHARACTER,
                )
            ],
        ),
    )

    assert result.bundle.characters[0].emotions["fear"] == 100
    assert result.applied_changes[0].clamped
    assert result.applied_changes[0].computed_value == 115


def test_delta_clamps_to_0_and_reports_computed_value():
    result = apply_state_diff(
        bundle(),
        StateDiff(
            id="diff_001",
            turn=1,
            changes=[
                StateDiffChange(
                    target="relationship",
                    id="char_001__char_002",
                    op="delta",
                    path="trust",
                    value=-30,
                    visibility=Visibility.CANON,
                )
            ],
        ),
    )

    assert result.bundle.relationships[0].trust == 0
    assert result.applied_changes[0].clamped
    assert result.applied_changes[0].computed_value == -20


def test_inverse_of_unclamped_delta_is_negative_delta():
    result = apply_state_diff(
        bundle(),
        StateDiff(
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
        ),
    )

    inverse = result.inverse_diff.changes[0]
    assert inverse.op == "delta"
    assert inverse.value == -10


def test_inverse_of_clamped_delta_is_set_to_original_value():
    result = apply_state_diff(
        bundle(),
        StateDiff(
            id="diff_001",
            turn=1,
            changes=[
                StateDiffChange(
                    target="character",
                    id="char_001",
                    op="delta",
                    path="emotions.fear",
                    value=20,
                    visibility=Visibility.CHARACTER,
                )
            ],
        ),
    )

    inverse = result.inverse_diff.changes[0]
    assert inverse.op == "set"
    assert inverse.value == 95


def test_remove_by_id_inverse_carries_full_content():
    result = apply_state_diff(
        bundle(),
        StateDiff(
            id="diff_001",
            turn=1,
            changes=[
                StateDiffChange(
                    target="canon",
                    id="canon_001",
                    op="remove",
                    visibility=Visibility.CANON,
                )
            ],
        ),
    )

    inverse = result.inverse_diff.changes[0]
    assert inverse.op == "add"
    assert inverse.value["id"] == "canon_001"
    assert inverse.value["text"] == "The station exists."


def test_inverse_diff_restores_original_state():
    original = bundle()
    result = apply_state_diff(
        original,
        StateDiff(
            id="diff_001",
            turn=1,
            changes=[
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
        ),
    )

    restored = apply_state_diff(result.bundle, result.inverse_diff).bundle

    assert restored.model_dump(mode="json") == original.model_dump(mode="json")


def test_state_diff_reject_preserves_original_state():
    original = bundle()
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


def test_remove_absent_id_is_rejected():
    with pytest.raises(StateDiffError):
        apply_state_diff(
            bundle(),
            StateDiff(
                id="diff_001",
                turn=1,
                changes=[
                    StateDiffChange(
                        target="canon",
                        id="canon_099",
                        op="remove",
                        visibility=Visibility.CANON,
                    )
                ],
            ),
        )


def test_memory_summary_add_and_rollback():
    result = apply_state_diff(
        bundle(),
        StateDiff(
            id="diff_001",
            turn=10,
            changes=[
                StateDiffChange(
                    target="memory",
                    op="add",
                    path="",
                    value={"id": "memory_0010", "up_to_turn": 10, "text": "要約その1"},
                    visibility=Visibility.READER,
                )
            ],
        ),
    )

    assert len(result.bundle.memory_summaries) == 1
    assert result.bundle.memory_summaries[0].text == "要約その1"

    restored = apply_state_diff(result.bundle, result.inverse_diff).bundle
    assert restored.memory_summaries == []


def test_multi_turn_rollback_applies_inverse_diffs_in_descending_turn_order():
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


def test_timeline_add_change_appends_a_timeline_entry():
    result = apply_state_diff(
        bundle(),
        StateDiff(
            id="diff_001",
            turn=1,
            changes=[
                StateDiffChange(
                    target="timeline",
                    op="add",
                    path="",
                    value={"turn": 1, "event_ids": ["event_0001"]},
                    visibility=Visibility.CANON,
                )
            ],
        ),
    )

    assert result.bundle.timeline[0].turn == 1
    assert result.bundle.timeline[0].event_ids == ["event_0001"]


def test_timeline_add_change_inverse_removes_the_entry():
    original = bundle()
    result = apply_state_diff(
        original,
        StateDiff(
            id="diff_001",
            turn=1,
            changes=[
                StateDiffChange(
                    target="timeline",
                    op="add",
                    path="",
                    value={"turn": 1, "event_ids": ["event_0001"]},
                    visibility=Visibility.CANON,
                )
            ],
        ),
    )

    restored = apply_state_diff(result.bundle, result.inverse_diff).bundle

    assert restored.model_dump(mode="json") == original.model_dump(mode="json")


def test_schema_export_writes_world_state_schema(tmp_path):
    export_state_schemas(tmp_path / "schemas")

    assert (tmp_path / "schemas" / "WorldState.schema.yaml").exists()


def test_character_stats_and_skills_default_empty_for_legacy_data():
    character = CharacterState.model_validate({"id": "char_001", "name": "Aoi", "role": "lead"})

    assert character.stats == {}
    assert character.skills == {}


def test_schema_export_includes_character_stats_and_skills(tmp_path):
    export_state_schemas(tmp_path / "schemas")

    schema = yaml.safe_load(
        (tmp_path / "schemas" / "CharacterState.schema.yaml").read_text(encoding="utf-8")
    )
    for field in ("stats", "skills"):
        assert schema["properties"][field]["type"] == "object"
        assert schema["properties"][field]["additionalProperties"]["type"] == "integer"
        assert field not in schema.get("required", [])


def test_legacy_inventory_strings_upgrade_deterministically_and_round_trip():
    character = CharacterState.model_validate(
        {"id": "char_001", "name": "Aoi", "role": "lead", "inventory": ["古い鍵", "古い鍵"]}
    )

    assert [item.model_dump(mode="json") for item in character.inventory] == [
        {"id": "item_001", "name": "古い鍵", "qty": 1, "note": None},
        {"id": "item_002", "name": "古い鍵", "qty": 1, "note": None},
    ]
    assert CharacterState.model_validate_json(character.model_dump_json()) == character


def test_character_inventory_rejects_duplicate_structured_item_ids():
    with pytest.raises(ValidationError, match="inventory item ids must be unique"):
        CharacterState.model_validate(
            {
                "id": "char_001",
                "name": "Aoi",
                "role": "lead",
                "inventory": [
                    {"id": "item_001", "name": "古い鍵", "qty": 1},
                    {"id": "item_001", "name": "懐中電灯", "qty": 1},
                ],
            }
        )


def test_character_inventory_rejects_legacy_and_structured_id_collision():
    with pytest.raises(ValidationError, match="inventory item ids must be unique"):
        CharacterState.model_validate(
            {
                "id": "char_001",
                "name": "Aoi",
                "role": "lead",
                "inventory": [
                    "古い鍵",
                    {"id": "item_001", "name": "懐中電灯", "qty": 1},
                ],
            }
        )


@pytest.mark.parametrize("qty", [0, -1])
def test_inventory_item_rejects_non_positive_qty(qty):
    with pytest.raises(ValidationError, match="greater than 0"):
        InventoryItem(id="item_001", name="鍵", qty=qty)


def test_inventory_item_requires_id_name_and_qty():
    with pytest.raises(ValidationError):
        InventoryItem.model_validate({})


def test_inventory_item_rejects_blank_name():
    with pytest.raises(ValidationError, match="name must not be blank"):
        InventoryItem(id="item_001", name="   ", qty=1)


def test_state_store_loads_legacy_string_inventory(tmp_path):
    state_dir = tmp_path / "state"
    StateStore.save(bundle(), state_dir)
    character_path = state_dir / "characters" / "char_001.yaml"
    raw = yaml.safe_load(character_path.read_text(encoding="utf-8"))
    raw["inventory"] = ["懐中電灯", "古い鍵"]
    character_path.write_text(
        yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    loaded = StateStore.load(state_dir)

    assert [(item.id, item.name, item.qty) for item in loaded.characters[0].inventory] == [
        ("item_001", "懐中電灯", 1),
        ("item_002", "古い鍵", 1),
    ]


def test_schema_export_includes_inventory_item(tmp_path):
    export_state_schemas(tmp_path / "schemas")

    schema = yaml.safe_load(
        (tmp_path / "schemas" / "InventoryItem.schema.yaml").read_text(encoding="utf-8")
    )
    assert schema["required"] == ["id", "name", "qty"]


def test_quest_model_accepts_documented_statuses_and_rejects_bad_id():
    for status in ("open", "advanced", "resolved", "failed"):
        assert Quest(id="quest_001", title="出口を探す", status=status).status == status
    with pytest.raises(ValidationError, match="expected quest"):
        Quest(id="bad", title="出口を探す", status="open")


def test_quest_optional_load_and_save_round_trip(tmp_path):
    state_dir = tmp_path / "state"
    StateStore.save(bundle(), state_dir)
    (state_dir / "quests.yaml").unlink()
    assert StateStore.load(state_dir).quests == []

    loaded = StateStore.load(state_dir)
    loaded.quests = [
        Quest(
            id="quest_001",
            title="出口を探す",
            status="advanced",
            objectives=["案内図を確認する"],
        )
    ]
    StateStore.save(loaded, state_dir)
    assert StateStore.load(state_dir).quests == loaded.quests


def test_schema_export_includes_quest(tmp_path):
    export_state_schemas(tmp_path / "schemas")

    schema = yaml.safe_load(
        (tmp_path / "schemas" / "Quest.schema.yaml").read_text(encoding="utf-8")
    )
    assert schema["required"] == ["id", "title", "status"]


def test_visual_profiles_are_explicit_and_character_profile_is_optional():
    legacy = CharacterState.model_validate({"id": "char_001", "name": "Aoi", "role": "lead"})
    profiles = VisualProfilesState(
        backgrounds=[
            BackgroundVisualProfile(
                id="background_001",
                name="Platform",
                summary="A foggy station platform",
            )
        ],
        style_lock=StyleLockProfile(art_style="watercolor anime"),
    )

    assert legacy.visual_profile is None
    assert profiles.backgrounds[0].name == "Platform"
    assert profiles.style_lock is not None
    assert profiles.style_lock.art_style == "watercolor anime"


def test_state_store_missing_visual_profiles_file_loads_defaults(tmp_path):
    state_dir = tmp_path / "state"
    StateStore.save(bundle(), state_dir)
    (state_dir / "visual_profiles.yaml").unlink()

    loaded = StateStore.load(state_dir)

    assert loaded.visual_profiles == VisualProfilesState()


def test_state_store_round_trips_visual_profiles(tmp_path):
    state_dir = tmp_path / "state"
    populated = bundle().model_copy(
        update={
            "characters": [
                bundle()
                .characters[0]
                .model_copy(
                    update={"visual_profile": CharacterVisualProfile(summary="short black hair")}
                )
            ],
            "visual_profiles": VisualProfilesState(
                style_lock=StyleLockProfile(art_style="ink wash"),
            ),
        }
    )

    StateStore.save(populated, state_dir)
    loaded = StateStore.load(state_dir)

    assert loaded.characters[0].visual_profile is not None
    assert loaded.characters[0].visual_profile.summary == "short black hair"
    assert loaded.visual_profiles.style_lock is not None
    assert loaded.visual_profiles.style_lock.art_style == "ink wash"


def test_schema_export_includes_visual_profile_models(tmp_path):
    export_state_schemas(tmp_path / "schemas")

    for name in (
        "CharacterVisualProfile",
        "BackgroundVisualProfile",
        "StyleLockProfile",
        "VisualProfilesState",
    ):
        schema = yaml.safe_load(
            (tmp_path / "schemas" / f"{name}.schema.yaml").read_text(encoding="utf-8")
        )
        assert schema["title"] == name


# Issue 008: threat escalation tracks (ThreatTrack/ThreatStage on WorldState).


def test_world_threats_defaults_to_empty_list():
    assert WorldState(id="world_001", name="x", summary="y").threats == []


def test_threat_track_pressure_and_stages_default():
    threat = ThreatTrack(id="threat_001", name="Pursuer", pressure_per_turn="2d6")

    assert threat.pressure == 0
    assert threat.stages == []


def test_threat_stage_at_below_range_rejected():
    with pytest.raises(ValidationError):
        ThreatStage(at=0, text="closer", visibility=Visibility.SCENE)


def test_threat_stage_at_above_range_rejected():
    with pytest.raises(ValidationError):
        ThreatStage(at=101, text="closer", visibility=Visibility.SCENE)


def test_threat_stage_blank_text_rejected():
    with pytest.raises(ValidationError):
        ThreatStage(at=25, text="", visibility=Visibility.SCENE)


def _threat_bundle() -> WorldStateBundle:
    return WorldStateBundle(
        world=WorldState(
            id="world_001",
            name="Mist Station",
            summary="A quiet station.",
            threats=[
                ThreatTrack(
                    id="threat_001",
                    name="Pursuer",
                    pressure=10,
                    pressure_per_turn="2d6",
                    stages=[ThreatStage(at=25, text="closer", visibility=Visibility.SCENE)],
                ),
                ThreatTrack(id="threat_002", name="Other", pressure=5, pressure_per_turn="1d6"),
            ],
        )
    )


def test_world_threat_pressure_set_diff_updates_the_matching_threat_only():
    result = apply_state_diff(
        _threat_bundle(),
        StateDiff(
            id="diff_001",
            turn=1,
            changes=[
                StateDiffChange(
                    target="world",
                    op="set",
                    path="threats.threat_001.pressure",
                    value=40,
                    visibility=Visibility.GM_ONLY,
                )
            ],
        ),
    )

    assert result.bundle.world.threats[0].pressure == 40
    assert result.bundle.world.threats[1].pressure == 5


def test_world_threat_pressure_set_diff_rollback_restores_original_pressure():
    original = _threat_bundle()
    result = apply_state_diff(
        original,
        StateDiff(
            id="diff_001",
            turn=1,
            changes=[
                StateDiffChange(
                    target="world",
                    op="set",
                    path="threats.threat_001.pressure",
                    value=40,
                    visibility=Visibility.GM_ONLY,
                )
            ],
        ),
    )

    restored = apply_state_diff(result.bundle, result.inverse_diff).bundle

    assert restored.model_dump(mode="json") == original.model_dump(mode="json")


def test_world_threat_pressure_set_diff_unknown_threat_id_raises():
    with pytest.raises(StateDiffError):
        apply_state_diff(
            _threat_bundle(),
            StateDiff(
                id="diff_001",
                turn=1,
                changes=[
                    StateDiffChange(
                        target="world",
                        op="set",
                        path="threats.threat_099.pressure",
                        value=40,
                        visibility=Visibility.GM_ONLY,
                    )
                ],
            ),
        )


def test_faction_delta_diff_updates_resource_and_relation_keys_and_rolls_back():
    original = WorldStateBundle(
        world=WorldState(id="world_001", name="World", summary=""),
        factions=[
            FactionState(
                id="faction_001",
                name="Mist Keepers",
                public_face="old station committee",
                resources={"influence": 45},
                relations={"char_001": 40},
            )
        ],
    )

    result = apply_state_diff(
        original,
        StateDiff(
            id="diff_001",
            turn=1,
            changes=[
                StateDiffChange(
                    target="faction",
                    id="faction_001",
                    op="delta",
                    path="resources.influence",
                    value=-5,
                    visibility=Visibility.GM_ONLY,
                ),
                StateDiffChange(
                    target="faction",
                    id="faction_001",
                    op="delta",
                    path="relations.char_001",
                    value=10,
                    visibility=Visibility.GM_ONLY,
                ),
            ],
        ),
    )

    assert result.bundle.factions[0].resources["influence"] == 40
    assert result.bundle.factions[0].relations["char_001"] == 50

    restored = apply_state_diff(result.bundle, result.inverse_diff).bundle
    assert restored.model_dump(mode="json") == original.model_dump(mode="json")


# Issue 012: speech register profile (first_person / forbidden_terms on CharacterState).


def test_speech_profile_defaults_to_no_first_person_and_empty_forbidden_terms():
    profile = SpeechProfile()

    assert profile.first_person is None
    assert profile.forbidden_terms == []


def test_character_state_defaults_to_an_empty_speech_profile():
    character = CharacterState(id="char_001", name="Aoi", role="lead")

    assert character.speech == SpeechProfile()


def test_character_state_accepts_a_speech_profile():
    character = CharacterState(
        id="char_001",
        name="Aoi",
        role="lead",
        speech=SpeechProfile(first_person="私", forbidden_terms=["僕", "俺"]),
    )

    assert character.speech.first_person == "私"
    assert character.speech.forbidden_terms == ["僕", "俺"]
