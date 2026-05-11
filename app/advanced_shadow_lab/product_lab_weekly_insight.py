from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.product_lab_weekly_insight_report import (
    build_weekly_insight_report,
    weekly_insight_chat_copy,
    weekly_insight_report_blockers,
    weekly_insight_source_refs,
)
from app.memory.application.long_term_context_shadow.weekly_insight_artifact import (
    _weekly_insight_shadow_artifact,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_weekly_insight"
)
ARTIFACT_TYPE = "advanced_product_lab_weekly_insight_artifact"


def run_product_lab_weekly_insight(
    *, fixture_inputs: Mapping[str, Any], enabled: bool
) -> dict[str, Any]:
    if not enabled:
        return inactive_weekly_insight_artifact()
    fixture = _mapping(fixture_inputs.get("weekly_insight_fixture_payload"))
    if not fixture:
        return _blocked(["weekly_insight_fixture_payload.missing"])
    shadow = _weekly_insight_shadow_artifact(dict(fixture))
    report = build_weekly_insight_report(fixture)
    blockers = weekly_insight_report_blockers(report)
    allowed = not blockers
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "pass",
        "lab_enabled": True,
        "chat_first": True,
        "weekly_insight_report_generated": True,
        "weekly_insight_chat_candidate_allowed": allowed,
        "lab_chat_delivery_allowed": allowed,
        "weekly_insight_report": report,
        "lab_chat_copy": weekly_insight_chat_copy(report),
        "source_shadow_artifact": shadow,
        "source_output_refs": weekly_insight_source_refs(fixture, report),
        "best_practice_evidence": _best_practice_evidence(),
        "llm_boundary": {
            "narrative_summary_generated": True,
            "may_synthesize_framing": True,
            "may_invent_metrics": False,
            "deterministic_metrics_are_truth": True,
        },
        "scheduler_delivery_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "notification_delivery_allowed": False,
        "push_or_line_delivery_connected": False,
        "served_to_mainline_user": False,
        "mainline_activation_enabled": False,
        "self_use_v1_affected": False,
        "weekly_insight_report_written_to_product_db": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "blockers": blockers,
        **dict(FALSE_FLAGS),
    }


def inactive_weekly_insight_artifact() -> dict[str, Any]:
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "not_applicable",
        "lab_enabled": False,
        "weekly_insight_report_generated": False,
        "weekly_insight_chat_candidate_allowed": False,
        "lab_chat_delivery_allowed": False,
        "blockers": [],
        **dict(FALSE_FLAGS),
    }


def _blocked(blockers: list[str]) -> dict[str, Any]:
    return {
        **inactive_weekly_insight_artifact(),
        "status": "blocked",
        "blockers": blockers,
    }


def _best_practice_evidence() -> dict[str, Any]:
    return {
        "required": True,
        "sources_checked": [
            "https://openai.github.io/openai-agents-python/guardrails/",
            "https://platform.openai.com/docs/guides/evaluation-best-practices",
            "https://openai.github.io/openai-agents-python/sessions/",
        ],
        "adopted_guidance": [
            "guard before delivery and keep output/tool side effects blocked",
            "separate session history from durable memory truth",
            "keep fixture evidence and replay artifacts explicit",
        ],
        "rejected_guidance": ["no production scheduler activation in this slice"],
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "inactive_weekly_insight_artifact",
    "run_product_lab_weekly_insight",
]
