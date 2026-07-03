import logging

from living_narrative.session.autonomy import normalize_mode_level, should_stop_for_level
from living_narrative.state.models import AutonomyLevel, UserMode


def test_watcher_manual_normalizes_to_watch(caplog):
    caplog.set_level(logging.WARNING)

    result = normalize_mode_level("watcher", "manual")

    assert result.autonomy_level == AutonomyLevel.WATCH
    assert result.normalized is True
    assert "normalized watcher+manual" in caplog.text


def test_player_character_auto_normalizes_to_assist(caplog):
    caplog.set_level(logging.WARNING)

    result = normalize_mode_level("player_character", "auto")

    assert result.autonomy_level == AutonomyLevel.ASSIST
    assert result.normalized is True
    assert "player_character+auto" in caplog.text


def test_valid_combination_is_not_normalized():
    result = normalize_mode_level("assistant_gm", "assist")

    assert result.user_mode == UserMode.ASSISTANT_GM
    assert result.autonomy_level == AutonomyLevel.ASSIST
    assert result.normalized is False


def test_stop_condition_stops_all_limited_levels():
    assert should_stop_for_level("watch", "stop_condition") is True
    assert should_stop_for_level("god", "stop_condition") is True
    assert should_stop_for_level("god", "major_secret_reveal") is False
