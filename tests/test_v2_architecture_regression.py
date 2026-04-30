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
    assert "extract_provider" in source
    assert "manager_provider=manager_provider" in source
    assert "search_port=search_provider" in source
    assert "extract_port=extract_provider" in source
    assert f'{_legacy_provider_token("planner")}={_legacy_provider_token("planner")}' not in source
    assert f'{_legacy_provider_token("primary")}={_legacy_provider_token("primary")}' not in source


def test_runtime_trace_contract_exports_manager_stage_names() -> None:
    source = (ROOT / "app" / "runtime" / "contracts" / "trace.py").read_text(encoding="utf-8")

    assert 'MANAGER_LOOP_STAGE = "intake_manager_round"' in source


def test_v2_manager_tools_compatibility_facade_is_deleted() -> None:
    assert not (ROOT / "app" / "intake" / "application" / ("manager_" + "tools.py")).exists()


def test_v2_schemas_no_longer_exports_archived_recommendation_contracts() -> None:
    source = (ROOT / "app" / "schemas.py").read_text(encoding="utf-8")

    assert "RecommendationCandidate" not in source
    assert "RecommendationResponseResult" not in source
    assert "HintPacket" not in source


def test_v2_services_import_intake_domain_tools_and_ignore_legacy_provider_split() -> None:
    bundle1 = (ROOT / "app" / "intake" / "application" / "intake_turn_orchestrator.py").read_text(encoding="utf-8")
    bundle2 = (ROOT / "app" / "intake" / "application" / "intake_execution_orchestrator.py").read_text(encoding="utf-8")
    bundle2_tools = (ROOT / "app" / "runtime" / "application" / "bundle2_tool_batch.py").read_text(encoding="utf-8")
    estimation = (ROOT / "app" / "intake" / "application" / "intake_estimation_tools.py").read_text(encoding="utf-8")

    assert "manager_tools" not in bundle1
    assert "manager_tools" not in bundle2
    assert "from .intake_trace_tools import append_trace_event_tool" in bundle1
    assert "from .intake_trace_tools import append_trace_event_tool, resolve_correction_target_tool" in bundle2
    assert _legacy_provider_token("planner") not in bundle1
    assert _legacy_provider_token("primary") not in bundle1
    assert _legacy_provider_token("planner") not in bundle2
    assert _legacy_provider_token("primary") not in bundle2
    assert "search_adapter" not in bundle1
    assert "search_adapter" not in bundle2
    assert "search_adapter" not in bundle2_tools
    assert "search_adapter" not in estimation
