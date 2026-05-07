from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

SYNC_CONTRACT_PATH = Path("docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml")
MANAGER_RUNTIME_GATE_LEDGER_PATH = Path("docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml")
UPSTREAM_RUNTIME_GATE = "rt7_clarify_commit_correction_closure"
CLARIFY_COMMIT_CORRECTION_SAME_TRUTH_READY_STATUS = "clarify_commit_correction_same_truth_gate_ready_for_human_review"
REQUIRED_SHORT_TERM_CONTEXT_FLAGS = (
    "browser_executed",
    "pending_followup_created",
    "pending_followup_reloaded",
    "chat_history_context_fields_reloaded",
    "assistant_followup_bubble_rendered",
    "assistant_commit_bubble_rendered",
    "today_same_day_meal_rendered",
    "today_summary_rendered",
    "product_pages_no_debug_trace",
)
REQUIRED_TARGET_CANDIDATE_FLAGS = ("browser_executed", "target_candidate_surface_checked", "target_candidate_list_read_only", "context_strip_read_only", "product_pages_no_debug_trace")
REQUIRED_BROWSER_SMOKE_FLAGS = ("browser_executed", "today_meal_list_rendered", "today_summary_rendered")
REQUIRED_FIXTURE_STEPS = (
    "food_log", "listed_basket_commit", "correction", "removal",
    "reload_continuity", "browser_render_same_truth", "context_replay", "fake_provider_context_smoke",
)

def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))

def _read_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return dict(loaded) if isinstance(loaded, dict) else {}

def _truthy(value: Any) -> bool:
    if value is True:
        return True
    if value in (False, None):
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "claimed", "enabled"}
    if isinstance(value, int | float):
        return value != 0
    return False

def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")

