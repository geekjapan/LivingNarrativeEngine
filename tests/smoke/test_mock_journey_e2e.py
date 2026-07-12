"""Issue 063: the ADR-0005 D1 journey stays runnable in CI.

This test runs exactly three mock-provider turns from a clean ``init`` project. Turn 2 submits
one ``scene_directive`` intervention through the served Web API; the final assertions verify the
novel-draft export is non-empty and does not expose GM-only state.
"""

import yaml
from fastapi.testclient import TestClient
from typer.testing import CliRunner

import living_narrative.web.server as web_server
from living_narrative.cli import app

runner = CliRunner()


def test_mock_provider_journey_init_serve_intervene_and_export(tmp_path, monkeypatch):
    project_dir = tmp_path / "mist_station"

    # Start from clean state through the public init CLI and pin the seed for replayable turns.
    init_result = runner.invoke(
        app,
        [
            "init",
            "--title",
            "霧の駅",
            "--template",
            "mist_station",
            "--output",
            str(project_dir),
        ],
    )
    assert init_result.exit_code == 0, init_result.output

    project_path = project_dir / "project.yaml"
    project = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    project["random_seed"] = "issue-063-mock-journey-fixed-seed"
    project_path.write_text(
        yaml.safe_dump(project, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    assert project["llm"]["provider"] == "mock"
    assert project["random_seed"] == "issue-063-mock-journey-fixed-seed"

    # Invoke the public serve CLI, then drive the exact app handed to uvicorn over HTTP.
    served = {}

    def capture_server(app_instance, *, host, port):
        served.update(app=app_instance, host=host, port=port)

    monkeypatch.setattr(web_server.uvicorn, "run", capture_server)
    serve_result = runner.invoke(app, ["serve", "--project-root", str(tmp_path), "--port", "8765"])
    assert serve_result.exit_code == 0, serve_result.output
    assert served["host"] == "127.0.0.1"

    with TestClient(served["app"]) as client:
        assert client.get("/api/projects").json()[0]["name"] == "mist_station"

        # Three turns are the representative minimum: plain turn 1, intervention turn 2, plain
        # turn 3. The intervention is a user-submitted scene_directive via the Web API.
        turn_results = [client.post("/api/project/mist_station/turn")]
        turn_results.append(
            client.post(
                "/api/project/mist_station/turn",
                json={
                    "drafts": [
                        {
                            "type": "scene_directive",
                            "target": {"kind": "scene", "id": "scene_001"},
                            "content": "足音の方向へ慎重に近づく",
                            "visibility": "scene",
                        }
                    ]
                },
            )
        )
        turn_results.append(client.post("/api/project/mist_station/turn"))

        assert [response.status_code for response in turn_results] == [200, 200, 200]
        assert [response.json()["turn"] for response in turn_results] == [1, 2, 3]

        intervention_data = client.get("/api/project/mist_station/interventions").json()
        assert [entry["type"] for entry in intervention_data["history"]] == ["scene_directive"]

    # Export the reader-facing novel draft through the public CLI and check minimal structure plus
    # the disclosure contract: GM vault, hidden facts, private minds, and their text stay absent.
    export_result = runner.invoke(app, ["export", "novel", "--project", str(project_path)])
    assert export_result.exit_code == 0, export_result.output

    export_path = project_dir / "workspace" / "exports" / "novel_draft.md"
    assert export_path.is_file()
    export_text = export_path.read_text(encoding="utf-8")
    assert export_text.strip()
    assert "## 第1章" in export_text
    for forbidden_key in ("gm_vault", "hidden_facts", "secrets", "private_mind"):
        assert forbidden_key not in export_text

    gm_vault = yaml.safe_load(
        (project_dir / "workspace" / "state" / "gm_vault.yaml").read_text(encoding="utf-8")
    )
    assert gm_vault is not None, "gm_vault.yaml must contain entries"
    assert all(entry["text"] not in export_text for entry in gm_vault)
