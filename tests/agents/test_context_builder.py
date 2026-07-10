from living_narrative.agents import build_character_context, build_world_context
from living_narrative.state.models import (
    CharacterState,
    Event,
    GmVaultEntry,
    HiddenFact,
    MemorySummary,
    Quest,
    RelationshipState,
    SceneState,
    SceneStatus,
    SpeechProfile,
    Visibility,
    WorldState,
    WorldStateBundle,
)


def _bundle() -> WorldStateBundle:
    return WorldStateBundle(
        world=WorldState(id="world_001", name="World", summary="Summary"),
        characters=[
            CharacterState(
                id="char_001",
                name="Aoi",
                role="detective",
                knowledge={"knows": ["駅にいる"], "believes": [], "does_not_know": []},
                private_mind=["Aoi private"],
                speech=SpeechProfile(first_person="私", forbidden_terms=["僕", "俺"]),
                stats={"hp": 10},
            ),
            CharacterState(
                id="char_002",
                name="Ren",
                role="suspect",
                private_mind=["Ren plans betrayal"],
                secrets=["Ren secret debt"],
                speech=SpeechProfile(first_person="俺", forbidden_terms=["僕"]),
                stats={"hp": 7},
            ),
        ],
        scenes=[
            SceneState(
                id="scene_001",
                location="駅",
                time="夜",
                active_characters=["char_001", "char_002"],
                reader_visible_facts=["駅は静か"],
                hidden_facts=[
                    HiddenFact(
                        id="fact_001",
                        text="Aoi can see this clue",
                        visibility=Visibility.CHARACTER,
                        known_by=["char_001"],
                    ),
                    HiddenFact(
                        id="fact_002",
                        text="Ren only clue",
                        visibility=Visibility.CHARACTER,
                        known_by=["char_002"],
                    ),
                ],
            )
        ],
        quests=[
            Quest(
                id="quest_001",
                title="出口を探す",
                status="advanced",
                objectives=["案内図を確認する"],
            ),
            Quest(id="quest_002", title="完了済み", status="resolved"),
        ],
        relationships=[
            RelationshipState(
                **{
                    "from": "char_001",
                    "to": "char_002",
                    "trust": 20,
                    "affection": 30,
                    "tension": 80,
                    "suspicion": 90,
                }
            )
        ],
        gm_vault=[GmVaultEntry(id="gm_vault_001", text="GM hidden truth")],
    )


def test_character_context_contains_only_unfinished_reader_safe_quests():
    context = build_character_context(_bundle(), "char_001")

    assert [quest.model_dump(mode="json") for quest in context.open_quests] == [
        {
            "id": "quest_001",
            "title": "出口を探す",
            "status": "advanced",
            "objectives": ["案内図を確認する"],
        }
    ]


def test_character_context_excludes_other_private_mind():
    context = build_character_context(_bundle(), "char_001")

    assert "Ren plans betrayal" not in context.model_dump_json()


def test_character_context_exposes_only_reader_safe_combat_target_eligibility():
    context = build_character_context(_bundle(), "char_001")

    assert [item.model_dump() for item in context.eligible_combat_targets] == [{"id": "char_002"}]
    serialized = context.model_dump_json()
    assert "Ren plans betrayal" not in serialized
    assert "Ren secret debt" not in serialized


def test_character_context_includes_own_speech_profile():
    # Only char_001's own speech profile is present; other characters are never embedded
    # in CharacterAgentInput at all (scoped_state is a copy of this character alone).
    context = build_character_context(_bundle(), "char_001")

    assert context.scoped_state.speech.first_person == "私"
    assert context.scoped_state.speech.forbidden_terms == ["僕", "俺"]


def test_character_context_excludes_hidden_from_event():
    events = [
        Event(
            id="event_0001",
            turn=1,
            type="secret",
            text="Hidden event",
            visibility=Visibility.SCENE,
            hidden_from=["char_001"],
        )
    ]

    context = build_character_context(_bundle(), "char_001", events=events)

    assert context.visible_events == []


def test_character_context_excludes_gm_vault():
    context = build_character_context(_bundle(), "char_001")

    assert "GM hidden truth" not in context.model_dump_json()


def test_character_context_includes_own_visible_facts():
    context = build_character_context(_bundle(), "char_001")

    assert "駅にいる" in context.visible_facts
    assert "駅は静か" in context.visible_facts
    assert "Aoi can see this clue" in context.visible_facts


def test_character_context_truncates_events_to_recent_limit():
    events = [
        Event(
            id=f"event_{index:04d}",
            turn=index,
            type="public",
            text=f"event {index}",
            visibility=Visibility.READER,
        )
        for index in range(1, 6)
    ]

    context = build_character_context(_bundle(), "char_001", events=events, event_limit=2)

    assert [event.text for event in context.visible_events] == ["event 4", "event 5"]


def test_character_context_includes_scene_summary():
    bundle = _bundle()
    bundle.scenes[0].summary = "霧の奥へ歩き始めた。"

    context = build_character_context(bundle, "char_001")

    assert "霧の奥へ歩き始めた。" in context.visible_facts


def test_character_context_omits_empty_scene_summary():
    context = build_character_context(_bundle(), "char_001")

    assert "" not in context.visible_facts


def test_character_context_includes_related_relationships():
    context = build_character_context(_bundle(), "char_001")

    assert len(context.relationships) == 1
    assert context.relationships[0].suspicion == 90


def test_character_context_includes_latest_memory_summary():
    bundle = _bundle()
    bundle.memory_summaries = [
        MemorySummary(id="memory_0005", up_to_turn=5, text="5ターン目までの要約"),
        MemorySummary(id="memory_0010", up_to_turn=10, text="10ターン目までの要約"),
    ]

    context = build_character_context(bundle, "char_001")

    assert "10ターン目までの要約" in context.visible_facts
    assert "5ターン目までの要約" not in context.visible_facts


def test_character_context_omits_memory_summary_when_none_exist():
    context = build_character_context(_bundle(), "char_001")

    assert "" not in context.visible_facts
    assert all("要約" not in fact for fact in context.visible_facts)


def test_character_context_excludes_facts_from_a_pending_scene():
    bundle = _bundle()
    bundle.scenes.append(
        SceneState(
            id="scene_002",
            location="次の場所",
            time="夜",
            active_characters=["char_001"],
            reader_visible_facts=["まだ始まっていない場面の手がかり"],
            status=SceneStatus.PENDING,
        )
    )

    context = build_character_context(bundle, "char_001")

    assert "まだ始まっていない場面の手がかり" not in context.visible_facts


def test_world_context_contains_full_state():
    context = build_world_context(_bundle())

    assert context.requires_visibility is True
    assert context.bundle.gm_vault[0].text == "GM hidden truth"
