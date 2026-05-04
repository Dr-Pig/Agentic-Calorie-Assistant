from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any


def _json_safe(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(payload, ensure_ascii=False, default=str))
    if not isinstance(normalized, dict):  # pragma: no cover - guarded by type hints
        raise ValueError("body budget diagnostic payload must be an object")
    return normalized


def build_body_budget_sync_diagnostic_artifact(
    body_budget_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_schema_version": "body_budget_sync_diagnostic.v1",
        "artifact_type": "body_budget_sync_diagnostic",
        "status": "ok",
        "generated_at": datetime.now(UTC).isoformat(),
        "claim_scope": "local_body_budget_diagnostic",
        "local_only": True,
        "diagnostic_only": True,
        "body_budget_summary": _json_safe(body_budget_summary),
        "runtime_truth_changed": {
            "scope": "body_budget_read_model_only",
            "does_not_change": [
                "meal_thread_truth",
                "nutrition_evidence_truth",
                "fooddb_truth",
                "manager_context_packet",
                "rescue_proposal_truth",
                "recommendation_truth",
                "proactive_trigger_truth",
            ],
        },
        "live_tool_calling": False,
        "automatic_calibration_enabled": False,
        "rescue_enabled": False,
        "recommendation_enabled": False,
        "proactive_enabled": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
    }


__all__ = ["build_body_budget_sync_diagnostic_artifact"]
