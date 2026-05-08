from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from app.composition.accurate_intake_product_pages_renderer_source_map_page_specs import (
    PAGE_SPECS,
)
from app.composition.accurate_intake_product_pages_renderer_source_map_same_truth_body import (
    SAME_TRUTH_FIELD_CONTRACTS_BODY,
)
from app.composition.accurate_intake_product_pages_renderer_source_map_same_truth_chat_today import (
    SAME_TRUTH_FIELD_CONTRACTS_CHAT_TODAY,
)
from app.composition.accurate_intake_product_pages_renderer_source_map_shared import (
    FORBIDDEN_SEMANTIC_FRAGMENTS,
    REQUIRED_PAGES,
)


SAME_TRUTH_FIELD_CONTRACTS = {
    **SAME_TRUTH_FIELD_CONTRACTS_CHAT_TODAY,
    **SAME_TRUTH_FIELD_CONTRACTS_BODY,
}
RENDERER_READY_STATUS = "product_pages_renderer_source_map_ready_for_human_review"
RENDERER_SOURCE_CLOSURE_READY_STATUS = "product_pages_renderer_source_closure_ready_for_browser"
REQUIRED_MANAGER_SOURCE_CLOSURE_GATES = (
    "rt6_bootstrap_no_plan_body_closure",
    "rt7_clarify_commit_correction_closure",
    "rt8_overshoot_runtime_truth",
    "rt11c_renderer_input_basis_evidence_pack",
    "rt14_limited_live_ladder",
)
ENDPOINT_METHOD_CONTRACT = {
    "/estimate": ("POST",),
    "/accurate-intake/chat-history": ("GET",),
    "/today/current-budget": ("GET",),
    "/body-plan/active": ("GET",),
    "/weight/observations": ("GET",),
    "/weight/observation": ("POST",),
    "/onboarding/bootstrap": ("POST",),
    "/body-plan/manual-daily-target": ("POST",),
    "/today/deficit-summary": ("GET",),
    "/today/effective-budget": ("GET",),
    "/today/weekly-progress": ("GET",),
}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _selector_present(html: str, selector: str) -> bool:
    return f'id="{selector.lstrip("#")}"' in html


def _strip_js_non_code(script: str) -> str:
    output: list[str] = []
    index = 0
    state = "code"
    quote = ""
    while index < len(script):
        char = script[index]
        next_char = script[index + 1] if index + 1 < len(script) else ""
        if state == "code":
            if char == "/" and next_char == "/":
                output.extend((" ", " "))
                index += 2
                state = "line_comment"
                continue
            if char == "/" and next_char == "*":
                output.extend((" ", " "))
                index += 2
                state = "block_comment"
                continue
            if char in {"'", '"', "`"}:
                output.append(" ")
                quote = char
                index += 1
                state = "string"
                continue
            output.append(char)
            index += 1
            continue
        if state == "line_comment":
            output.append("\n" if char == "\n" else " ")
            index += 1
            if char == "\n":
                state = "code"
            continue
        if state == "block_comment":
            if char == "*" and next_char == "/":
                output.extend((" ", " "))
                index += 2
                state = "code"
                continue
            output.append("\n" if char == "\n" else " ")
            index += 1
            continue
        if state == "string":
            if char == "\\":
                output.append("\n" if char == "\n" else " ")
                if next_char:
                    output.append("\n" if next_char == "\n" else " ")
                    index += 2
                else:
                    index += 1
                continue
            if char == quote:
                output.append(" ")
                index += 1
                state = "code"
                continue
            output.append("\n" if char == "\n" else " ")
            index += 1
            continue
    return "".join(output)


def _function_present(html: str, function_name: str) -> bool:
    scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", html, flags=re.IGNORECASE | re.DOTALL)
    declaration = re.compile(
        rf"^\s*(?:async\s+)?function\s+{re.escape(function_name)}\s*\(",
        re.MULTILINE,
    )
    return any(declaration.search(_strip_js_non_code(script)) is not None for script in scripts)


