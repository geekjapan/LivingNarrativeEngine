import pytest
import yaml
from pydantic import ValidationError

from living_narrative.export_replay.tts_script import (
    RIGHTS_NOTICE,
    TTSMetadata,
    TTSScript,
    TTSSegment,
    TTSVoiceProfile,
    build_tts_script,
    render_tts_script_markdown,
    write_tts_script_exports,
)
from living_narrative.export_replay.vn_script import VNCommand, VNScript, VNTurn
from living_narrative.state.models import (
    CharacterState,
    CharacterVoiceProfile,
    VoiceProfile,
    VoiceProfilesState,
    WorldState,
    WorldStateBundle,
)


def _state() -> WorldStateBundle:
    return WorldStateBundle(
        world=WorldState(id="world_001", name="駅", summary="霧の駅"),
        characters=[CharacterState(id="char_001", name="リナ", role="主人公")],
        voice_profiles=VoiceProfilesState(
            characters=[CharacterVoiceProfile(character_id="char_001", quality="明るい", pace=1.1)],
            narrator=VoiceProfile(quality="静かな語り", pace=0.9),
        ),
    )


def test_tts_script_keeps_only_spoken_text_in_source_order():
    script = VNScript(
        warnings=["GMに見せない内部warning"],
        turns=[
            VNTurn(
                turn=2,
                commands=[
                    VNCommand(kind="background", text="秘密の背景"),
                    VNCommand(kind="direction", text="暗転"),
                    VNCommand(kind="sprite", character_id="char_001"),
                    VNCommand(kind="dialogue", character_id="char_001", text="行こう"),
                    VNCommand(kind="bgm", text="不穏な曲"),
                    VNCommand(kind="sfx", text="足音"),
                    VNCommand(kind="narration", text="霧が晴れた。"),
                ],
            )
        ],
    )

    result = build_tts_script(script, _state())

    assert [(item.sequence, item.kind, item.text) for item in result.segments] == [
        (1, "dialogue", "行こう"),
        (2, "narration", "霧が晴れた。"),
    ]
    dumped = result.model_dump_json()
    for forbidden in ["秘密の背景", "暗転", "不穏な曲", "足音", "内部warning"]:
        assert forbidden not in dumped


def test_tts_script_warns_and_omits_unknown_or_unprofiled_speakers():
    script = VNScript(
        turns=[
            VNTurn(
                turn=1,
                commands=[
                    VNCommand(kind="dialogue", character_id="char_999", text="未知"),
                    VNCommand(kind="dialogue", character_id="char_002", text="profileなし"),
                ],
            )
        ]
    )
    original = _state()
    state = original.model_copy(
        update={
            "characters": [
                *original.characters,
                CharacterState(id="char_002", name="カイ", role="友人"),
            ]
        }
    )

    result = build_tts_script(script, state)

    assert result.segments == []
    assert "unknown speaker" in result.warnings[0]
    assert "voice profile missing" in result.warnings[1]


def test_narration_uses_explicit_default_only_when_narrator_is_absent():
    original = _state()
    state = original.model_copy(
        update={"voice_profiles": VoiceProfilesState(default=VoiceProfile(quality="既定"))}
    )
    script = VNScript(turns=[VNTurn(turn=1, commands=[VNCommand(kind="narration", text="本文")])])

    result = build_tts_script(script, state)

    assert result.segments[0].voice == "default"
    assert result.segments[0].profile.quality == "既定"


def test_narration_without_narrator_or_default_warns_and_is_omitted():
    original = _state()
    state = original.model_copy(update={"voice_profiles": VoiceProfilesState()})
    script = VNScript(turns=[VNTurn(turn=1, commands=[VNCommand(kind="narration", text="本文")])])

    result = build_tts_script(script, state)

    assert result.segments == []
    assert "narrator/default voice profile missing" in result.warnings[0]


def test_tts_exports_are_atomic_and_include_rights_notice(tmp_path):
    result = build_tts_script(
        VNScript(turns=[VNTurn(turn=1, commands=[VNCommand(kind="narration", text="本文")])]),
        _state(),
    )

    yaml_path, markdown_path = write_tts_script_exports(tmp_path, result)

    assert (
        yaml.safe_load(yaml_path.read_text(encoding="utf-8"))["metadata"]["rights_notice"]
        == RIGHTS_NOTICE
    )
    assert RIGHTS_NOTICE in render_tts_script_markdown(result)
    assert RIGHTS_NOTICE in markdown_path.read_text(encoding="utf-8")
    assert not list(tmp_path.glob("*.tmp"))


