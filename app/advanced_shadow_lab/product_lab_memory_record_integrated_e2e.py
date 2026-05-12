from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain import (
    run_advanced_shadow_e2e_fixture_chain,
)
from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.product_lab_memory_record_e2e_inputs import (
    build_memory_record_chain_payload,
    memory_record_ids,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_memory_record_integrated_e2e"
)
NON_CLAIMS = [
    "not_mainline_runtime_activation",
    "not_self_use_v1_activation",
    "not_production_scheduler_delivery",
    "not_canonical_mutation",
    "not_durable_product_memory",
]


def run_memory_record_integrated_e2e_chain(
    *,
    summary_artifact: Mapping[str, Any],
    readiness_report: Mapping[str, Any],
    source_summary_path: str | Path | None = None,
    source_readiness_path: str | Path | None = None,
) -> dict[str, Any]:
    blockers = _preflight_blockers(summary_artifact, readiness_report)
    if blockers:
        return _artifact(
            status="blocked",
            blockers=blockers,
            summary_artifact=summary_artifact,
            readiness_report=readiness_report,
            integrated_chain=None,
            source_summary_path=source_summary_path,
            source_readiness_path=source_readiness_path,
        )

    payload = build_memory_record_chain_payload(summary_artifact)
    integrated_chain = run_advanced_shadow_e2e_fixture_chain(
        memory_summary_projection=payload["memory_summary_projection"],
        recommendation_payload=payload["recommendation_payload"],
        derived_memory_views=payload["derived_memory_views"],
        current_budget_view=payload["current_budget_view"],
        active_body_plan_view=payload["active_body_plan_view"],
        open_proposals_view=payload["open_proposals_view"],
        proposal_candidate_output=payload["proposal_candidate_output"],
        user_control_models=payload["user_control_models"],
        interaction_plan=payload["interaction_plan"],
    )
    return _artifact(
        status="pass" if integrated_chain.get("status") == "pass" else "blocked",
        blockers=[
            f"integrated_chain.{item}"
            for item in integrated_chain.get("blockers") or []
        ],
        summary_artifact=summary_artifact,
        readiness_report=readiness_report,
        integrated_chain=integrated_chain,
        source_summary_path=source_summary_path,
        source_readiness_path=source_readiness_path,
    )


def _artifact(
    *,
    status: str,
    blockers: list[str],
    summary_artifact: Mapping[str, Any],
    readiness_report: Mapping[str, Any],
    integrated_chain: Mapping[str, Any] | None,
    source_summary_path: str | Path | None,
    source_readiness_path: str | Path | None,
) -> dict[str, Any]:
    source_refs = _recommendation_source_refs(integrated_chain or {})
    return {
        "artifact_type": "advanced_product_lab_memory_record_integrated_e2e_artifact",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/product_lab_memory_record_integrated_e2e.py",
        "consumer": "advanced_product_lab_live_and_e2e_diagnostics",
        "retirement_trigger": "approved_advanced_product_lab_activation_plan",
        "source_summary_path": str(source_summary_path or ""),
        "source_readiness_path": str(source_readiness_path or ""),
        "source_summary_artifact_type": str(summary_artifact.get("artifact_type") or ""),
        "source_readiness_status": str(readiness_report.get("status") or ""),
        "source_memory_record_ids": memory_record_ids(summary_artifact),
        "memory_record_summary_drives_chain": bool(
            integrated_chain and source_refs
        ),
        "integrated_chain_artifact": dict(integrated_chain) if integrated_chain else None,
        "journey_terminal_evidence_count": len(
            (integrated_chain or {}).get("journey_terminal_evidence") or []
        ),
        "recommendation_selected_candidate_id": _selected_candidate_id(
            integrated_chain or {}
        ),
        "recommendation_source_refs_include_memory_records": bool(
            set(memory_record_ids(summary_artifact)) & _source_ref_ids(source_refs)
        ),
        "blockers": blockers,
        "lab_enabled": True,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _preflight_blockers(
    summary_artifact: Mapping[str, Any],
    readiness_report: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if readiness_report.get("status") != "pass":
        blockers.append(f"readiness_report.status_{readiness_report.get('status')}")
        blockers.extend(
            f"readiness_report.{item}"
            for item in readiness_report.get("blockers") or []
        )
    if summary_artifact.get("artifact_type") != (
        "advanced_product_lab_memory_record_dogfood_summary"
    ):
        blockers.append("summary_artifact.type_not_memory_record_dogfood")
    if not memory_record_ids(summary_artifact):
        blockers.append("summary_artifact.memory_record_ids_missing")
    return blockers


def _recommendation_source_refs(chain: Mapping[str, Any]) -> list[str]:
    stage = _stage(chain, "recommendation_three_node_shadow_artifact")
    offer = stage.get("shadow_offer_packet") if isinstance(stage, Mapping) else {}
    return [str(ref) for ref in (offer or {}).get("source_refs") or []]


def _selected_candidate_id(chain: Mapping[str, Any]) -> str:
    stage = _stage(chain, "recommendation_three_node_shadow_artifact")
    return str(stage.get("selected_candidate_id") or "") if isinstance(stage, Mapping) else ""


def _source_ref_ids(source_refs: list[str]) -> set[str]:
    return {ref.split(":", 1)[1] for ref in source_refs if ":" in ref}


def _stage(chain: Mapping[str, Any], artifact_type: str) -> Mapping[str, Any]:
    for item in chain.get("stage_artifacts") or []:
        if isinstance(item, Mapping) and item.get("artifact_type") == artifact_type:
            return item
    return {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "run_memory_record_integrated_e2e_chain",
]
