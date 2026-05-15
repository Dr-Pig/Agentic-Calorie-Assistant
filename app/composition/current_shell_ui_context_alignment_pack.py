from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.current_shell_ui_context_alignment_policy import (
    EXPECTED_STATUSES,
    REQUIRED_INPUTS,
    _artifact_statuses,
    _claim_blockers,
    _group_specific_blockers,
    _identity_blockers,
    _int_value,
    _object_dict,
    _required_true_blockers,
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def build_pl_ce_ui_context_alignment_pack_artifact(
    input_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    inputs = {
        group_id: _object_dict(input_artifacts.get(group_id))
        for group_id in REQUIRED_INPUTS
    }
    blockers: list[str] = []
    for group_id, payload in inputs.items():
        blockers.extend(_identity_blockers(group_id, payload))
        blockers.extend(_claim_blockers(group_id, payload))
        blockers.extend(_required_true_blockers(group_id, payload))
        blockers.extend(_group_specific_blockers(group_id, payload))

    matrix_summary = _object_dict(inputs["context_coverage_matrix"].get("summary"))
    source_map_summary = _object_dict(inputs["product_pages_renderer_source_map"].get("summary"))
    status = "ui_context_alignment_ready_for_human_review" if not blockers else "blocked"
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pl_ce_ui_context_alignment_pack",
            "status": status,
            "claim_scope": "pl_ce_ui_context_alignment_for_human_review_only",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "required_inputs": list(REQUIRED_INPUTS),
            "blockers": blockers,
            "included_artifact_statuses": _artifact_statuses(inputs),
            "summary": {
                "pages_verified": ["chat", "today", "body"],
                "context_covered_capabilities": _int_value(
                    matrix_summary.get("covered_capability_count")
                ),
                "context_known_runtime_gap_count": _int_value(
                    matrix_summary.get("known_runtime_gap_count")
                ),
                "renderer_source_map_page_count": _int_value(
                    source_map_summary.get("page_count")
                ),
                "renderer_source_map_selector_count": _int_value(
                    source_map_summary.get("selector_count")
                ),
                "renderer_source_map_endpoint_count": _int_value(
                    source_map_summary.get("endpoint_count")
                ),
                "seven_day_diary_checked": inputs["product_pages_seven_day_diary_smoke"].get(
                    "seven_day_window_checked"
                )
                is True,
                "chat_context_reload_checked": inputs[
                    "product_pages_short_term_context_smoke"
                ].get("chat_history_context_fields_reloaded")
                is True,
                "body_read_model_checked": inputs["product_pages_browser_smoke"].get(
                    "body_plan_readback_checked"
                )
                is True,
            },
            "review_checkpoints": [
                "chat_page_renders_short_term_context_without_semantic_ownership",
                "today_page_renders_seven_day_daily_diary_without_trace_panel",
                "body_page_renders_backend_read_model_without_tdee_math",
                "context_coverage_matrix_is_included_before_human_review",
            ],
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": True,
            "aggregate_only": True,
            "self_generated_evidence_used": False,
            "render_only_boundary_ok": not blockers,
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
            "frontend_semantic_owner": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
        }
    )


__all__ = [
    "EXPECTED_STATUSES",
    "REQUIRED_INPUTS",
    "build_pl_ce_ui_context_alignment_pack_artifact",
]
