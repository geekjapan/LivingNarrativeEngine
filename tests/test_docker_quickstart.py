from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def test_dockerfile_uses_python_312_uv_and_web_extra() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text()

    assert "FROM python:3.12-slim" in dockerfile
    assert "COPY --from=uv /uv /uvx /bin/" in dockerfile
    assert "uv sync --frozen --no-dev --extra web" in dockerfile
    assert "living-narrative serve --project-root /projects --port 8000" in dockerfile


def test_compose_publishes_only_host_loopback() -> None:
    compose = yaml.safe_load((ROOT / "compose.yml").read_text())

    assert compose["services"]["app"]["ports"] == ["127.0.0.1:8000:8000"]
    assert compose["services"]["app"]["volumes"] == ["./projects:/projects"]


def test_secrets_and_local_workspaces_are_excluded() -> None:
    dockerignore = (ROOT / ".dockerignore").read_text().splitlines()
    gitignore = (ROOT / ".gitignore").read_text().splitlines()
    env_example = (ROOT / ".env.example").read_text()

    assert ".env" in dockerignore
    assert ".env" in gitignore
    assert "projects/" in gitignore
    assert "/sandbox" in dockerignore
    assert ".orca" in dockerignore
    assert "OPENAI_BASE_URL=" in env_example
    assert "OPENAI_API_KEY=" in env_example


def test_readme_quickstart_documents_local_and_compose_commands() -> None:
    readme = (ROOT / "README.md").read_text()

    required_commands = (
        "uv sync --extra web",
        "uv run living-narrative init",
        "uv run living-narrative serve",
        "docker compose build",
        "docker compose run --rm app living-narrative init",
        "docker compose up",
        "docker compose down",
    )
    assert all(command in readme for command in required_commands)
    assert "http://127.0.0.1:8000" in readme
