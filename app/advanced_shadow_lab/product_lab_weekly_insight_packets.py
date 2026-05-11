from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_weekly_insight_packets"
)


def with_weekly_insight_chat_packet(
    packets: list[Mapping[str, Any]],
    weekly_insight: Mapping[str, Any],
    proactive: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    if weekly_insight.get("status") != "pass":
        return packets
    if weekly_insight.get("weekly_insight_chat_candidate_allowed") is not True:
        return packets
    if "weekly_insight" not in set(proactive.get("pre_delivery_review", {}).get("allowed_trigger_types") or []):
        return packets
    return [*packets, _packet(weekly_insight, proactive)]


def weekly_insight_product_fields(packet: Mapping[str, Any]) -> dict[str, Any]:
    if str(packet.get("trigger_type") or "") != "weekly_insight":
        return {}
    return {
        "product_lab_copy": str(packet.get("product_lab_copy") or ""),
        "weekly_insight_report": dict(_mapping(packet.get("weekly_insight_report"))),
        "product_runtime_output_refs": [
            str(item) for item in packet.get("product_runtime_output_refs") or []
        ],
    }


def _packet(
    weekly_insight: Mapping[str, Any],
    proactive: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "packet_id": "weekly_insight:2",
        "workflow_family": "proactive",
        "trigger_type": "weekly_insight",
        "packet_kind": "weekly_insight_report",
        "surface": "chat",
        "product_lab_copy": str(weekly_insight.get("lab_chat_copy") or ""),
        "weekly_insight_report": _surface_report(weekly_insight),
        "product_runtime_output_refs": [
            str(weekly_insight.get("artifact_type") or ""),
            str(proactive.get("artifact_type") or ""),
        ],
        "served_to_lab_chat": True,
        "served_to_mainline_user": False,
        "scheduler_enqueued": False,
        "canonical_mutation_requested": False,
    }


def _surface_report(weekly_insight: Mapping[str, Any]) -> dict[str, Any]:
    report = _mapping(weekly_insight.get("weekly_insight_report"))
    return {
        "report_id": str(report.get("report_id") or ""),
        "week_start_date": str(report.get("week_start_date") or ""),
        "week_end_date": str(report.get("week_end_date") or ""),
        "deficit_achievement_rate": report.get("deficit_achievement_rate"),
        "logging_coverage": report.get("logging_coverage"),
        "overshoot_days": report.get("overshoot_days"),
        "top_calorie_sources": list(report.get("top_calorie_sources") or []),
        "positive_highlights": list(report.get("positive_highlights") or []),
        "swap_opportunities": list(report.get("swap_opportunities") or []),
        "narrative_summary": str(report.get("narrative_summary") or ""),
        "canonical_product_mutation_allowed": False,
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["weekly_insight_product_fields", "with_weekly_insight_chat_packet"]
