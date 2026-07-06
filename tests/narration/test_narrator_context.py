import yaml

from living_narrative.narration import build_narrator_context
from living_narrative.pipeline.context import TurnContext
from living_narrative.state.models import Event, Visibility
from living_narrative.state.store import StateStore
from living_narrative.workspace.loader import load_project


def _write_unresolved_threads(project_path, threads: list[dict]) -> None:
    state_dir = project_path.parent / "workspace" / "state"
    (state_dir / "unresolved_threads.yaml").write_text(
        yaml.safe_dump(threads, allow_unicode=True), encoding="utf-8"
    )


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


def test_scene_summary_from_active_scene_is_included(tmp_path, build_project):
    project_path = build_project(tmp_path, scene_summary="霧の中、足音が近づいている。")

    narrator_context = build_narrator_context(_context(project_path, []), [])

    assert narrator_context.scene_summary == "霧の中、足音が近づいている。"


def test_scene_summary_defaults_to_empty_string(tmp_path, build_project):
    project_path = build_project(tmp_path)

    narrator_context = build_narrator_context(_context(project_path, []), [])

    assert narrator_context.scene_summary == ""


def test_open_threads_are_supplied_and_resolved_ones_are_excluded(tmp_path, build_project):
    project_path = build_project(tmp_path)
    _write_unresolved_threads(
        project_path,
        [
            {
                "id": "thread_000101",
                "description": "お守りの由来は謎のままだ。",
                "status": "open",
                "related_event_ids": [],
                "notes": [],
                "opened_turn": 1,
            },
            {
                "id": "thread_000102",
                "description": "案内板の謎はもう解けている。",
                "status": "resolved",
                "related_event_ids": [],
                "notes": [],
                "opened_turn": 1,
            },
        ],
    )

    narrator_context = build_narrator_context(_context(project_path, []), [])

    assert [thread.id for thread in narrator_context.open_threads] == ["thread_000101"]
    assert narrator_context.open_threads[0].description == "お守りの由来は謎のままだ。"
    assert narrator_context.open_threads[0].opened_turn == 1


def test_no_unresolved_threads_yields_empty_open_threads(tmp_path, build_project):
    project_path = build_project(tmp_path)

    narrator_context = build_narrator_context(_context(project_path, []), [])

    assert narrator_context.open_threads == []


def test_pending_scene_facts_and_summary_are_excluded(tmp_path, build_project):
    project_path = build_project(
        tmp_path,
        scene_status="pending",
        reader_visible_facts=["まだ始まっていない場面の手がかり"],
        scene_summary="まだ語られていない場面。",
    )

    narrator_context = build_narrator_context(_context(project_path, []), [])

    assert narrator_context.scene_reader_visible_facts == []
    assert narrator_context.scene_summary == ""
