from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_PAGES = ("chat", "today", "body")

PAGE_SPECS = {
    "chat": {
        "path": ROOT / "static" / "accurate-intake-chat.html",
        "page_id": "accurate-intake-chat-page-v1",
        "surface_role": "chat",
        "selectors": (
            "#chat-scroll",
            "#message-input",
            "#send-button",
            "#chat-history-status",
            "#user-id",
            "#local-date",
            "#chat-day-link",
            "#composer",
        ),
        "endpoints": ("/estimate", "/accurate-intake/chat-history"),
        "render_functions": (
            "renderHistory",
            "appendMessage",
            "loadHistory",
            "submitMessage",
            "updateNavigationLinks",
            "updateCurrentUrl",
        ),
        "backend_fields": (
            "payload.messages",
            "message.role",
            "message.content",
            "payload.coach_message",
            "payload.message_count",
            "user_id: userId()",
            "local_date: selectedDate()",
            "allow_search: false",
        ),
    },
    "today": {
        "path": ROOT / "static" / "accurate-intake-today.html",
        "page_id": "accurate-intake-today-page-v1",
        "surface_role": "today-diary",
        "selectors": (
            "#user-id",
            "#selected-date",
            "#previous-day",
            "#next-day",
            "#day-strip",
            "#budget-kcal",
            "#consumed-kcal",
            "#remaining-kcal",
            "#today-status",
            "#meal-list",
            "#chat-link",
        ),
        "endpoints": ("/today/current-budget",),
        "render_functions": (
            "renderDayStrip",
            "renderMeals",
            "loadToday",
            "writeText",
            "updateNavigationLinks",
            "updateCurrentUrl",
        ),
        "backend_fields": (
            "payload.budget_kcal",
            "payload.consumed_kcal",
            "payload.remaining_kcal",
            "payload.meals",
            "payload.status",
            "meal.meal_title",
            "meal.occurred_at",
            "meal.resolution_status",
            "meal.total_kcal",
        ),
    },
    "body": {
        "path": ROOT / "static" / "accurate-intake-body.html",
        "page_id": "accurate-intake-body-page-v1",
        "surface_role": "body-plan",
        "selectors": (
            "#body-plan-summary",
            "#plan-daily-target",
            "#plan-tdee",
            "#plan-current-weight",
            "#plan-target-weight",
            "#plan-activity",
            "#plan-goal",
            "#body-budget-loop",
            "#body-active-target",
            "#body-consumed-kcal",
            "#body-remaining-kcal",
            "#body-estimated-deficit",
            "#body-effective-budget",
            "#body-weekly-progress",
            "#body-status",
            "#weight-form",
            "#weight-kg",
            "#onboarding-form",
            "#manual-target-form",
            "#manual-daily-target",
            "#weight-history",
        ),
        "endpoints": (
            "/body-plan/active",
            "/weight/observations",
            "/weight/observation",
            "/onboarding/bootstrap",
            "/body-plan/manual-daily-target",
            "/today/deficit-summary",
            "/today/effective-budget",
            "/today/weekly-progress",
        ),
        "render_functions": (
            "renderPlan",
            "renderWeights",
            "renderBudgetReadModels",
            "loadBudgetReadModels",
            "loadBody",
            "writeText",
            "requestJson",
            "updateNavigationLinks",
            "updateCurrentUrl",
        ),
        "backend_fields": (
            "plan.plan_status",
            "plan.daily_budget_kcal",
            "plan.recommended_target_kcal",
            "plan.estimated_tdee",
            "plan.current_weight_kg",
            "plan.target_weight_kg",
            "plan.activity_level",
            "plan.goal_type",
            "payload.observations",
            "payload.weight_kg",
            "payload.active_body_plan",
            "payload.target_kcal",
            "payload.current_budget?.budget_kcal",
            "deficit.active_daily_target_kcal",
            "deficit.consumed_kcal",
            "deficit.remaining_kcal",
            "deficit.estimated_daily_deficit_kcal",
            "effective.runtime_effective_budget_kcal",
            "weekly.total_consumed_kcal",
            "weekly.estimated_weekly_deficit_kcal",
        ),
    },
}

