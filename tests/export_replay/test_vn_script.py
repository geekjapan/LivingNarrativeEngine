import json

import pytest
from pydantic import ValidationError

from living_narrative.export_replay.vn_script import (
    PROMPT_TEMPLATE_NAME,
    VNCommand,
    VNLineOutput,
    VNScript,
    VNScriptError,
    VNTurnOutput,
    build_vn_script,
    generate_vn_script,
    load_reader_narrations,
    render_vn_script_markdown,
)
from living_narrative.llm.errors import StructuredOutputError


class FakeGateway:
    def __init__(self, output=None, error=None):
        self.output = output
        self.error = error
        self.calls = []

    def complete(self, binding_key, messages, response_schema, prompt_template_name):
        self.calls.append((binding_key, messages, response_schema, prompt_template_name))
        if self.error:
            raise self.error
        return self.output


def test_vn_script_extracts_all_supported_commands(tmp_path, write_turn_dir):
    runs = tmp_path / "runs"
    write_turn_dir(
        runs,
        1,
        narration="""# BACKGROUND: 夜の駅
# BGM: 静かなピアノ
# SPRITE: char_001
char_001: 「誰かいる？」
# SFX: 電車のブレーキ音
霧がホームを覆う。""",
    )

    script = build_vn_script(load_reader_narrations(runs))

    assert [command.kind for command in script.turns[0].commands] == [
        "background",
        "bgm",
        "sprite",
        "dialogue",
        "sfx",
        "narration",
    ]
    assert script.turns[0].commands[2].character_id == "char_001"
    assert "**char_001**" in render_vn_script_markdown(script)


def test_vn_script_reads_only_narration_and_adoption_metadata(
    tmp_path, write_turn_dir, monkeypatch
):
    runs = tmp_path / "runs"
    turn_dir = write_turn_dir(runs, 1, narration="読者に見える本文")
    (turn_dir / "events.yaml").write_text(
        "- visibility: gm_only\n  text: 絶対に出してはいけない秘密\n", encoding="utf-8"
    )
    (turn_dir / "state_diff.yaml").write_text(
        "gm_vault: 絶対に出してはいけない秘密\n", encoding="utf-8"
    )

    original_read_text = type(turn_dir).read_text
    read_names = []

    def recording_read_text(path, *args, **kwargs):
        read_names.append(path.name)
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(type(turn_dir), "read_text", recording_read_text)

    script = build_vn_script(load_reader_narrations(runs))
    combined = render_vn_script_markdown(script)

    assert "読者に見える本文" in combined
    assert "絶対に出してはいけない秘密" not in combined
    assert set(read_names) <= {"narration.md", "meta.yaml", "review.yaml"}
    assert "events.yaml" not in read_names
    assert "state_diff.yaml" not in read_names


def test_vn_script_skips_non_reader_narration(tmp_path, write_turn_dir):
    runs = tmp_path / "runs"
    write_turn_dir(runs, 1, narration="採用本文")
    private = write_turn_dir(runs, 2, narration="GM本文")
    narration_path = private / "narration.md"
    narration_path.write_text(
        narration_path.read_text(encoding="utf-8").replace(
            "visibility: reader", "visibility: gm_only"
        ),
        encoding="utf-8",
    )

    script = build_vn_script(load_reader_narrations(runs))

    assert [turn.turn for turn in script.turns] == [1]


def test_vn_script_skips_reject_all_and_non_applied_turns(tmp_path, write_turn_dir):
    runs = tmp_path / "runs"
    write_turn_dir(runs, 1, narration="採用本文")
    write_turn_dir(runs, 2, narration="却下本文", review_decision="reject_all")
    write_turn_dir(runs, 3, narration="レビュー停止本文", status="stopped_for_review")
    write_turn_dir(runs, 4, narration="失敗本文", status="failed")

    script = build_vn_script(load_reader_narrations(runs))

    assert [turn.turn for turn in script.turns] == [1]


def test_llm_vn_script_uses_safe_input_and_records_reference_warnings():
    gateway = FakeGateway(
        VNTurnOutput(
            lines=[
                VNLineOutput(
                    type="dialogue",
                    speaker="char_999",
                    text="誰かいる？",
                    sprite="char_002",
                    background="background_999",
                ),
                VNLineOutput(
                    type="dialogue",
                    speaker="char_001",
                    text="ここにいる",
                    sprite="char_001",
                    background="background_001",
                ),
                VNLineOutput(type="direction", text="暗転する"),
            ]
        )
    )

    script = generate_vn_script(
        [(1, "読者に見える通常novel本文。秘密語は入力に存在しない。")],
        gateway,
        allowed_character_ids={"char_001"},
        allowed_background_ids={"background_001"},
        profile="vn-editor",
    )

    binding, messages, schema, template = gateway.calls[0]
    payload = json.loads(messages[1]["content"])
    assert binding == "vn-editor"
    assert schema is VNTurnOutput
    assert template == PROMPT_TEMPLATE_NAME
    assert payload == {
        "turn": 1,
        "narration": "読者に見える通常novel本文。秘密語は入力に存在しない。",
        "allowed_character_ids": ["char_001"],
        "allowed_background_ids": ["background_001"],
    }
    assert "gm_vault" not in messages[1]["content"]
    assert "private_mind" not in messages[1]["content"]
    commands = script.turns[0].commands
    assert commands[0] == VNCommand(kind="narration", text="誰かいる？")
    assert commands[1].kind == "background"
    assert commands[2].kind == "sprite"
    assert commands[3].kind == "dialogue"
    assert commands[4] == VNCommand(kind="direction", text="暗転する")
    assert len(script.warnings) == 3
    assert "unknown speaker" in script.warnings[2]
    assert '"warnings"' in script.model_dump_json()


def test_vn_models_reject_incomplete_commands_and_non_v1_format():
    with pytest.raises(ValidationError):
        VNCommand(kind="dialogue", text="台詞")
    with pytest.raises(ValidationError):
        VNCommand(kind="sprite", character_id="char_001", text="余計")
    with pytest.raises(ValidationError):
        VNScript(format="v2")


def test_llm_vn_script_wraps_structured_output_exhaustion():
    error = StructuredOutputError(
        provider_name="mock", model="m", schema_name="VNTurnOutput", last_error="invalid"
    )

    with pytest.raises(VNScriptError, match="turn 1"):
        generate_vn_script(
            [(1, "本文")],
            FakeGateway(error=error),
            allowed_character_ids=set(),
            allowed_background_ids=set(),
        )