def _read_page_html(page: str, html_overrides: dict[str, str] | None) -> tuple[str, Path]:
    spec = PAGE_SPECS[page]
    path = Path(spec["path"])
    if html_overrides and page in html_overrides:
        return html_overrides[page], path
    return path.read_text(encoding="utf-8"), path


def _page_source_map(page: str, html: str, path: Path) -> tuple[dict[str, Any], list[str]]:
    spec = PAGE_SPECS[page]
    blockers: list[str] = []
    if f'data-page-id="{spec["page_id"]}"' not in html:
        blockers.append(f"{page}.missing_page_id:{spec['page_id']}")
    if f'data-surface-role="{spec["surface_role"]}"' not in html:
        blockers.append(f"{page}.missing_surface_role:{spec['surface_role']}")

    missing_selectors = [
        selector for selector in spec["selectors"] if not _selector_present(html, selector)
    ]
    missing_endpoints = [endpoint for endpoint in spec["endpoints"] if endpoint not in html]
    missing_render_functions = [
        function_name for function_name in spec["render_functions"] if not _function_present(html, function_name)
    ]
    missing_backend_fields = [field for field in spec["backend_fields"] if field not in html]
    forbidden_present = [
        fragment for fragment in FORBIDDEN_SEMANTIC_FRAGMENTS if fragment in html
    ]
    blockers.extend(f"{page}.missing_selector:{selector}" for selector in missing_selectors)
    blockers.extend(f"{page}.missing_endpoint:{endpoint}" for endpoint in missing_endpoints)
    blockers.extend(
        f"{page}.missing_render_function:{function_name}"
        for function_name in missing_render_functions
    )
    blockers.extend(
        f"{page}.missing_backend_field:{field}" for field in missing_backend_fields
    )
    blockers.extend(
        f"{page}.forbidden_semantic_fragment:{fragment}"
        for fragment in forbidden_present
    )

    return (
        {
            "source_artifact_path": str(path),
            "page_id": spec["page_id"],
            "surface_role": spec["surface_role"],
            "selectors": list(spec["selectors"]),
            "endpoints": list(spec["endpoints"]),
            "render_functions": list(spec["render_functions"]),
            "backend_fields": list(spec["backend_fields"]),
            "missing_selectors": missing_selectors,
            "missing_endpoints": missing_endpoints,
            "missing_render_functions": missing_render_functions,
            "missing_backend_fields": missing_backend_fields,
            "forbidden_semantic_fragments_present": forbidden_present,
            "render_only_boundary_ok": not forbidden_present,
        },
        blockers,
    )


