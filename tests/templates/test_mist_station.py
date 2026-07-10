"""Sample world "霧の駅" (mist_station template): schema validity + design.md D3's
requirement that every gm_vault hidden truth is connected to a character's
knowledge/secrets/private_mind, so the leak checker has real detection targets (proposal.md)."""

from living_narrative.state.store import StateStore
from living_narrative.workspace.init import create_project

# design.md D3: each gm_vault entry's connection point, expressed as keyword(s) that must
# appear together in at least one character's knowledge.believes/secrets/private_mind.
_VAULT_KEYWORD_LINKS = {
    "gm_vault_001": ["封印", "施設"],  # 封印施設の存在 -> カイの believes
    "gm_vault_002": ["幼い頃", "記憶"],  # カイの部分的知識 -> カイの secrets
    "gm_vault_003": ["末裔"],  # ミラの正体 -> ミラの secrets
}


def _character_texts(character):
    return [
        *character.knowledge.knows,
        *character.knowledge.believes,
        *character.secrets,
        *character.private_mind,
    ]


def test_mist_station_state_is_schema_valid(tmp_path):
    output = tmp_path / "mist_station"
    create_project(output, title="霧の駅", template="mist_station")

    bundle = StateStore.load(output / "workspace" / "state")

    assert bundle.world.id == "world_001"
    assert len(bundle.characters) == 4
    assert len(bundle.factions) == 1
    assert len(bundle.gm_vault) == 3
    assert len(bundle.scenes) == 2
    rina = next(character for character in bundle.characters if character.id == "char_001")
    assert rina.visual_profile is not None
    assert rina.visual_profile.hair == "艶のある黒髪のボブ"
    assert bundle.visual_profiles.backgrounds[0].id == "background_001"
    assert bundle.visual_profiles.style_lock is not None
    assert bundle.visual_profiles.style_lock.art_style == "静謐な現代日本ミステリーのアニメ背景美術"


def test_every_gm_vault_entry_is_linked_to_a_character(tmp_path):
    output = tmp_path / "mist_station"
    create_project(output, title="霧の駅", template="mist_station")
    bundle = StateStore.load(output / "workspace" / "state")

    vault_ids = {entry.id for entry in bundle.gm_vault}
    assert vault_ids == set(_VAULT_KEYWORD_LINKS)

    all_character_text = [
        text for character in bundle.characters for text in _character_texts(character)
    ]
    for vault_id, keywords in _VAULT_KEYWORD_LINKS.items():
        assert any(all(keyword in text for keyword in keywords) for text in all_character_text), (
            f"{vault_id} has no character text containing all of {keywords}"
        )


def test_scene_001_hidden_facts_reference_the_starting_characters(tmp_path):
    output = tmp_path / "mist_station"
    create_project(output, title="霧の駅", template="mist_station")
    bundle = StateStore.load(output / "workspace" / "state")

    scene = next(scene for scene in bundle.scenes if scene.id == "scene_001")
    assert scene.active_characters == ["char_001", "char_002"]
    assert scene.hidden_facts
    known_by_ids = {char_id for fact in scene.hidden_facts for char_id in fact.known_by}
    assert known_by_ids <= {c.id for c in bundle.characters}


def test_scene_002_is_pending_with_empty_active_characters_for_carry_over(tmp_path):
    """Issue 009: scene_002 is template-defined but not yet started; its cast is carried over
    from scene_001 by the state manager's scene_transition handling, not pre-filled here.
    Also exercises the store loader with multiple scene files (state/scenes/*.yaml)."""
    output = tmp_path / "mist_station"
    create_project(output, title="霧の駅", template="mist_station")
    bundle = StateStore.load(output / "workspace" / "state")

    scene = next(scene for scene in bundle.scenes if scene.id == "scene_002")
    assert scene.status == "pending"
    assert scene.active_characters == []
    known_by_ids = {char_id for fact in scene.hidden_facts for char_id in fact.known_by}
    assert known_by_ids <= {c.id for c in bundle.characters}


