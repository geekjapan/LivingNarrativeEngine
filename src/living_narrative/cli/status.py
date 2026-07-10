"""``living-narrative status``: human-readable and ``--json`` project summary (cli/spec.md
"status の人間可読出力とJSON出力"). PC mode includes only the bound character's intended
private fields and never another character's private state or unknown GM facts."""

import json
from pathlib import Path

import typer

from living_narrative.cli._common import load_project_or_exit
from living_narrative.llm.costs import collect_project_costs
from living_narrative.pipeline import turn_dir_path
from living_narrative.pipeline.turn_numbering import read_turn_status
from living_narrative.session.player_character import build_player_character_projection
from living_narrative.session.resume import restore_resume_state
from living_narrative.state.models import SceneStatus, UserMode
from living_narrative.state.store import StateStore


def status(
    project: Path = typer.Option(..., "--project", help="Path to project.yaml"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON"),
) -> None:
    read = load_project_or_exit(project)
    bundle = StateStore.load(read.paths.state)
    resume_state = restore_resume_state(read.paths.runs, read.paths.root / "interventions.yaml")

    pending_turn = resume_state.pending_review_turn
    pending_status = (
        read_turn_status(turn_dir_path(read.paths.runs, pending_turn))
        if pending_turn is not None
        else None
    )
    active_scene = next((s for s in bundle.scenes if s.status == SceneStatus.ACTIVE), None)
    llm_usage = collect_project_costs(project, read.paths.runs)

    player_mode = read.config.user_mode is UserMode.PLAYER_CHARACTER
    pc_projection = (
        build_player_character_projection(read.config, bundle, active_scene)
        if player_mode
        else None
    )
    summary = {
        "current_turn": resume_state.last_applied_turn or 0,
        "pending_review": pending_turn is not None,
        "pending_review_turn": pending_turn,
        "pending_review_status": pending_status.value if pending_status else None,
        "user_mode": read.config.user_mode.value,
        "autonomy_level": read.config.autonomy_level.value,
        "scene": (
            pc_projection.scene.model_dump(mode="json")
            if pc_projection and pc_projection.scene
            else (
                {
                    "id": active_scene.id,
                    "location": active_scene.location,
                    "mood": active_scene.mood,
                }
                if active_scene is not None and not player_mode
                else None
            )
        ),
        "world_parameters": (
            pc_projection.world_parameters if pc_projection else dict(bundle.world.parameters)
        ),
        "visible_facts": pc_projection.visible_facts if pc_projection else [],
        "characters": (
            [item.model_dump(mode="json") for item in pc_projection.characters]
            if pc_projection
            else [
                {
                    "id": character.id,
                    "name": character.name,
                    "status": character.status.value,
                    "stats": dict(character.stats),
                    "skills": dict(character.skills),
                }
                for character in bundle.characters
            ]
        ),
        "llm_usage": llm_usage.model_dump(mode="json"),
    }

    if json_output:
        typer.echo(json.dumps(summary, ensure_ascii=False))
        return

    pending_status_label = pending_status.value if pending_status else "?"
    lines = [
        f"ターン: {summary['current_turn']}",
        (
            f"レビュー待ち: あり (turn {pending_turn}, {pending_status_label})"
            if pending_turn is not None
            else "レビュー待ち: なし"
        ),
        f"user_mode: {summary['user_mode']}",
        f"autonomy_level: {summary['autonomy_level']}",
        (
            f"現在のシーン: {summary['scene']['location']} ({summary['scene']['mood']})"
            if summary["scene"] is not None
            else "現在のシーン: なし"
        ),
        f"world parameters: {summary['world_parameters']}",
        *([f"可視情報: {summary['visible_facts']}"] if player_mode else []),
        "キャラクター:",
        *(
            f"  {character['id']} {character['name']} [{character['status']}] "
            f"stats={character['stats']} skills={character['skills']}"
            for character in summary["characters"]
        ),
        (
            f"LLM利用: {llm_usage.calls} calls / {llm_usage.total_tokens} tokens "
            f"(prompt {llm_usage.prompt_tokens}, completion {llm_usage.completion_tokens})"
        ),
        (
            f"概算費用: ${llm_usage.cost_usd:.6f} USD"
            if llm_usage.cost_usd is not None
            else "概算費用: 価格未設定"
        ),
    ]
    lines.extend(
        f"  model {entry.model}: {entry.calls} calls / {entry.total_tokens} tokens / "
        + (f"${entry.cost_usd:.6f} USD" if entry.cost_usd is not None else "価格未設定")
        for entry in llm_usage.by_model
    )
    lines.extend(
        f"  profile {entry.profile_name or '未設定'}: "
        f"{entry.calls} calls / {entry.total_tokens} tokens / "
        + (f"${entry.cost_usd:.6f} USD" if entry.cost_usd is not None else "価格未設定")
        for entry in llm_usage.by_profile
    )
    typer.echo("\n".join(lines))
