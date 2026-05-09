from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.composition.accurate_intake_product_pages_renderer_source_map import (
    build_product_pages_renderer_source_map_artifact,
)
from app.composition.accurate_intake_today_macro_runtime_flags import build_today_macro_runtime_summary_flags
TODAY_PAGE = Path("static/accurate-intake-today.html")
RENDERER_READY_STATUS = "product_pages_renderer_source_map_ready_for_human_review"
TODAY_MACRO_READY_STATUS = "today_macro_mirror_gate_ready_for_human_review"
TODAY_MACRO_RUNTIME_READY_STATUS = "today_macro_runtime_mirror_gate_ready_for_browser"
REQUIRED_MANAGER_RUNTIME_GATES = (
    "rt11c_renderer_input_basis_evidence_pack",
    "rt14_limited_live_ladder",
)
REQUIRED_SELECTORS = (
    "#macro-panel",
    "#macro-guard-reason",
    "#protein-g",
    "#carbs-g",
    "#fat-g",
)
REQUIRED_BACKEND_FIELDS = (
    "payload.consumed_protein",
    "payload.consumed_carbs",
    "payload.consumed_fat",
    "payload.show_macro",
    "payload.macro_guard_reason",
)
REQUIRED_CURRENT_BUDGET_PAYLOAD_FIELDS = (
    "consumed_protein",
    "consumed_carbs",
    "consumed_fat",
    "show_macro",
    "macro_guard_reason",
)
VISIBLE_PAYLOAD = {
    "show_macro": True,
    "macro_guard_reason": "backend hidden reason should not show here",
    "consumed_protein": 31,
    "consumed_carbs": 44,
    "consumed_fat": 12,
}
GUARDED_PAYLOAD = {
    "show_macro": False,
    "macro_guard_reason": "Backend says macros are insufficient today.",
    "consumed_protein": 31,
    "consumed_carbs": 44,
    "consumed_fat": 12,
}
def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))
def _extract_function_source(html: str, function_name: str) -> str:
    marker = f"function {function_name}("
    start = html.find(marker)
    if start == -1:
        raise AssertionError(f"Could not find {function_name} in Today page")
    brace_start = html.find("{", start)
    if brace_start == -1:
        raise AssertionError(f"Could not find opening brace for {function_name}")
    depth = 0
    index = brace_start
    while index < len(html):
        char = html[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return html[start : index + 1]
        index += 1
    raise AssertionError(f"Could not find closing brace for {function_name}")
def _run_render_macro_panel(payload: dict[str, object], *, html_override: str | None = None) -> dict[str, object]:
    html = html_override if html_override is not None else TODAY_PAGE.read_text(encoding="utf-8")
    function_source = _extract_function_source(html, "renderMacroPanel")
    payload_json = json.dumps(payload, ensure_ascii=False)
    node_script = f"""
const elements = new Map();
function makeElement(id) {{
  return {{
    id,
    textContent: "",
    hidden: false,
    dataset: {{}},
  }};
}}
const document = {{
  getElementById(id) {{
    if (!elements.has(id)) {{
      elements.set(id, makeElement(id));
    }}
    return elements.get(id);
  }},
}};
function el(id) {{
  return document.getElementById(id);
}}
function writeText(id, value) {{
  el(id).textContent = value == null ? "--" : String(value);
}}
{function_source}
const payload = {payload_json};
renderMacroPanel(payload);
const result = {{
  macro_panel_hidden: el("macro-panel").hidden,
  macro_state: el("macro-panel").dataset.macroState,
  macro_grid_hidden: el("macro-grid").hidden,
  macro_guard_reason_hidden: el("macro-guard-reason").hidden,
  macro_guard_reason_text: el("macro-guard-reason").textContent,
  protein_text: el("protein-g").textContent,
  carbs_text: el("carbs-g").textContent,
  fat_text: el("fat-g").textContent,
}};
process.stdout.write(JSON.stringify(result));
"""
    completed = subprocess.run(["node", "-e", node_script], check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)
def _runtime_gate_statuses(manager_gate_ledger_artifact: dict[str, Any] | None) -> dict[str, str | None]:
    gates = (manager_gate_ledger_artifact or {}).get("gates") or []
    if not isinstance(gates, list):
        return {gate_id: None for gate_id in REQUIRED_MANAGER_RUNTIME_GATES}
    by_id = {
        str(gate.get("gate_id")): str(gate.get("status"))
        for gate in gates
        if isinstance(gate, dict) and gate.get("gate_id") is not None
    }
    return {gate_id: by_id.get(gate_id) for gate_id in REQUIRED_MANAGER_RUNTIME_GATES}


def _validate_runtime_macro_case(
    *,
    payload: dict[str, object],
    runtime_case: dict[str, object],
) -> list[str]:
    blockers: list[str] = []
    expected_protein = str(payload.get("consumed_protein"))
    expected_carbs = str(payload.get("consumed_carbs"))
    expected_fat = str(payload.get("consumed_fat"))
    if payload.get("show_macro") is True:
        if runtime_case["macro_state"] != "visible":
            blockers.append("today_macro_runtime_panel.visible_case.macro_state_not_visible")
        if runtime_case["macro_grid_hidden"] is not False:
            blockers.append("today_macro_runtime_panel.visible_case.macro_grid_hidden")
        if runtime_case["macro_guard_reason_hidden"] is not True:
            blockers.append("today_macro_runtime_panel.visible_case.guard_reason_visible")
        if runtime_case["protein_text"] != expected_protein:
            blockers.append("today_macro_runtime_panel.visible_case.protein_text_mismatch")
        if runtime_case["carbs_text"] != expected_carbs:
            blockers.append("today_macro_runtime_panel.visible_case.carbs_text_mismatch")
        if runtime_case["fat_text"] != expected_fat:
            blockers.append("today_macro_runtime_panel.visible_case.fat_text_mismatch")
        return blockers

    if payload.get("show_macro") is False:
        if runtime_case["macro_state"] != "guarded":
            blockers.append("today_macro_runtime_panel.guarded_case.macro_state_not_guarded")
        if runtime_case["macro_grid_hidden"] is not True:
            blockers.append("today_macro_runtime_panel.guarded_case.macro_grid_visible")
        if runtime_case["macro_guard_reason_hidden"] is not False:
            blockers.append("today_macro_runtime_panel.guarded_case.guard_reason_hidden")
        if runtime_case["macro_guard_reason_text"] != str(payload.get("macro_guard_reason")):
            blockers.append("today_macro_runtime_panel.guarded_case.guard_reason_text_mismatch")
        if runtime_case["protein_text"] != "--":
            blockers.append("today_macro_runtime_panel.guarded_case.protein_text_leaked")
        if runtime_case["carbs_text"] != "--":
            blockers.append("today_macro_runtime_panel.guarded_case.carbs_text_leaked")
        if runtime_case["fat_text"] != "--":
            blockers.append("today_macro_runtime_panel.guarded_case.fat_text_leaked")
        if not payload.get("macro_guard_reason"):
            blockers.append("current_budget_payload.guarded_case.missing_macro_guard_reason")
        return blockers

    blockers.append("current_budget_payload.show_macro_not_boolean")
    return blockers
def build_today_macro_mirror_gate_artifact(
    *,
    renderer_source_map_artifact: dict[str, Any] | None = None,
    html_override: str | None = None,
) -> dict[str, Any]:
    renderer = renderer_source_map_artifact or build_product_pages_renderer_source_map_artifact(
        html_overrides={"today": html_override} if html_override is not None else None
    )
    blockers: list[str] = []
    today_source_map = dict(renderer.get("source_map", {}).get("today") or {})
    if renderer.get("status") != RENDERER_READY_STATUS:
        blockers.append(f"renderer_source_map.unexpected_status:{renderer.get('status')}")
    if renderer.get("blockers"):
        blockers.append("renderer_source_map.upstream_blockers_present")
    selectors = set(today_source_map.get("selectors") or [])
    render_functions = set(today_source_map.get("render_functions") or [])
    backend_fields = set(today_source_map.get("backend_fields") or [])
    for selector in REQUIRED_SELECTORS:
        if selector not in selectors:
            blockers.append(f"renderer_source_map.today.missing_selector:{selector}")
    if "renderMacroPanel" not in render_functions:
        blockers.append("renderer_source_map.today.missing_render_function:renderMacroPanel")
    for field in REQUIRED_BACKEND_FIELDS:
        if field not in backend_fields:
            blockers.append(f"renderer_source_map.today.missing_backend_field:{field}")

    visible_case = _run_render_macro_panel(VISIBLE_PAYLOAD, html_override=html_override)
    guarded_case = _run_render_macro_panel(GUARDED_PAYLOAD, html_override=html_override)
    if visible_case["macro_panel_hidden"] is not False:
        blockers.append("today_macro_panel.visible_case.macro_panel_hidden")
    if visible_case["macro_state"] != "visible":
        blockers.append("today_macro_panel.visible_case.macro_state_not_visible")
    if visible_case["macro_grid_hidden"] is not False:
        blockers.append("today_macro_panel.visible_case.macro_grid_hidden")
    if visible_case["macro_guard_reason_hidden"] is not True:
        blockers.append("today_macro_panel.visible_case.macro_guard_reason_visible")
    if visible_case["protein_text"] != "31":
        blockers.append("today_macro_panel.visible_case.protein_text_mismatch")
    if visible_case["carbs_text"] != "44":
        blockers.append("today_macro_panel.visible_case.carbs_text_mismatch")
    if visible_case["fat_text"] != "12":
        blockers.append("today_macro_panel.visible_case.fat_text_mismatch")

    if guarded_case["macro_panel_hidden"] is not False:
        blockers.append("today_macro_panel.guarded_case.macro_panel_hidden")
    if guarded_case["macro_state"] != "guarded":
        blockers.append("today_macro_panel.guarded_case.macro_state_not_guarded")
    if guarded_case["macro_grid_hidden"] is not True:
        blockers.append("today_macro_panel.guarded_case.macro_grid_visible")
    if guarded_case["macro_guard_reason_hidden"] is not False:
        blockers.append("today_macro_panel.guarded_case.macro_guard_reason_hidden")
    if guarded_case["macro_guard_reason_text"] != str(GUARDED_PAYLOAD["macro_guard_reason"]):
        blockers.append("today_macro_panel.guarded_case.macro_guard_reason_text_mismatch")
    if guarded_case["protein_text"] == "31":
        blockers.append("today_macro_panel.guarded_case.protein_text_leaked")
    if guarded_case["carbs_text"] == "44":
        blockers.append("today_macro_panel.guarded_case.carbs_text_leaked")
    if guarded_case["fat_text"] == "12":
        blockers.append("today_macro_panel.guarded_case.fat_text_leaked")

    status = TODAY_MACRO_READY_STATUS if not blockers else "blocked"
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_today_macro_mirror_gate",
            "status": status,
            "pass_type": "contract",
            "claim_scope": "appshell_today_macro_mirror_gate_for_human_review_only",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "renderer_source_map_status": renderer.get("status"),
            "renderer_source_map_artifact_type": renderer.get("artifact_type"),
            "renderer_source_map_source_artifact_path": today_source_map.get("source_artifact_path"),
            "required_backend_fields": list(REQUIRED_BACKEND_FIELDS),
            "required_selectors": list(REQUIRED_SELECTORS),
            "visible_case": visible_case,
            "guarded_case": guarded_case,
            "summary": {
                "renderer_contract_fields_checked": len(REQUIRED_BACKEND_FIELDS),
                "visible_case_checked": True,
                "guarded_case_checked": True,
            },
            "blockers": blockers,
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": True,
            "frontend_semantic_owner": False,
            "frontend_calculates_macro_values": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        }
    )


