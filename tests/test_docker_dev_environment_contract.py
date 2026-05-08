from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_compose_yaml_defines_app_and_test_dev_services() -> None:
    compose = _read("compose.yaml")

    assert "services:" in compose
    assert "  app:" in compose
    assert "  test:" in compose
    assert "target: dev" in compose
    assert "PYTHONPATH: /app" in compose
    assert ".:/app" in compose
    assert "uvicorn app.main:app" in compose
    assert "python -m pytest" in compose


def test_legacy_compose_yml_is_not_the_canonical_dev_file() -> None:
    assert not (ROOT / "compose.yml").exists()


def test_dockerignore_keeps_dev_verification_inputs_available() -> None:
    ignored = set(_read(".dockerignore").splitlines())

    for forbidden in ("docs/", "tests/", "scripts/", "*.md"):
        assert forbidden not in ignored

    for required in (".env", ".venv", ".git", "artifacts/", "runtime/", "workspace_data/"):
        assert required in ignored


def test_devcontainer_is_not_claimed_without_tracked_config() -> None:
    readme = _read("README.md")

    assert not (ROOT / ".devcontainer" / "devcontainer.json").exists()
    assert "No Dev Container is currently tracked" in readme


def test_readme_uses_current_public_repo_identity() -> None:
    readme = _read("README.md")

    assert readme.lstrip("\ufeff").startswith("# Agentic Calorie Assistant")
    assert "Text Meal Canary" not in readme
    assert "](/C:/Users/User/" not in readme
    assert "[AGENTS.md](AGENTS.md)" in readme
    assert "[docs/DOC_INDEX.md](docs/DOC_INDEX.md)" in readme


def test_docker_dev_environment_is_local_manual_only_without_advisory_workflow() -> None:
    assert not (ROOT / ".github" / "workflows" / "ci-advisory.yml").exists()

    compose = _read("compose.yaml")
    assert "  app:" in compose
    assert "  test:" in compose
    assert "docker/build-push-action" not in compose


def test_dockerfile_is_local_parity_not_deploy_surface() -> None:
    dockerfile = _read("Dockerfile")

    assert "FROM base AS dev" in dockerfile
    assert "FROM base AS runtime" not in dockerfile
    assert "Render" not in dockerfile
    assert "Railway" not in dockerfile
    assert "Fly" not in dockerfile
    assert "alembic upgrade head && uvicorn" not in dockerfile


def test_readme_documents_mac_docker_and_python312_fallback() -> None:
    readme = _read("README.md")

    assert "Docker / Mac Recommended" in readme
    assert "docker compose build app" in readme
    assert "docker compose run --rm test" in readme
    assert "Python 3.12" in readme
    assert "Python 3.9" in readme


def test_docker_and_shell_files_are_lf_normalized_for_mac_linux() -> None:
    attributes = _read(".gitattributes")

    assert "*.sh text eol=lf" in attributes
    assert "Dockerfile text eol=lf" in attributes
    assert ".dockerignore text eol=lf" in attributes
