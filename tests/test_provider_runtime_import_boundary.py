from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from scripts import check_runtime_boundaries


def test_provider_runtime_import_does_not_reference_gemini_adapter() -> None:
    source = Path("app/runtime/interface/provider_runtime.py").read_text(encoding="utf-8")

    assert "gemini_adapter" not in source
    assert "GeminiAdapter" not in source
    assert "search_provider = TavilyAdapter()" not in source
    assert "TavilySearchPort" in source
    assert "extract_provider = TavilyExtractPort()" in source
    assert "TavilyExtractPort" in source


def test_provider_runtime_import_succeeds_without_gemini_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_MANAGER_PROVIDER", raising=False)
    monkeypatch.delenv("AI_PROVIDER", raising=False)

    module = importlib.import_module("app.runtime.interface.provider_runtime")

    assert module.manager_provider.readiness()["provider"] == "deepseek"
    assert module.search_provider.readiness()["provider"] == "tavily"
    assert module.extract_provider.readiness()["provider"] == "tavily"


@pytest.mark.asyncio
async def test_ping_reports_extract_readiness(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_MANAGER_PROVIDER", raising=False)
    monkeypatch.delenv("AI_PROVIDER", raising=False)

    module = importlib.import_module("app.runtime.interface.base_routes")
    payload = await module.ping()

    assert payload["extract"]["provider"] == "tavily"
    assert payload["search"]["provider"] == "tavily"


def test_gemini_provider_is_explicitly_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module("app.runtime.interface.provider_runtime")
    monkeypatch.setenv("AI_MANAGER_PROVIDER", "gemini")

    with pytest.raises(RuntimeError, match="Gemini provider is not supported"):
        module._create_provider(
            provider_env="AI_MANAGER_PROVIDER",
            default_provider="deepseek",
            role_label="manager",
        )


def test_startup_readiness_uses_selected_deepseek_provider_token(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module("app.readiness")
    monkeypatch.setenv("AI_MANAGER_PROVIDER", "deepseek")
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("AI_BUILDER_TOKEN", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-token")

    module.validate_config()


def test_startup_readiness_uses_selected_builderspace_provider_token(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module("app.readiness")
    monkeypatch.setenv("AI_MANAGER_PROVIDER", "builderspace")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("AI_BUILDER_TOKEN", "test-token")

    module.validate_config()


def test_startup_readiness_fails_missing_selected_provider_token(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module("app.readiness")
    monkeypatch.setenv("AI_MANAGER_PROVIDER", "deepseek")
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("AI_BUILDER_TOKEN", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(SystemExit):
        module.validate_config()


def test_runtime_boundary_gate_blocks_concrete_provider_imports_outside_composition_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = tmp_path
    target = root / "app" / "intake" / "application" / "bad_provider_import.py"
    target.parent.mkdir(parents=True)
    target.write_text("from app.providers.builderspace_adapter import BuilderSpaceAdapter\n", encoding="utf-8")
    monkeypatch.setattr(check_runtime_boundaries, "REPO_ROOT", root)

    findings = check_runtime_boundaries.collect_findings(target)

    assert any("provider-inversion violation" in finding.message for finding in findings)


def test_runtime_boundary_gate_allows_provider_runtime_composition_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = tmp_path
    target = root / "app" / "runtime" / "interface" / "provider_runtime.py"
    target.parent.mkdir(parents=True)
    target.write_text("from app.providers.builderspace_adapter import BuilderSpaceAdapter\n", encoding="utf-8")
    monkeypatch.setattr(check_runtime_boundaries, "REPO_ROOT", root)

    findings = check_runtime_boundaries.collect_findings(target)

    assert not any("provider-inversion violation" in finding.message for finding in findings)
