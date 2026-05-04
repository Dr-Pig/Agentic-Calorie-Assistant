from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _base_scenarios() -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": "approved_common_serving_anchor_fixture",
            "source_family": "fooddb_fixture",
            "packet_status": "approved_anchor_shape_fixture",
            "fixture_or_real": "fixture",
            "runtime_truth_allowed": False,
            "manager_consumable": True,
            "product_loop_consumption": "diagnostic_only",
            "requires_human_approval": False,
        },
        {
            "scenario_id": "approved_exact_card_fixture",
            "source_family": "fooddb_fixture",
            "packet_status": "approved_exact_card_shape_fixture",
            "fixture_or_real": "fixture",
            "runtime_truth_allowed": False,
            "manager_consumable": True,
            "product_loop_consumption": "diagnostic_only",
            "requires_human_approval": False,
        },
        {
            "scenario_id": "missing_evidence",
            "source_family": "fooddb_fixture",
            "packet_status": "missing_evidence",
            "fixture_or_real": "fixture",
            "runtime_truth_allowed": False,
            "manager_consumable": True,
            "product_loop_consumption": "diagnostic_only",
            "requires_human_approval": False,
        },
        {
            "scenario_id": "ambiguous_candidates",
            "source_family": "fooddb_fixture",
            "packet_status": "ambiguous_candidates",
            "fixture_or_real": "fixture",
            "runtime_truth_allowed": False,
            "manager_consumable": True,
            "product_loop_consumption": "diagnostic_only",
            "requires_human_approval": False,
        },
        {
            "scenario_id": "rejected_validator_only_source",
            "source_family": "fooddb_fixture",
            "packet_status": "rejected_validator_only",
            "fixture_or_real": "fixture",
            "runtime_truth_allowed": False,
            "manager_consumable": False,
            "product_loop_consumption": "diagnostic_only",
            "requires_human_approval": True,
        },
        {
            "scenario_id": "websearch_candidate_not_approved",
            "source_family": "websearch_fixture",
            "packet_status": "candidate_not_approved",
            "fixture_or_real": "fixture",
            "runtime_truth_allowed": False,
            "manager_consumable": False,
            "product_loop_consumption": "diagnostic_only",
            "requires_human_approval": True,
            "web_tavily_used": False,
        },
    ]


def _apply_overrides(
    scenarios: list[dict[str, Any]],
    overrides: dict[str, dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    by_id = {scenario["scenario_id"]: dict(scenario) for scenario in scenarios}
    for scenario_id, override in dict(overrides or {}).items():
        if scenario_id in by_id:
            by_id[scenario_id].update(dict(override))
    return [by_id[str(scenario["scenario_id"])] for scenario in scenarios]


def _scenario_blockers(scenario: dict[str, Any]) -> list[str]:
    scenario_id = str(scenario.get("scenario_id") or "unknown")
    blockers: list[str] = []
    if scenario.get("fixture_or_real") != "fixture":
        blockers.append(f"{scenario_id}.fixture_or_real")
    if scenario.get("runtime_truth_allowed") is not False:
        blockers.append(f"{scenario_id}.runtime_truth_allowed")
    if scenario.get("product_loop_consumption") != "diagnostic_only":
        blockers.append(f"{scenario_id}.product_loop_consumption")
    if scenario.get("source_family") == "websearch_fixture" and scenario.get("web_tavily_used") is not False:
        blockers.append(f"{scenario_id}.web_tavily_used")
    return blockers


def build_fixture_evidence_packet_emulator_artifact(
    *,
    overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    scenarios = _apply_overrides(_base_scenarios(), overrides)
    blockers = [
        blocker
        for scenario in scenarios
        for blocker in _scenario_blockers(scenario)
    ]
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_fixture_evidence_packet_emulator",
            "claim_scope": "fixture_evidence_packet_shape_diagnostic",
            "status": "fixture_packet_emulator_ready" if not blockers else "fail",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "blockers": blockers,
            "scenario_ids": [str(scenario["scenario_id"]) for scenario in scenarios],
            "scenarios": scenarios,
            "local_only": True,
            "diagnostic_only": True,
            "fixture_evidence_used": True,
            "fixture_packet_truth": False,
            "fooddb_evidence_used": False,
            "websearch_evidence_used": False,
            "web_tavily_used": False,
            "raw_sources_read": False,
            "promotion_policy_changed": False,
            "shared_contract_changed": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "fooddb_truth_updated": False,
            "ready_for_fdb_integration": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "live_llm_invoked": False,
        }
    )


__all__ = ["build_fixture_evidence_packet_emulator_artifact"]
