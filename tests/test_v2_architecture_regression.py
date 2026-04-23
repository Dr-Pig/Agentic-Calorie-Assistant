from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _legacy_provider_token(prefix: str) -> str:
    return prefix + "_provider"


def _legacy_request_support_token() -> str:
    return "text_meal_" + "request_support"


def test_v2_routes_use_manager_provider_entrypoint() -> None:
    # Phase 6d: canonical location is app/intake/interface/v2_routes.py;
    canonical = ROOT / "app" / "intake" / "interface" / "v2_routes.py"
    source = canonical.read_text(encoding="utf-8")

    assert "manager_provider" in source
    assert "search_provider" in source
    assert "manager_provider=manager_provider" in source
    assert f'{_legacy_provider_token("planner")}={_legacy_provider_token("planner")}' not in source
    assert f'{_legacy_provider_token("primary")}={_legacy_provider_token("primary")}' not in source


def test_runtime_trace_contract_exports_manager_stage_names() -> None:
    source = (ROOT / "app" / "runtime" / "contracts" / "trace.py").read_text(encoding="utf-8")

    assert 'MANAGER_LOOP_STAGE = "intake_manager_round"' in source


def test_v2_manager_tools_no_longer_imports_v1_orchestration_bridge() -> None:
    source = (ROOT / "app" / "intake" / "application" / "manager_tools.py").read_text(encoding="utf-8")

    assert "execute_text_meal_orchestration" not in source
    assert "OrchestrationOutcome" not in source
    assert _legacy_request_support_token() not in source


def test_v2_services_import_intake_domain_tools_and_ignore_legacy_provider_split() -> None:
    bundle1 = (ROOT / "app" / "intake" / "application" / "bundle1_service.py").read_text(encoding="utf-8")
    bundle2 = (ROOT / "app" / "intake" / "application" / "bundle2_service.py").read_text(encoding="utf-8")

    assert "from . import manager_tools as tools" in bundle1
    assert "from . import manager_tools as tools" in bundle2
    assert _legacy_provider_token("planner") not in bundle1
    assert _legacy_provider_token("primary") not in bundle1
    assert _legacy_provider_token("planner") not in bundle2
    assert _legacy_provider_token("primary") not in bundle2