def _same_truth_contract_blockers(source_map: dict[str, dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for page, contracts in SAME_TRUTH_FIELD_CONTRACTS.items():
        page_map = source_map.get(page, {})
        selectors = set(page_map.get("selectors") or [])
        endpoints = set(page_map.get("endpoints") or [])
        backend_fields = set(page_map.get("backend_fields") or [])
        missing_backend_fields = set(page_map.get("missing_backend_fields") or [])
        for field_id, contract in contracts.items():
            selector = str(contract.get("ui_selector") or "")
            endpoint = str(contract.get("read_model_or_api") or "")
            if selector not in selectors:
                blockers.append(f"{page}.same_truth_contract.{field_id}.missing_selector:{selector}")
            if endpoint not in endpoints:
                blockers.append(f"{page}.same_truth_contract.{field_id}.missing_endpoint:{endpoint}")
            for field in contract.get("required_backend_fields") or ():
                if field not in backend_fields or field in missing_backend_fields:
                    blockers.append(
                        f"{page}.same_truth_contract.{field_id}.missing_backend_field:{field}"
                    )
            if contract.get("truth_owner") in {None, "", "ui", "frontend"}:
                blockers.append(f"{page}.same_truth_contract.{field_id}.ui_truth_owner")
            if contract.get("frontend_role") not in {
                "render_backend_structured_fields_only",
                "preserve_query_context_only",
            }:
                blockers.append(f"{page}.same_truth_contract.{field_id}.frontend_role_not_render_only")
    return blockers


def _same_truth_contract_count() -> int:
    return sum(len(contracts) for contracts in SAME_TRUTH_FIELD_CONTRACTS.values())


def _manager_gate_statuses(manager_gate_ledger_artifact: dict[str, Any] | None) -> dict[str, str | None]:
    gates = (manager_gate_ledger_artifact or {}).get("gates") or []
    if not isinstance(gates, list):
        return {gate_id: None for gate_id in REQUIRED_MANAGER_SOURCE_CLOSURE_GATES}
    by_id = {
        str(gate.get("gate_id")): str(gate.get("status"))
        for gate in gates
        if isinstance(gate, dict) and gate.get("gate_id") is not None
    }
    return {gate_id: by_id.get(gate_id) for gate_id in REQUIRED_MANAGER_SOURCE_CLOSURE_GATES}


def _runtime_route_table() -> dict[str, list[str]]:
    from app.routes import router as app_router

    route_methods: dict[str, set[str]] = {}
    for route in app_router.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not path or not methods:
            continue
        route_methods.setdefault(str(path), set()).update(
            str(method) for method in methods if method not in {"HEAD", "OPTIONS"}
        )
    return {path: sorted(methods) for path, methods in route_methods.items()}


def _endpoint_contract_blockers(
    *,
    source_map: dict[str, dict[str, Any]],
    route_table: dict[str, list[str]],
) -> list[str]:
    blockers: list[str] = []
    page_endpoints = {
        endpoint
        for page in REQUIRED_PAGES
        for endpoint in source_map.get(page, {}).get("endpoints", [])
    }
    for endpoint, required_methods in ENDPOINT_METHOD_CONTRACT.items():
        if endpoint not in page_endpoints:
            blockers.append(f"renderer_source_map.endpoint_missing_from_pages:{endpoint}")
        if endpoint not in route_table:
            blockers.append(f"route_table.missing_endpoint:{endpoint}")
            continue
        available_methods = set(route_table.get(endpoint) or [])
        for method in required_methods:
            if method not in available_methods:
                blockers.append(f"route_table.endpoint_method_missing:{endpoint}:{method}")
    for endpoint in page_endpoints:
        if endpoint not in ENDPOINT_METHOD_CONTRACT:
            blockers.append(f"renderer_source_map.endpoint_missing_method_contract:{endpoint}")
    return blockers


def build_product_pages_renderer_source_map_artifact(
    *,
    html_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    source_map: dict[str, dict[str, Any]] = {}
    blockers: list[str] = []
    for page in REQUIRED_PAGES:
        html, path = _read_page_html(page, html_overrides)
        page_map, page_blockers = _page_source_map(page, html, path)
        source_map[page] = page_map
        blockers.extend(page_blockers)
    same_truth_blockers = _same_truth_contract_blockers(source_map)
    blockers.extend(same_truth_blockers)

    selector_count = sum(len(page["selectors"]) for page in source_map.values())
    endpoint_count = sum(len(page["endpoints"]) for page in source_map.values())
    backend_field_count = sum(len(page["backend_fields"]) for page in source_map.values())
    status = "product_pages_renderer_source_map_ready_for_human_review" if not blockers else "blocked"
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_product_pages_renderer_source_map",
            "status": status,
            "claim_scope": "product_pages_renderer_source_map_for_human_review_only",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "pages": list(REQUIRED_PAGES),
            "blockers": blockers,
            "source_map": source_map,
            "summary": {
                "page_count": len(REQUIRED_PAGES),
                "selector_count": selector_count,
                "endpoint_count": endpoint_count,
                "backend_field_count": backend_field_count,
                "same_truth_field_contract_count": _same_truth_contract_count(),
                "same_truth_contract_blocker_count": len(same_truth_blockers),
            },
            "same_truth_renderer_contract_status": (
                "ready_for_human_review" if not same_truth_blockers else "blocked"
            ),
            "same_truth_renderer_contract": SAME_TRUTH_FIELD_CONTRACTS,
            "review_checkpoints": [
                "chat_page_renders_conversation_from_chat_history_and_estimate_response",
                "today_page_renders_daily_diary_from_today_budget_read_model",
                "body_page_renders_body_plan_and_weight_read_models",
                "frontend_does_not_own_semantic_routing_or_kcal_math",
            ],
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": True,
            "aggregate_only": True,
            "self_generated_evidence_used": False,
            "render_only_boundary_ok": not blockers,
            "ui_truth_owner": False,
            "frontend_semantic_owner": False,
            "frontend_calculates_kcal": False,
            "frontend_calculates_remaining": False,
            "frontend_calculates_tdee": False,
            "frontend_selects_target": False,
            "context_engineering_fault_claimed": False,
            "human_review_required": True,
            "review_required_before_provider_call": True,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "shared_contract_changed": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_llm_invoked": False,
            "live_provider_called": False,
            "web_tavily_used": False,
            "websearch_evidence_used": False,
            "fooddb_evidence_used": False,
            "fooddb_truth_updated": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_db_used": False,
            "manager_context_packet_schema_changed": False,
            "mutation_authority": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
        }
    )


def build_product_pages_renderer_source_closure_artifact(
    *,
    manager_gate_ledger_artifact: dict[str, Any] | None,
    renderer_source_map_artifact: dict[str, Any] | None = None,
    route_table_override: dict[str, list[str]] | None = None,
    html_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    source_map_artifact = renderer_source_map_artifact or build_product_pages_renderer_source_map_artifact(
        html_overrides=html_overrides
    )
    source_map = source_map_artifact.get("source_map") or {}
    route_table = route_table_override if route_table_override is not None else _runtime_route_table()
    blockers: list[str] = []
    if source_map_artifact.get("status") != RENDERER_READY_STATUS:
        blockers.append(f"renderer_source_map.unexpected_status:{source_map_artifact.get('status')}")
    if source_map_artifact.get("blockers"):
        blockers.append("renderer_source_map.upstream_blockers_present")

    upstream_gate_statuses = _manager_gate_statuses(manager_gate_ledger_artifact)
    for gate_id, status in upstream_gate_statuses.items():
        if status != "green":
            blockers.append(f"manager_runtime_gate.{gate_id}_not_green:{status}")
    blockers.extend(
        _endpoint_contract_blockers(
            source_map=source_map,
            route_table=route_table,
        )
    )

    status = RENDERER_SOURCE_CLOSURE_READY_STATUS if not blockers else "blocked"
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_product_pages_renderer_source_closure_gate",
            "status": status,
            "pass_type": "contract",
            "claim_scope": "appshell_renderer_source_closure_for_browser_gate_input",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "pages": list(REQUIRED_PAGES),
            "blockers": blockers,
            "source_map_status": source_map_artifact.get("status"),
            "source_map_artifact_type": source_map_artifact.get("artifact_type"),
            "upstream_manager_gates": upstream_gate_statuses,
            "route_table_checked": True,
            "endpoint_method_contract": {
                endpoint: list(methods) for endpoint, methods in ENDPOINT_METHOD_CONTRACT.items()
            },
            "route_table_subset": {
                endpoint: route_table.get(endpoint)
                for endpoint in ENDPOINT_METHOD_CONTRACT
                if endpoint in route_table
            },
            "summary": {
                "page_count": len(REQUIRED_PAGES),
                "manager_runtime_gates_checked": len(REQUIRED_MANAGER_SOURCE_CLOSURE_GATES),
                "endpoint_method_contract_count": len(ENDPOINT_METHOD_CONTRACT),
                "route_endpoint_count": len(route_table),
            },
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "ui_truth_owner": False,
            "frontend_semantic_owner": False,
            "frontend_calculates_kcal": False,
            "frontend_calculates_remaining": False,
            "frontend_calculates_tdee": False,
            "frontend_selects_target": False,
            "context_engineering_fault_claimed": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "live_llm_invoked": False,
            "live_provider_called": False,
            "web_tavily_used": False,
            "websearch_evidence_used": False,
            "fooddb_evidence_used": False,
            "fooddb_truth_updated": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_db_used": False,
            "manager_context_packet_schema_changed": False,
            "mutation_authority": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
        }
    )


__all__ = [
    "REQUIRED_PAGES",
    "build_product_pages_renderer_source_map_artifact",
    "build_product_pages_renderer_source_closure_artifact",
]
