from __future__ import annotations

from typing import Any, Mapping


def memory_record_live_provider_payload(
    integrated_e2e_artifact: Mapping[str, Any],
    *,
    constraints: Mapping[str, Any],
) -> dict[str, Any]:
    chain = _mapping(integrated_e2e_artifact.get("integrated_chain_artifact"))
    return {
        "target_surface": "advanced_product_lab_memory_record_integrated_diagnostic",
        "source_artifact_type": str(integrated_e2e_artifact.get("artifact_type") or ""),
        "source_status": str(integrated_e2e_artifact.get("status") or ""),
        "memory_record_summary": {
            "memory_record_ids": list(
                integrated_e2e_artifact.get("source_memory_record_ids") or []
            ),
            "summary_drives_chain": bool(
                integrated_e2e_artifact.get("memory_record_summary_drives_chain")
            ),
            "recommendation_selected_candidate_id": str(
                integrated_e2e_artifact.get("recommendation_selected_candidate_id")
                or ""
            ),
            "recommendation_source_refs_include_memory_records": bool(
                integrated_e2e_artifact.get(
                    "recommendation_source_refs_include_memory_records"
                )
            ),
        },
        "integrated_ux_summary": {
            "journey_terminal_evidence_count": int(
                integrated_e2e_artifact.get("journey_terminal_evidence_count") or 0
            ),
            "chat_ux_packet_status": str(
                _mapping(chain.get("chat_ux_packet")).get("status") or ""
            ),
            "terminal_review_sink_status": str(
                _mapping(chain.get("terminal_review_sink")).get("status") or ""
            ),
        },
        "activation_boundary": {
            "lab_enabled": True,
            "mainline_activation_enabled": False,
            "mainline_runtime_connected": False,
            "durable_product_memory_written": False,
            "canonical_product_mutation_allowed": False,
            "user_facing_behavior_changed": False,
        },
        "constraints": dict(constraints),
    }


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["memory_record_live_provider_payload"]
