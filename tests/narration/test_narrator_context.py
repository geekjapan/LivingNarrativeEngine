from living_narrative.narration import build_narrator_context
from living_narrative.pipeline.context import TurnContext
from living_narrative.state.models import Event, Visibility
from living_narrative.state.store import StateStore
from living_narrative.workspace.loader import load_project


def _context(project_path, resolved_events) -> TurnContext:
    read = load_project(project_path)
    bundle = StateStore.load(read.paths.state)
    from living_narrative.random.engine import RandomEngine

    return TurnContext(
        turn=1,
        project=read.config,
        paths=read.paths,
        bundle=bundle,
        random_engine=RandomEngine(read.config.random_seed),
    )


def test_hidden_facts_and_gm_only_events_are_excluded(tmp_path, build_project):
    project_path = build_project(
        tmp_path,
        reader_visible_facts=["駅は静まり返っている"],
        hidden_facts=[
            {"id": "fact_001", "text": "実は爆弾がある", "visibility": "gm_only", "known_by": []}
        ],
    )
    events = [
        Event(
            id="event_0001",
            turn=1,
            type="secret",
            text="秘密の出来事",
            visibility=Visibility.GM_ONLY,
        ),
        Event(
            id="event_0002",
            turn=1,
            type="public",
            text="公開の出来事",
            visibility=Visibility.READER,
        ),
    ]

    narrator_context = build_narrator_context(_context(project_path, events), events)

    assert "実は爆弾がある" not in narrator_context.model_dump_json()
    assert "秘密の出来事" not in [e.text for e in narrator_context.reader_visible_events]
    assert "公開の出来事" in [e.text for e in narrator_context.reader_visible_events]
    assert narrator_context.scene_reader_visible_facts == ["駅は静まり返っている"]


def test_must_not_reveal_intervention_filters_matching_reader_visible_content(
    tmp_path, build_project
):
    project_path = build_project(tmp_path, reader_visible_facts=["秘密の手がかりがある"])
    events = [
        Event(
            id="event_0001",
            turn=1,
            type="public",
            text="秘密の手がかりがある",
            visibility=Visibility.READER,
        )
    ]
    interventions = [
        {
            "type": "reveal_control",
            "target_id": "秘密の手がかりがある",
            "constraints": {"mode": "must-not-reveal"},
        }
    ]

    narrator_context = build_narrator_context(_context(project_path, events), events, interventions)

    assert narrator_context.scene_reader_visible_facts == []
    assert narrator_context.reader_visible_events == []
