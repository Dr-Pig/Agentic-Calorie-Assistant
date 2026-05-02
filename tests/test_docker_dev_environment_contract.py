from __future__ import annotations

import json
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


def test_devcontainer_uses_compose_app_service_without_runtime_activation() -> None:
    config = json.loads(_read(".devcontainer/devcontainer.json"))

    assert config["dockerComposeFile"] == "../compose.yaml"
    assert config["service"] == "app"
    assert config["workspaceFolder"] == "/app"
    assert config["overrideCommand"] is True
    assert "python scripts/verify_environment.py" in config["postCreateCommand"]


def test_ci_has_docker_dev_environment_gate_without_deployment_side_effects() -> None:
    ci = _read(".github/workflows/ci.yml")

    assert "docker-dev-environment" in ci
    assert "docker compose config" in ci
    assert "docker compose build app" in ci
    assert "docker compose run --rm test" in ci
    assert "docker/build-push-action" not in ci


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