def test_world_stage_100_carries_a_scene_transition_to_scene_002(tmp_path):
    output = tmp_path / "mist_station"
    create_project(output, title="霧の駅", template="mist_station")
    bundle = StateStore.load(output / "workspace" / "state")

    threat = next(t for t in bundle.world.threats if t.id == "threat_001")
    stage_100 = next(stage for stage in threat.stages if stage.at == 100)
    assert stage_100.effects["scene_transition"] == {"end": "scene_001", "start": "scene_002"}


def test_relationships_are_directed_pairs_between_valid_characters(tmp_path):
    output = tmp_path / "mist_station"
    create_project(output, title="霧の駅", template="mist_station")
    bundle = StateStore.load(output / "workspace" / "state")

    character_ids = {c.id for c in bundle.characters}
    for relationship in bundle.relationships:
        assert relationship.from_ in character_ids
        assert relationship.to in character_ids
        assert relationship.from_ != relationship.to


def test_world_parameters_are_within_0_to_100(tmp_path):
    output = tmp_path / "mist_station"
    create_project(output, title="霧の駅", template="mist_station")
    bundle = StateStore.load(output / "workspace" / "state")

    for value in bundle.world.parameters.values():
        assert 0 <= value <= 100


def test_world_has_a_nonzero_emotion_decay_rate(tmp_path):
    """Issue 010: mist_station opts into engine-side emotion homeostasis."""
    output = tmp_path / "mist_station"
    create_project(output, title="霧の駅", template="mist_station")
    bundle = StateStore.load(output / "workspace" / "state")

    assert bundle.world.emotion_decay_per_turn == 5


def test_world_has_pacing_config(tmp_path):
    """Issue 011: mist_station opts into stall detection/response."""
    output = tmp_path / "mist_station"
    create_project(output, title="霧の駅", template="mist_station")
    bundle = StateStore.load(output / "workspace" / "state")

    assert bundle.world.pacing.stall_window == 3
    assert bundle.world.pacing.pressure_boost == 4


def test_every_character_has_a_speech_profile_with_a_first_person_pronoun(tmp_path):
    """Issue 012: mist_station defines each character's first-person pronoun and the
    other pronouns forbidden to them, so the speech-register checker has real targets."""
    output = tmp_path / "mist_station"
    create_project(output, title="霧の駅", template="mist_station")
    bundle = StateStore.load(output / "workspace" / "state")

    expected = {
        "char_001": ("私", {"僕", "俺"}),
        "char_002": ("俺", {"僕"}),
        "char_003": ("私", {"僕", "俺"}),
        "char_004": ("俺", {"僕"}),
    }
    for character in bundle.characters:
        first_person, forbidden = expected[character.id]
        assert character.speech.first_person == first_person
        assert set(character.speech.forbidden_terms) == forbidden
        assert character.speech.first_person not in character.speech.forbidden_terms


def test_every_character_emotions_baseline_matches_its_initial_emotions(tmp_path):
    """Issue 010: each character's baseline is set to its starting emotion values so decay
    is a no-op until the LLM actually moves emotions away from them."""
    output = tmp_path / "mist_station"
    create_project(output, title="霧の駅", template="mist_station")
    bundle = StateStore.load(output / "workspace" / "state")

    for character in bundle.characters:
        assert character.emotions_baseline == character.emotions


def test_every_character_has_non_empty_stats_and_skills_after_template_init(tmp_path):
    output = tmp_path / "mist_station"
    create_project(output, title="霧の駅", template="mist_station")

    bundle = StateStore.load(output / "workspace" / "state")

    assert {character.id for character in bundle.characters} == {
        "char_001",
        "char_002",
        "char_003",
        "char_004",
    }
    for character in bundle.characters:
        assert character.stats
        assert character.skills
        assert all(isinstance(value, int) for value in character.stats.values())
        assert all(isinstance(value, int) for value in character.skills.values())
