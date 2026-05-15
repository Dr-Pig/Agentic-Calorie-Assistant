from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.composition.dogfood_feedback_source_refs import build_feedback_source_refs

DESKTOP_FEEDBACK_CATEGORIES = [
    "manager_behavior",
    "nutrition_estimate",
    "macro_gap",
    "fooddb_gap",
    "ui_ux",
    "bug",
    "latency",
    "product_feedback",
]

DESKTOP_FEEDBACK_ROUTING_TARGETS = {
    "manager_behavior": "ManagerRuntime",
    "nutrition_estimate": "ManagerRuntime",
    "macro_gap": "FoodDB",
    "fooddb_gap": "FoodDB",
    "ui_ux": "AppShell",
    "bug": "SharedCurrentShell",
    "latency": "ManagerRuntime",
    "product_feedback": "SharedCurrentShell",
}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _clean_optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _required_text(value: Any, *, field: str) -> str:
    text = _clean_optional_text(value)
    if text is None:
        raise ValueError(f"{field}_required")
    return text


def _normalized_feedback_category(category: Any) -> str:
    value = _required_text(category, field="category")
    if value not in DESKTOP_FEEDBACK_CATEGORIES:
        raise ValueError("unsupported_feedback_category")
    return value


def _feedback_triage(category: str) -> dict[str, Any]:
    routing_target = DESKTOP_FEEDBACK_ROUTING_TARGETS[category]
    return {
        "review_status": "needs_review",
        "routing_target": routing_target,
        "routing_reason": f"{category}_feedback",
        "routing_is_product_truth": False,
    }


def build_feedback_record_from_desktop_capture(
    *,
    category: str,
    feedback_text: str,
    page: str,
    selected_date: str,
    user_external_id: str,
    request_id: str | None = None,
    trace_id: str | None = None,
    message_id: str | None = None,
    meal_id: str | None = None,
    severity: str = "medium",
    ui_event: dict[str, Any] | None = None,
    operation_context: dict[str, Any] | None = None,
    auto_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_category = _normalized_feedback_category(category)
    triage = _feedback_triage(normalized_category)
    auto_context_payload = _object_dict(auto_context)
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_dogfood_feedback_record",
            "status": "captured",
            "feedback_id": f"feedback-{uuid4()}",
            "captured_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "local_dogfood_feedback_triage_record",
            "local_only": True,
            "contains_personal_diet_logs": True,
            "do_not_commit": True,
            "category": normalized_category,
            "review_status": triage["review_status"],
            "routing_target": triage["routing_target"],
            "triage": triage,
            "severity": _clean_optional_text(severity) or "medium",
            "feedback_text": _required_text(feedback_text, field="feedback_text"),
            "linked_context": {
                "page": _required_text(page, field="page"),
                "selected_date": _required_text(selected_date, field="selected_date"),
                "user_external_id": _required_text(user_external_id, field="user_external_id"),
                "request_id": _clean_optional_text(request_id) or _clean_optional_text(trace_id),
                "trace_id": _clean_optional_text(trace_id),
                "message_id": _clean_optional_text(message_id),
                "meal_id": _clean_optional_text(meal_id),
                "context_status": _clean_optional_text(auto_context_payload.get("context_status"))
                or "submitted_context_only",
                "auto_context_source": _clean_optional_text(auto_context_payload.get("auto_context_source")),
                "feedback_links_to_trace": bool(_clean_optional_text(trace_id)),
                "recent_messages": auto_context_payload.get("recent_messages")
                if isinstance(auto_context_payload.get("recent_messages"), list)
                else [],
                "read_model_snapshot": _object_dict(auto_context_payload.get("read_model_snapshot")),
            },
            "source_refs": build_feedback_source_refs(
                request_id=request_id or trace_id,
                trace_id=trace_id,
                message_id=message_id,
                meal_id=meal_id,
            ),
            "ui_event": _object_dict(ui_event),
            "operation_context": _object_dict(operation_context),
            "feedback_owner": "human_operator",
            "frontend_semantic_owner": False,
            "mutation_authority": False,
            "manager_context_injection_allowed": False,
            "food_kb_truth_update_allowed": False,
            "canonical_eval_promotion_allowed": False,
            "product_truth_update_allowed": False,
        }
    )


__all__ = [
    "DESKTOP_FEEDBACK_CATEGORIES",
    "DESKTOP_FEEDBACK_ROUTING_TARGETS",
    "build_feedback_record_from_desktop_capture",
]