def test_tts_markdown_includes_all_voice_profile_directions():
    state = _state()
    script = VNScript(
        turns=[
            VNTurn(
                turn=1,
                commands=[VNCommand(kind="dialogue", character_id="char_001", text="本文")],
            )
        ]
    )

    markdown = render_tts_script_markdown(build_tts_script(script, state))

    assert "- quality: 明るい" in markdown
    assert "- pace: 1.1" in markdown
    assert "- pitch:" not in markdown

    profiled_state = state.model_copy(
        update={
            "voice_profiles": VoiceProfilesState(
                characters=[
                    CharacterVoiceProfile(
                        character_id="char_001",
                        quality="明るい",
                        pace=1.1,
                        pitch="高め",
                        notes=["語尾を明瞭に"],
                    )
                ]
            )
        }
    )
    markdown = render_tts_script_markdown(build_tts_script(script, profiled_state))
    assert "- pitch: 高め" in markdown
    assert "- note: 語尾を明瞭に" in markdown


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"speaker": None}, "dialogue requires speaker"),
        ({"voice": "narrator"}, "dialogue requires character voice"),
        (
            {"kind": "narration", "speaker": "char_001", "voice": "narrator"},
            "narration does not accept speaker",
        ),
        (
            {"kind": "narration", "speaker": None, "voice": "character"},
            "narration requires narrator or default voice",
        ),
    ],
)
def test_tts_segment_rejects_contradictory_speaker_voice_combinations(changes, message):
    values = {
        "turn": 1,
        "sequence": 1,
        "kind": "dialogue",
        "text": "本文",
        "speaker": "char_001",
        "voice": "character",
        "profile": TTSVoiceProfile(quality="明るい"),
        **changes,
    }

    with pytest.raises(ValidationError, match=message):
        TTSSegment.model_validate(values)


def test_tts_artifact_models_forbid_extras_blank_text_and_invalid_rights_metadata():
    segment = {
        "turn": 1,
        "sequence": 1,
        "kind": "narration",
        "text": "本文",
        "speaker": None,
        "voice": "narrator",
        "profile": TTSVoiceProfile(quality="静か"),
    }
    metadata = {"rights_notice": RIGHTS_NOTICE}

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        TTSSegment.model_validate({**segment, "internal": "secret"})
    with pytest.raises(ValidationError, match="spoken text must not be blank"):
        TTSSegment.model_validate({**segment, "text": "  \n"})
    with pytest.raises(ValidationError, match="speaker must not be blank"):
        TTSSegment.model_validate(
            {**segment, "kind": "dialogue", "speaker": "  ", "voice": "character"}
        )
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        TTSScript.model_validate({"metadata": metadata, "unknown": True})
    with pytest.raises(ValidationError, match="rights_notice"):
        TTSScript.model_validate({"metadata": {}})
    with pytest.raises(ValidationError, match="Input should be"):
        TTSMetadata.model_validate({"rights_notice": "replaced"})
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        TTSVoiceProfile.model_validate({"quality": "静か", "unexpected": True})
    with pytest.raises(ValidationError, match="valid number"):
        TTSVoiceProfile.model_validate({"quality": "静か", "pace": "1.2"})


@pytest.mark.parametrize("turn", [0, -1])
def test_tts_segment_rejects_non_positive_turn_numbers(turn):
    with pytest.raises(ValidationError, match="greater than or equal to 1"):
        TTSSegment(
            turn=turn,
            sequence=1,
            kind="narration",
            text="本文",
            speaker=None,
            voice="narrator",
            profile=TTSVoiceProfile(quality="静か"),
        )


def test_tts_rights_metadata_cannot_be_mutated_or_replaced_with_invalid_data():
    script = build_tts_script(
        VNScript(turns=[VNTurn(turn=1, commands=[VNCommand(kind="narration", text="本文")])]),
        _state(),
    )

    with pytest.raises(ValidationError, match="Instance is frozen"):
        script.metadata.rights_notice = "replaced"
    with pytest.raises(ValidationError, match="rights_notice"):
        script.metadata = {"rights_notice": "replaced"}

    assert script.metadata.rights_notice == RIGHTS_NOTICE


def test_tts_atomic_write_cleans_unique_temporary_file_when_replace_fails(tmp_path, monkeypatch):
    result = build_tts_script(
        VNScript(turns=[VNTurn(turn=1, commands=[VNCommand(kind="narration", text="本文")])]),
        _state(),
    )
    replace_sources = []

    def fail_replace(source, destination):
        replace_sources.append(source)
        raise OSError("replace failed")

    monkeypatch.setattr("living_narrative.export_replay.tts_script.os.replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        write_tts_script_exports(tmp_path, result)

    assert len(replace_sources) == 1
    assert replace_sources[0].name.startswith(".tts_script.yaml.")
    assert not replace_sources[0].exists()
    assert not list(tmp_path.glob(".*.tmp"))
