"""宇宙站サンプル「軌道站エコー」の構造・参照・秘密漏洩検査。"""

from living_narrative.safety.leak_check import leak_checker
from living_narrative.state.diff import StateDiff
from living_narrative.state.store import StateStore
from living_narrative.workspace.init import create_project


class _LeakContext:
    def __init__(self, bundle):
        self.bundle = bundle


def _load_template(tmp_path):
    output = tmp_path / "orbital_echo"
    create_project(output, title="軌道站エコー", template="orbital_echo")
    return output, StateStore.load(output / "workspace" / "state")


def test_orbital_echo_is_schema_valid_and_has_required_content(tmp_path):
    output, bundle = _load_template(tmp_path)

    assert bundle.world.name == "軌道站エコー"
    assert len(bundle.characters) == 3
    assert len(bundle.gm_vault) == 3
    assert len(bundle.factions) == 2
    assert len(bundle.world.threats) == 1
    assert len(bundle.visual_profiles.backgrounds) == 2
    assert bundle.visual_profiles.style_lock is not None
    assert all(character.visual_profile is not None for character in bundle.characters)

    assert len(bundle.quests) == 1
    quest = bundle.quests[0]
    assert quest.id == "quest_001"
    assert quest.title == "十八時間後の救難音声"
    assert quest.status == "open"
    assert quest.objectives == [
        "酸素循環器を復旧する",
        "救難音声の送信源を特定する",
        "閉鎖区画を開放するか決断する",
    ]
    assert quest.related_event_ids == []


def test_orbital_echo_references_are_consistent(tmp_path):
    _, bundle = _load_template(tmp_path)
    character_ids = {character.id for character in bundle.characters}
    scene_ids = {scene.id for scene in bundle.scenes}

    for scene in bundle.scenes:
        assert set(scene.active_characters) <= character_ids
        for fact in scene.hidden_facts:
            assert set(fact.known_by) <= character_ids
    for relationship in bundle.relationships:
        assert relationship.from_ in character_ids
        assert relationship.to in character_ids
        assert relationship.from_ != relationship.to
    stage_100 = next(stage for stage in bundle.world.threats[0].stages if stage.at == 100)
    transition = stage_100.effects["scene_transition"]
    assert {transition["end"], transition["start"]} <= scene_ids


def test_orbital_echo_has_explicit_encounter_and_pacing_contracts(tmp_path):
    _, bundle = _load_template(tmp_path)

    assert all(scene.pacing_terminal or scene.fallback_affordance_ids for scene in bundle.scenes)
    for scene in bundle.scenes:
        affordances = {affordance.id: affordance for affordance in scene.affordances}
        for affordance_id in scene.fallback_affordance_ids:
            assert affordances[affordance_id].fallback_only
    assert {encounter.recurrence for encounter in bundle.encounters} == {"once", "cooldown"}
    assert all(
        encounter.cooldown_turns == 3
        for encounter in bundle.encounters
        if encounter.recurrence == "cooldown"
    )


def test_orbital_echo_secrets_are_meaningful_leak_targets(tmp_path):
    _, bundle = _load_template(tmp_path)
    context = _LeakContext(bundle)
    empty_diff = StateDiff(id="diff_0001", turn=1)

    secret = next(
        character for character in bundle.characters if character.id == "char_002"
    ).secrets[0]
    hidden_fact = next(scene for scene in bundle.scenes if scene.id == "scene_002").hidden_facts[0]

    assert leak_checker(context, secret, [], empty_diff)[0].severity == "error"
    finding = leak_checker(context, hidden_fact.text, [], empty_diff)[0]
    assert finding.severity == "error"
    assert finding.related_ids == ["fact_003"]


def test_public_clues_do_not_contain_gm_truth_but_truth_is_detected(tmp_path):
    _, bundle = _load_template(tmp_path)
    context = _LeakContext(bundle)
    empty_diff = StateDiff(id="diff_0001", turn=1)
    public_text = "\n".join(
        [
            *(scene.summary for scene in bundle.scenes),
            *(fact for scene in bundle.scenes for fact in scene.reader_visible_facts),
            *(quest.title for quest in bundle.quests),
            *(objective for quest in bundle.quests for objective in quest.objectives),
        ]
    )
    synthetic_truth = next(entry.text for entry in bundle.gm_vault if entry.id == "gm_vault_003")

    assert leak_checker(context, public_text, [], empty_diff) == []
    finding = leak_checker(context, synthetic_truth, [], empty_diff)[0]
    assert finding.severity == "error"
    assert "fact_001" in finding.related_ids or "char_002" in finding.related_ids


def test_every_gm_truth_has_a_character_or_scene_connection(tmp_path):
    _, bundle = _load_template(tmp_path)
    connected_text = "\n".join(
        [
            *(text for character in bundle.characters for text in character.secrets),
            *(text for character in bundle.characters for text in character.private_mind),
            *(fact.text for scene in bundle.scenes for fact in scene.hidden_facts),
        ]
    )
    keywords = {
        "gm_vault_001": ("装置", "誘導"),
        "gm_vault_002": ("地球管制", "証拠"),
        "gm_vault_003": ("声紋", "合成", "未来のレン本人"),
    }

    assert {entry.id for entry in bundle.gm_vault} == set(keywords)
    for required in keywords.values():
        assert all(keyword in connected_text for keyword in required)