SAME_TRUTH_FIELD_CONTRACTS = {
    "chat": {
        "conversation_history": {
            "ui_selector": "#chat-scroll",
            "displayed_fact": "date-scoped chat messages",
            "truth_owner": "composition_chat_history_read_model",
            "read_model_or_api": "/accurate-intake/chat-history",
            "required_backend_fields": ("payload.messages", "message.role", "message.content"),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "read_or_submit_message",
            "must_not": [
                "frontend_infer_intent",
                "frontend_infer_workflow",
                "frontend_select_target",
            ],
        },
        "current_turn_response": {
            "ui_selector": "#chat-scroll",
            "displayed_fact": "manager response bubble from current turn",
            "truth_owner": "manager_runtime_response",
            "read_model_or_api": "/estimate",
            "required_backend_fields": ("payload.coach_message",),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "submit_message_to_existing_backend_route",
            "must_not": [
                "frontend_infer_intent",
                "frontend_infer_logged_status",
                "frontend_infer_evidence_gap",
            ],
        },
        "session_navigation": {
            "ui_selector": "#local-date",
            "displayed_fact": "selected user and date context",
            "truth_owner": "browser_url_and_backend_query_contract",
            "read_model_or_api": "/accurate-intake/chat-history",
            "required_backend_fields": ("user_id: userId()", "local_date: selectedDate()"),
            "frontend_role": "preserve_query_context_only",
            "allowed_action": "navigate_between_chat_today_body",
            "must_not": [
                "frontend_create_memory",
                "frontend_override_backend_context",
            ],
        },
    },
    "today": {
        "budget_summary": {
            "ui_selector": "#remaining-kcal",
            "displayed_fact": "daily budget consumed and remaining values",
            "truth_owner": "budget_domain",
            "read_model_or_api": "/today/current-budget",
            "required_backend_fields": (
                "payload.budget_kcal",
                "payload.consumed_kcal",
                "payload.remaining_kcal",
            ),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "refresh_read_model",
            "must_not": [
                "frontend_recompute_consumed",
                "frontend_recompute_remaining",
                "frontend_infer_overshoot",
            ],
        },
        "meal_summaries": {
            "ui_selector": "#meal-list",
            "displayed_fact": "active meal summaries for selected day",
            "truth_owner": "intake_and_budget_projection",
            "read_model_or_api": "/today/current-budget",
            "required_backend_fields": (
                "payload.meals",
                "meal.meal_title",
                "meal.total_kcal",
                "meal.resolution_status",
            ),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "read_only_diary_navigation",
            "must_not": [
                "frontend_treat_summary_as_full_meal_truth",
                "frontend_infer_food_semantics",
            ],
        },
    },
    "body": {
        "active_body_plan": {
            "ui_selector": "#body-plan-summary",
            "displayed_fact": "active body plan and target posture",
            "truth_owner": "body_domain",
            "read_model_or_api": "/body-plan/active",
            "required_backend_fields": (
                "plan.daily_budget_kcal",
                "plan.recommended_target_kcal",
                "plan.estimated_tdee",
                "plan.current_weight_kg",
                "plan.target_weight_kg",
                "plan.activity_level",
                "plan.goal_type",
            ),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "refresh_read_model_or_submit_existing_forms",
            "must_not": [
                "frontend_calculate_tdee",
                "frontend_calculate_target",
                "frontend_infer_manual_override_legality",
            ],
        },
        "weight_observations": {
            "ui_selector": "#weight-history",
            "displayed_fact": "backend-supplied weight observations",
            "truth_owner": "body_domain",
            "read_model_or_api": "/weight/observations",
            "required_backend_fields": (
                "payload.observations",
                "payload.weight_kg",
            ),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "submit_weight_observation_to_existing_route",
            "must_not": [
                "frontend_infer_calibration_proposal",
                "frontend_infer_weight_trend",
            ],
        },
        "manual_target_readback": {
            "ui_selector": "#manual-daily-target",
            "displayed_fact": "manual daily target readback from backend",
            "truth_owner": "budget_and_body_plan_routes",
            "read_model_or_api": "/body-plan/manual-daily-target",
            "required_backend_fields": (
                "payload.target_kcal",
                "payload.current_budget?.budget_kcal",
            ),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "submit_existing_manual_target_form",
            "must_not": [
                "frontend_calculate_remaining",
                "frontend_infer_target_legality",
            ],
        },
        "budget_deficit_summary": {
            "ui_selector": "#body-budget-loop",
            "displayed_fact": "daily target consumed remaining and estimated deficit read model",
            "truth_owner": "composition_body_budget_read_model",
            "read_model_or_api": "/today/deficit-summary",
            "required_backend_fields": (
                "deficit.active_daily_target_kcal",
                "deficit.consumed_kcal",
                "deficit.remaining_kcal",
                "deficit.estimated_daily_deficit_kcal",
            ),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "refresh_read_model",
            "must_not": [
                "frontend_calculate_estimated_deficit",
                "frontend_infer_calibration_proposal",
            ],
        },
        "effective_budget": {
            "ui_selector": "#body-effective-budget",
            "displayed_fact": "runtime effective budget from budget composition read model",
            "truth_owner": "budget_composition_effective_budget_read_model",
            "read_model_or_api": "/today/effective-budget",
            "required_backend_fields": (
                "effective.runtime_effective_budget_kcal",
            ),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "refresh_read_model",
            "must_not": [
                "frontend_calculate_effective_budget",
                "frontend_calculate_remaining",
            ],
        },
        "weekly_progress": {
            "ui_selector": "#body-weekly-progress",
            "displayed_fact": "weekly consumed and estimated deficit summary from backend",
            "truth_owner": "composition_body_budget_weekly_read_model",
            "read_model_or_api": "/today/weekly-progress",
            "required_backend_fields": (
                "weekly.total_consumed_kcal",
                "weekly.estimated_weekly_deficit_kcal",
            ),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "refresh_read_model",
            "must_not": [
                "frontend_compute_weekly_deficit",
                "frontend_infer_weight_trend",
            ],
        },
    },
}

FORBIDDEN_SEMANTIC_FRAGMENTS = (
    "routeByKeyword",
    "rawTextRouting",
    "message.includes",
    "input.includes",
    "text.includes",
    "switch (text",
    "estimateKcal",
    "estimatedKcal",
    "calculateTdee",
    "calculateBmr",
    "activityMultiplier",
    "dailyDeficit =",
    "budget - consumed",
    "budget_kcal - consumed_kcal",
    "daily_target_kcal - consumed_kcal",
    "remaining =",
    "remainingKcal =",
    "workflow_effect =",
    "target_attachment =",
    "final_action =",
    "mutation_allowed =",
    "inferManagerContext",
    "inferEvidenceGap",
    "selectTarget",
    "localStorage",
    "sessionStorage",
)


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


__all__ = [
    "REQUIRED_PAGES",
    "build_product_pages_renderer_source_map_artifact",
]