def build_today_macro_runtime_mirror_gate_artifact(
    *,
    manager_gate_ledger_artifact: dict[str, Any] | None,
    current_budget_payload: dict[str, Any],
    renderer_source_map_artifact: dict[str, Any] | None = None,
    html_override: str | None = None,
) -> dict[str, Any]:
    base_gate = build_today_macro_mirror_gate_artifact(
        renderer_source_map_artifact=renderer_source_map_artifact,
        html_override=html_override,
    )
    blockers: list[str] = []
    if base_gate.get("status") != TODAY_MACRO_READY_STATUS:
        blockers.append(f"today_macro_mirror_gate.unexpected_status:{base_gate.get('status')}")
    if base_gate.get("blockers"):
        blockers.append("today_macro_mirror_gate.upstream_blockers_present")

    upstream_gate_statuses = _runtime_gate_statuses(manager_gate_ledger_artifact)
    for gate_id, status in upstream_gate_statuses.items():
        if status != "green":
            blockers.append(f"manager_runtime_gate.{gate_id}_not_green:{status}")

    missing_payload_fields = [
        field for field in REQUIRED_CURRENT_BUDGET_PAYLOAD_FIELDS if field not in current_budget_payload
    ]
    for field in missing_payload_fields:
        blockers.append(f"current_budget_payload.missing_field:{field}")

    runtime_case: dict[str, object] | None = None
    if not missing_payload_fields:
        runtime_case = _run_render_macro_panel(current_budget_payload, html_override=html_override)
        blockers.extend(
            _validate_runtime_macro_case(
                payload=current_budget_payload,
                runtime_case=runtime_case,
            )
        )

    status = TODAY_MACRO_RUNTIME_READY_STATUS if not blockers else "blocked"
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_today_macro_runtime_mirror_gate",
            "status": status,
            "pass_type": "runtime_backed",
            "claim_scope": "appshell_today_macro_runtime_mirror_gate_for_browser_closure",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "truth_owner": "CurrentBudgetView.macro_visibility",
            "renderer_role": "render_backend_structured_fields_only",
            "base_today_macro_mirror_gate_status": base_gate.get("status"),
            "upstream_manager_gates": upstream_gate_statuses,
            "current_budget_payload_fields_checked": list(REQUIRED_CURRENT_BUDGET_PAYLOAD_FIELDS),
            "runtime_case": runtime_case,
            "summary": {
                "manager_runtime_gates_checked": len(REQUIRED_MANAGER_RUNTIME_GATES),
                "current_budget_payload_fields_checked": len(REQUIRED_CURRENT_BUDGET_PAYLOAD_FIELDS),
                "runtime_dom_case_checked": runtime_case is not None,
            },
            "blockers": blockers,
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": False,
            "runtime_backed": True,
            **build_today_macro_runtime_summary_flags(base_gate, missing_payload_fields),
            "frontend_semantic_owner": False,
            "frontend_calculates_macro_values": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        }
    )


__all__ = [
    "build_today_macro_mirror_gate_artifact",
    "build_today_macro_runtime_mirror_gate_artifact",
]
