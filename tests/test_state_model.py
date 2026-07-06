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
    SpeechProfile,
    ThreatStage,
    ThreatTrack,
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
