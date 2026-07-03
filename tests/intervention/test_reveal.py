from living_narrative.intervention.reveal import (
    must_not_reveal_texts,
    reveal_now_sources,
    target_id_of,
)
from living_narrative.pipeline.context import TurnContext
from living_narrative.random.engine import RandomEngine
from living_narrative.state.models import (
    GmVaultEntry,
    LLMConfig,
    ProjectConfig,
    WorkspaceConfig,
    WorldState,
    WorldStateBundle,
)


def _context(gm_vault=None) -> TurnContext:
    project = ProjectConfig(
        id="p",
        title="P",
        genre="g",
        tone="t",
        autonomy_level="auto",
        user_mode="watcher",
        random_seed="seed",
        renderer="novel",
        llm=LLMConfig(provider="mock", model="mock"),
        workspace=WorkspaceConfig(root=".", state="state", runs="runs", exports="exports"),
    )
    bundle = WorldStateBundle(
        world=WorldState(id="world_001", name="World", summary=""),
        gm_vault=gm_vault or [],
    )
    return TurnContext(
        turn=1, project=project, paths=None, bundle=bundle, random_engine=RandomEngine("seed")
    )


def test_target_id_of_reads_nested_target():
    item = {"type": "reveal_control", "target": {"kind": "gm_vault", "id": "gm_vault_001"}}
    assert target_id_of(item) == "gm_vault_001"


def test_target_id_of_falls_back_to_flat_target_id():
    item = {"type": "reveal_control", "target_id": "secret"}
    assert target_id_of(item) == "secret"


def test_must_not_reveal_texts_resolves_gm_vault_fact_text():
    context = _context(gm_vault=[GmVaultEntry(id="gm_vault_001", text="カイの秘密")])
    interventions = [
        {
            "type": "reveal_control",
            "target": {"kind": "gm_vault", "id": "gm_vault_001"},
            "constraints": {"mode": "must-not-reveal"},
        }
    ]

    texts = must_not_reveal_texts(context, interventions)

    assert "カイの秘密" in texts


def test_reveal_now_sources_finds_the_gm_vault_entry():
    entry = GmVaultEntry(id="gm_vault_001", text="真実")
    context = _context(gm_vault=[entry])
    interventions = [
        {
            "type": "reveal_control",
            "target": {"kind": "gm_vault", "id": "gm_vault_001"},
            "constraints": {"mode": "reveal-now"},
        }
    ]

    pairs = reveal_now_sources(context, interventions)

    assert pairs == [(interventions[0], entry)]


def test_reveal_now_sources_ignores_unresolvable_targets():
    context = _context()
    interventions = [
        {
            "type": "reveal_control",
            "target": {"kind": "gm_vault", "id": "gm_vault_999"},
            "constraints": {"mode": "reveal-now"},
        }
    ]

    assert reveal_now_sources(context, interventions) == []
