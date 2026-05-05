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
            "#body-budget-dashboard",
            "#deficit-summary-card",
            "#deficit-active-target",
            "#deficit-consumed",
            "#deficit-remaining",
            "#deficit-latest-weight",
            "#weekly-progress-card",
            "#weekly-progress-list",
            "#weekly-deficit",
            "#weekly-weight-delta",
            "#weekly-logged-days",
            "#effective-budget-card",
            "#effective-budget",
            "#effective-adjustment",
            "#effective-base",
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
            "/today/weekly-progress",
            "/today/effective-budget",
        ),
        "render_functions": (
            "renderPlan",
            "renderDeficitSummary",
            "renderWeeklyProgress",
            "renderEffectiveBudget",
            "loadBodyBudget",
            "renderWeights",
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
            "payload.active_daily_target_kcal",
            "payload.consumed_kcal",
            "payload.remaining_kcal",
            "payload.latest_weight_kg",
            "payload.days",
            "payload.estimated_weekly_deficit_kcal",
            "payload.weight_delta_kg",
            "payload.logged_day_count",
            "payload.runtime_effective_budget_kcal",
            "payload.runtime_adjustment_total_kcal",
            "payload.base_budget_kcal",
        ),
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
            },
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
            "frontend_semantic_owner": False,
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
