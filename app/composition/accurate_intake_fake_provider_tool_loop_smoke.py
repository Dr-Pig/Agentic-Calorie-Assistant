from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

FORBIDDEN_TRUE_CLAIMS = (
    "live_llm_invoked",
    "web_tavily_used",
    "fooddb_truth_updated",
    "real_fooddb_pass_claimed",
    "dogfood_pass",
    "product_readiness_claimed",
    "private_self_use_approved",
    "fixture_packet_truth",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


def _overclaim_blockers(artifact_id: str, payload: dict[str, Any]) -> list[str]:
    return [
        f"{artifact_id}.{flag}"
        for flag in FORBIDDEN_TRUE_CLAIMS
        if payload.get(flag) is True
    ]


def _manager_consumable_fixture_packets(packet_emulator: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(scenario)
        for scenario in list(packet_emulator.get("scenarios") or [])
        if isinstance(scenario, dict)
        and scenario.get("manager_consumable") is True
        and scenario.get("runtime_truth_allowed") is False
        and scenario.get("fixture_or_real") == "fixture"
    ]


def build_fake_provider_tool_loop_smoke_artifact(
    *,
    context_smoke: dict[str, Any],
    fixture_packet_emulator: dict[str, Any],
) -> dict[str, Any]:
    context = _object_dict(context_smoke)
    packets = _object_dict(fixture_packet_emulator)
    provider_input = _object_dict(context.get("provider_input_summary"))
    manager_consumable_packets = _manager_consumable_fixture_packets(packets)

    blockers: list[str] = []
    blockers.extend(_overclaim_blockers("context_smoke", context))
    blockers.extend(_overclaim_blockers("fixture_packet_emulator", packets))
    if _status(context) != "pass":
        blockers.append("context_smoke.not_pass")
    if _status(packets) != "fixture_packet_emulator_ready":
        blockers.append("fixture_packet_emulator.not_ready")
    if provider_input.get("context_policy_version_present") is not True:
        blockers.append("context_smoke.context_policy_version_missing")
    if provider_input.get("forbidden_context_excluded") is not True:
        blockers.append("context_smoke.forbidden_context_not_excluded")
    if not manager_consumable_packets:
        blockers.append("fixture_packet_emulator.no_manager_consumable_packets")
    if context.get("final_semantic_decision_source") != "fixture_manager_structured_decision":
        blockers.append("context_smoke.semantic_source_not_fixture_manager")
    if context.get("deterministic_semantic_inference_used") is not False:
        blockers.append("context_smoke.deterministic_semantic_inference")
    if context.get("raw_text_intent_router_used") is not False:
        blockers.append("context_smoke.raw_text_intent_router_used")

    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_fake_provider_tool_loop_smoke",
            "claim_scope": "fake_provider_context_and_fixture_packet_tool_loop_smoke",
            "status": "fake_provider_tool_loop_smoke_pass" if not blockers else "fail",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "blockers": blockers,
            "provider_mode": "fake_provider_contract_test",
            "provider_input_summary": {
                "context_policy_version_present": provider_input.get(
                    "context_policy_version_present"
                )
                is True,
                "loaded_context_summary_present": provider_input.get(
                    "loaded_context_summary_present"
                )
                is True,
                "omitted_context_summary_present": provider_input.get(
                    "omitted_context_summary_present"
                )
                is True,
                "forbidden_context_excluded": provider_input.get(
                    "forbidden_context_excluded"
                )
                is True,
                "fixture_evidence_packets_present": bool(manager_consumable_packets),
                "fixture_packet_scenario_ids": [
                    str(packet.get("scenario_id"))
                    for packet in manager_consumable_packets
                ],
            },
            "tool_loop_trace_attributable": True,
            "final_semantic_decision_source": "fixture_manager_structured_decision",
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "local_only": True,
            "diagnostic_only": True,
            "evidence_packet_truth": False,
            "fixture_evidence_used": True,
            "fooddb_evidence_used": False,
            "websearch_evidence_used": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_truth_updated": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        }
    )


__all__ = ["build_fake_provider_tool_loop_smoke_artifact"]
