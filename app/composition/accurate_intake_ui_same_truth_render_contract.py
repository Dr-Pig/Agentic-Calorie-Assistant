from __future__ import annotations

from datetime import UTC, datetime
import json
import re
from typing import Any

REQUIRED_BACKEND_TRUTH_SELECTORS = (
    "#budget-kcal",
    "#consumed-kcal",
    "#remaining-kcal",
    "#meal-thread-list",
    "#pending-followup-list",
    "#runtime-status-list",
    "#failure-signal-list",
    "#same-truth-list",
)

REQUIRED_RENDER_FUNCTIONS = (
    "renderBudget",
    "renderDebug",
    "renderChatHistory",
    "renderReviewPanel",
)

REQUIRED_BACKEND_TRUTH_FIELDS = (
    "view.budget_kcal",
    "view.consumed_kcal",
    "view.remaining_kcal",
    "thread.active_version?.total_kcal",
    "thread.active_version?.status",
    "context_policy_version",
    "loaded_context_summary",
    "omitted_context_summary",
    "target_candidate_count",
)

FORBIDDEN_SEMANTIC_FRAGMENTS = (
    "routeByKeyword",
    "rawTextRouting",
    "message.includes",
    "input.includes",
    "text.includes",
    "switch (text",
    "estimateKcal",
    "estimatedKcal",
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


def build_ui_same_truth_render_contract(html: str) -> dict[str, Any]:
    missing_selectors = [
        selector
        for selector in REQUIRED_BACKEND_TRUTH_SELECTORS
        if not _selector_present(html, selector)
    ]
    missing_render_functions = [
        function_name
        for function_name in REQUIRED_RENDER_FUNCTIONS
        if not _function_present(html, function_name)
    ]
    missing_backend_truth_fields = [
        field for field in REQUIRED_BACKEND_TRUTH_FIELDS if field not in html
    ]
    forbidden_present = [
        fragment for fragment in FORBIDDEN_SEMANTIC_FRAGMENTS if fragment in html
    ]
    marker_blockers: list[str] = []
    if 'data-frontend-semantic-owner="false"' not in html:
        marker_blockers.append("frontend_semantic_owner_marker_missing")
    if 'data-live-llm-required="false"' not in html:
        marker_blockers.append("live_llm_required_marker_missing")
    blockers = [
        *[f"missing_selector:{selector}" for selector in missing_selectors],
        *[f"missing_render_function:{function_name}" for function_name in missing_render_functions],
        *[f"missing_backend_truth_field:{field}" for field in missing_backend_truth_fields],
        *[f"forbidden_semantic_fragment:{fragment}" for fragment in forbidden_present],
        *marker_blockers,
    ]
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_ui_same_truth_render_contract",
            "claim_scope": "local_shell_render_only_same_truth_contract",
            "status": "pass" if not blockers else "fail",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "blockers": blockers,
            "render_only_boundary_ok": not forbidden_present and not marker_blockers,
            "backend_truth_selectors_present": not missing_selectors,
            "required_render_functions_present": not missing_render_functions,
            "backend_truth_fields_present": not missing_backend_truth_fields,
            "backend_truth_selectors": list(REQUIRED_BACKEND_TRUTH_SELECTORS),
            "render_functions": list(REQUIRED_RENDER_FUNCTIONS),
            "backend_truth_fields": list(REQUIRED_BACKEND_TRUTH_FIELDS),
            "missing_selectors": missing_selectors,
            "missing_render_functions": missing_render_functions,
            "missing_backend_truth_fields": missing_backend_truth_fields,
            "forbidden_semantic_fragments_present": forbidden_present,
            "frontend_semantic_owner": False,
            "frontend_render_only": True,
            "ready_for_fdb_integration": False,
            "shared_contract_changed": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "fooddb_truth_updated": False,
            "fooddb_evidence_used": False,
            "websearch_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_db_used": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
        }
    )


__all__ = ["build_ui_same_truth_render_contract"]