def build_clarify_commit_correction_same_truth_gate_artifact(
    *,
    product_pages_browser_smoke: dict[str, Any],
    short_term_context_smoke: dict[str, Any],
    target_candidate_ui_smoke: dict[str, Any],
    fixture_full_product_loop_e2e: dict[str, Any],
    manager_runtime_gate_ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    gate_ledger = manager_runtime_gate_ledger or _read_yaml(MANAGER_RUNTIME_GATE_LEDGER_PATH)
    sync_contract = _read_yaml(SYNC_CONTRACT_PATH)

    gates = {
        str(entry.get("gate_id")): dict(entry)
        for entry in list(gate_ledger.get("gates") or [])
        if isinstance(entry, dict) and entry.get("gate_id")
    }
    upstream_gate = gates.get(UPSTREAM_RUNTIME_GATE, {})
    upstream_status = str(upstream_gate.get("status") or "missing")

    if _status(product_pages_browser_smoke) != "pass":
        blockers.append(
            f"product_pages_browser_smoke.unexpected_status:{product_pages_browser_smoke.get('status')}"
        )
    if _status(short_term_context_smoke) != "pass":
        blockers.append(
            f"short_term_context_smoke.unexpected_status:{short_term_context_smoke.get('status')}"
        )
    if _status(target_candidate_ui_smoke) != "pass":
        blockers.append(
            f"target_candidate_ui_smoke.unexpected_status:{target_candidate_ui_smoke.get('status')}"
        )
    if _status(fixture_full_product_loop_e2e) != "fixture_product_loop_e2e_diagnostic_pass":
        blockers.append(
            "fixture_full_product_loop_e2e.unexpected_status:"
            f"{fixture_full_product_loop_e2e.get('status')}"
        )

    for field in REQUIRED_BROWSER_SMOKE_FLAGS:
        if product_pages_browser_smoke.get(field) is not True:
            blockers.append(f"product_pages_browser_smoke.{field}_not_true")
    for field in REQUIRED_SHORT_TERM_CONTEXT_FLAGS:
        if short_term_context_smoke.get(field) is not True:
            blockers.append(f"short_term_context_smoke.{field}_not_true")
    for field in REQUIRED_TARGET_CANDIDATE_FLAGS:
        if target_candidate_ui_smoke.get(field) is not True:
            blockers.append(f"target_candidate_ui_smoke.{field}_not_true")

    if int(target_candidate_ui_smoke.get("target_candidate_count_rendered") or 0) < 2:
        blockers.append("target_candidate_ui_smoke.target_candidate_count_too_low")
    rendered_names = [str(item) for item in list(target_candidate_ui_smoke.get("target_candidate_names_rendered") or [])]
    for required_name in ("luwei", "milk tea"):
        if required_name not in rendered_names:
            blockers.append(f"target_candidate_ui_smoke.target_candidate_missing:{required_name}")

    completed_steps = {
        str(step) for step in list(fixture_full_product_loop_e2e.get("completed_product_loop_steps") or [])
    }
    for required_step in REQUIRED_FIXTURE_STEPS:
        if required_step not in completed_steps:
            blockers.append(f"fixture_full_product_loop_e2e.completed_step_missing:{required_step}")
    if fixture_full_product_loop_e2e.get("browser_executed") is not True:
        blockers.append("fixture_full_product_loop_e2e.browser_executed_not_true")
    if fixture_full_product_loop_e2e.get("fixture_evidence_used") is not True:
        blockers.append("fixture_full_product_loop_e2e.fixture_evidence_used_not_true")

    for payload_name, payload in (
        ("product_pages_browser_smoke", product_pages_browser_smoke),
        ("short_term_context_smoke", short_term_context_smoke),
        ("target_candidate_ui_smoke", target_candidate_ui_smoke),
        ("fixture_full_product_loop_e2e", fixture_full_product_loop_e2e),
    ):
        for forbidden_flag in (
            "frontend_semantic_owner",
            "frontend_selected_target",
            "deterministic_selected_target",
            "deterministic_semantic_inference_used",
            "raw_text_intent_router_used",
            "mutation_authority",
            "live_llm_invoked",
            "web_tavily_used",
            "fooddb_evidence_used",
            "real_fooddb_pass_claimed",
            "dogfood_pass",
            "web_readiness_claimed",
            "product_readiness_claimed",
            "private_self_use_approved",
        ):
            if _truthy(payload.get(forbidden_flag)):
                blockers.append(f"{payload_name}.{forbidden_flag}")

    if upstream_status != "green":
        blockers.append(f"upstream_gate.{UPSTREAM_RUNTIME_GATE}_not_green:{upstream_status}")

    status = CLARIFY_COMMIT_CORRECTION_SAME_TRUTH_READY_STATUS if not blockers else "blocked"
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_clarify_commit_correction_same_truth_gate",
            "status": status,
            "pass_type": "browser_executed",
            "claim_scope": "appshell_clarify_commit_correction_same_truth_for_human_review_only",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "journeys": ["B", "C", "D", "K"],
            "upstream_runtime_gate": UPSTREAM_RUNTIME_GATE,
            "upstream_runtime_gate_status": upstream_status,
            "current_shell_sync_contract_source": SYNC_CONTRACT_PATH.as_posix(),
            "manager_runtime_gate_ledger_source": MANAGER_RUNTIME_GATE_LEDGER_PATH.as_posix(),
            "current_shell_target": sync_contract.get("current_shell_target"),
            "artifact_inputs": {
                "product_pages_browser_smoke_status": product_pages_browser_smoke.get("status"),
                "short_term_context_smoke_status": short_term_context_smoke.get("status"),
                "target_candidate_ui_smoke_status": target_candidate_ui_smoke.get("status"),
                "fixture_full_product_loop_e2e_status": fixture_full_product_loop_e2e.get("status"),
            },
            "summary": {
                "required_short_term_context_flag_count": len(REQUIRED_SHORT_TERM_CONTEXT_FLAGS),
                "required_target_candidate_flag_count": len(REQUIRED_TARGET_CANDIDATE_FLAGS),
                "required_fixture_step_count": len(REQUIRED_FIXTURE_STEPS),
                "target_candidate_count_rendered": int(
                    target_candidate_ui_smoke.get("target_candidate_count_rendered") or 0
                ),
                "completed_fixture_step_count": len(completed_steps),
                "upstream_gate_green": upstream_status == "green",
            },
            "browser_truth": {
                "today_meal_list_rendered": product_pages_browser_smoke.get("today_meal_list_rendered"),
                "pending_followup_created": short_term_context_smoke.get("pending_followup_created"),
                "pending_followup_reloaded": short_term_context_smoke.get("pending_followup_reloaded"),
                "assistant_followup_bubble_rendered": short_term_context_smoke.get(
                    "assistant_followup_bubble_rendered"
                ),
                "assistant_commit_bubble_rendered": short_term_context_smoke.get(
                    "assistant_commit_bubble_rendered"
                ),
                "target_candidate_count_rendered": target_candidate_ui_smoke.get(
                    "target_candidate_count_rendered"
                ),
                "target_candidate_names_rendered": list(
                    target_candidate_ui_smoke.get("target_candidate_names_rendered") or []
                ),
                "completed_product_loop_steps": list(
                    fixture_full_product_loop_e2e.get("completed_product_loop_steps") or []
                ),
            },
            "blockers": blockers,
            "local_only": True,
            "diagnostic_only": True,
            "frontend_semantic_owner": False,
            "frontend_calculates_runtime_truth": False,
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
    "CLARIFY_COMMIT_CORRECTION_SAME_TRUTH_READY_STATUS",
    "build_clarify_commit_correction_same_truth_gate_artifact",
]
