from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.evidence_candidate_packetizer import (  # noqa: E402
    add_hard_recheck_metadata,
    build_candidate_packet,
)
from app.nutrition.application.evidence_packet_consumption import consume_rechecked_packets  # noqa: E402
from app.nutrition.application.exact_item_card_lookup import lookup_exact_item_card_candidates  # noqa: E402
from app.nutrition.application.final_mapping import map_final_item_result  # noqa: E402
from app.nutrition.application.local_synthesis import synthesize_local_manager_pass  # noqa: E402
from app.nutrition.application.packetizer_input_seed import (  # noqa: E402
    packetizer_input_seeds_from_anchor_lookup_result,
    packetizer_input_seeds_from_exact_item_lookup_result,
)
from app.nutrition.application.retrieval_intent import RetrievalIntent, build_diagnostic_retrieval_intent  # noqa: E402
from app.nutrition.application.small_anchor_store import lookup_anchor_candidates  # noqa: E402
from app.nutrition.application.synthesis_provider_bridge import (  # noqa: E402
    run_synthesis_manager_with_provider,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt10b_nutrition_estimate_quality_fake_provider.json"


class DeterministicFixturePass2Provider:
    """Fixture-only provider seam for RT10b."""

    def __init__(self, *, payload: dict[str, Any], trace: dict[str, Any] | None = None) -> None:
        self._payload = payload
        self._trace = trace or {}

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        trace = {
            "provider": "fixture",
            "model": "deterministic-pass2",
            "temperature": 0.0,
            "max_tokens": kwargs.get("max_tokens"),
            "response_format": {"type": "json_schema"},
            "timeout": None,
            "retry_policy": {"max_attempts": 1},
            "tool_choice": "none",
            "request_id": "rt10b-fake-provider",
        }
        trace.update(self._trace)
        return self._payload, trace


def _status(blockers: list[str]) -> str:
    return "pass" if not blockers else "fail"


def _anchor_case(message: str) -> tuple[Any, Any, Any]:
    intent = build_diagnostic_retrieval_intent(message)
    anchor_result = lookup_anchor_candidates(intent)
    packets = tuple(
        add_hard_recheck_metadata(build_candidate_packet(seed))
        for seed in packetizer_input_seeds_from_anchor_lookup_result(anchor_result)
    )
    consumption = consume_rechecked_packets(packets)
    return intent, consumption, anchor_result.clarify_support


def _clarify_case() -> tuple[Any, Any, Any]:
    intent = build_diagnostic_retrieval_intent("\u6211\u5403\u4e86\u6ef7\u5473")
    anchor_result = lookup_anchor_candidates(intent)
    return intent, consume_rechecked_packets(()), anchor_result.clarify_support


def _exact_case(message: str) -> tuple[Any, Any, Any]:
    intent = build_diagnostic_retrieval_intent(message)
    exact_result = lookup_exact_item_card_candidates(intent)
    packets = tuple(
        add_hard_recheck_metadata(build_candidate_packet(seed))
        for seed in packetizer_input_seeds_from_exact_item_lookup_result(exact_result)
    )
    return intent, consume_rechecked_packets(packets), None


def _listed_component_case(item_name: str) -> tuple[Any, Any, Any]:
    intent = RetrievalIntent(
        base_dish="\u6ef7\u5473",
        aliases=[],
        brand_hint=None,
        size_hint=None,
        modifier_hints=[],
        listed_items=[item_name],
        retrieval_goal="listed_item_lookup",
    )
    anchor_result = lookup_anchor_candidates(intent)
    packet = add_hard_recheck_metadata(
        build_candidate_packet(packetizer_input_seeds_from_anchor_lookup_result(anchor_result)[0])
    )
    return intent, consume_rechecked_packets((packet,)), anchor_result.clarify_support


def _mapping_for_provider_item(item: dict[str, Any]) -> dict[str, Any]:
    return map_final_item_result(
        item,
        canonical_write_decision={"can_write_canonical": True},
        interaction_type="food_logging",
    )


def _semantic_blockers(
    *,
    family: str,
    local_item: dict[str, Any],
    provider_item: dict[str, Any],
    provider_mapping: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if provider_item.get("exactness_posture") != local_item.get("exactness_posture"):
        blockers.append("exactness_posture_drift")
    if provider_item.get("likely_kcal") != local_item.get("likely_kcal"):
        blockers.append("likely_kcal_drift")
    if provider_item.get("suggested_followup_question") != local_item.get("suggested_followup_question"):
        blockers.append("followup_question_drift")

    if family == "exact_item":
        if provider_item.get("exactness_posture") != "exact":
            blockers.append("exact_item_not_exact")
        if provider_mapping.get("external_outcome") != "logged":
            blockers.append("exact_item_not_logged")
    elif family == "generic_common_food":
        if provider_item.get("exactness_posture") != "estimated":
            blockers.append("generic_item_not_estimated")
        if provider_mapping.get("external_outcome") != "logged":
            blockers.append("generic_item_not_logged")
    elif family == "optional_refinement":
        if provider_mapping.get("external_outcome") != "logged":
            blockers.append("optional_refinement_not_logged")
        if provider_mapping.get("followup_role") != "precision_refinement":
            blockers.append("optional_refinement_followup_role_mismatch")
    elif family == "blocking_clarify":
        if provider_item.get("exactness_posture") != "unresolved":
            blockers.append("blocking_clarify_not_unresolved")
        if provider_mapping.get("external_outcome") != "draft":
            blockers.append("blocking_clarify_not_draft")
        if provider_mapping.get("ledger_status") != "excluded_pending_info":
            blockers.append("blocking_clarify_ledger_status_mismatch")
    elif family == "listed_component":
        if provider_item.get("assumed_composition") != "listed item":
            blockers.append("listed_component_grounding_mismatch")
        if provider_mapping.get("external_outcome") != "logged":
            blockers.append("listed_component_not_logged")
    return blockers


async def _provider_case(
    *,
    case_id: str,
    family: str,
    case_factory: Any,
    provider_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    intent, consumption, clarify_support = case_factory()
    local_result = synthesize_local_manager_pass(
        intent,
        consumption,
        clarify_support=clarify_support,
    )
    local_item = dict(local_result["item_results"][0])
    provider = DeterministicFixturePass2Provider(
        payload=provider_payload or {"item_results": local_result["item_results"]},
    )
    provider_result = await run_synthesis_manager_with_provider(
        provider,
        intent,
        consumption,
        clarify_support=clarify_support,
    )
    provider_item = dict(provider_result["item_results"][0]) if provider_result["item_results"] else {}
    provider_mapping = _mapping_for_provider_item(provider_item) if provider_item else {}

    blockers: list[str] = []
    if provider_result.get("payload_shape_valid") is not True:
        blockers.append("payload_shape_invalid")
    if provider_result.get("item_results_source") != "manager_pass_2_payload":
        blockers.append("item_results_source_drift")
    if provider_result.get("item_results_owner_class") != "runtime_payload":
        blockers.append("item_results_owner_class_drift")
    if provider_result.get("forbidden_mutation_fields_present") != []:
        blockers.append("forbidden_mutation_fields_present")
    if not provider_item:
        blockers.append("provider_item_results_missing")
    else:
        blockers.extend(
            _semantic_blockers(
                family=family,
                local_item=local_item,
                provider_item=provider_item,
                provider_mapping=provider_mapping,
            )
        )

    return {
        "case_id": case_id,
        "family": family,
        "status": _status(blockers),
        "blockers": blockers,
        "provider_params": provider_result.get("provider_params"),
        "payload_shape_valid": provider_result.get("payload_shape_valid"),
        "item_results_source": provider_result.get("item_results_source"),
        "item_results_owner_class": provider_result.get("item_results_owner_class"),
        "forbidden_mutation_fields_present": provider_result.get("forbidden_mutation_fields_present"),
        "local_exactness_posture": local_item.get("exactness_posture"),
        "provider_exactness_posture": provider_item.get("exactness_posture"),
        "local_likely_kcal": local_item.get("likely_kcal"),
        "provider_likely_kcal": provider_item.get("likely_kcal"),
        "provider_mapping_external_outcome": provider_mapping.get("external_outcome"),
    }


async def build_rt10b_nutrition_estimate_quality_fake_provider_artifact(
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    cases = [
        await _provider_case(
            case_id="exact_item_provider_keeps_exact_posture",
            family="exact_item",
            case_factory=lambda: _exact_case("\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f"),
        ),
        await _provider_case(
            case_id="generic_item_provider_keeps_honest_estimate",
            family="generic_common_food",
            case_factory=lambda: _anchor_case("\u6211\u5403\u4e86\u8336\u8449\u86cb"),
        ),
        await _provider_case(
            case_id="optional_refinement_provider_keeps_refinement_posture",
            family="optional_refinement",
            case_factory=lambda: _anchor_case("\u6211\u559d\u4e86\u73cd\u73e0\u5976\u8336"),
        ),
        await _provider_case(
            case_id="blocking_clarify_provider_keeps_unresolved_posture",
            family="blocking_clarify",
            case_factory=_clarify_case,
        ),
        await _provider_case(
            case_id="listed_component_provider_keeps_component_grounding",
            family="listed_component",
            case_factory=lambda: _listed_component_case("\u8c46\u5e72"),
        ),
    ]
    blockers = [f"{case['case_id']}.{blocker}" for case in cases for blocker in case["blockers"]]
    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return {
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output_path.name,
        "artifact_path": str(resolved_output_path),
        "claim_scope": "fake_provider_nutrition_quality_gate",
        "launch_scope": "current_shell_v1",
        "producer_track": "CurrentShell/ManagerRuntime",
        "target_manager_runtime_gate": "rt10b_nutrition_estimate_quality_fake_provider",
        "pass_type": "fixture",
        "runtime_backed": False,
        "live_llm_invoked": False,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "supports_journeys": ["B", "C", "D"],
        "status": _status(blockers),
        "blockers": blockers,
        "summary": {
            "case_count": len(cases),
            "passed_case_count": sum(1 for case in cases if case["status"] == "pass"),
        },
        "cases": cases,
        "best_practice_basis": {
            "fake_provider_role": "offline provider seam validation before live diagnostics",
            "semantic_owner": "local manager reference plus provider pass-2 payload parity",
            "forbidden": "provider payload may not claim mutation authority or drift nutrition posture",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the RT10b fake-provider nutrition estimate quality artifact."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to write the JSON artifact.",
    )
    args = parser.parse_args(argv)
    artifact = asyncio.run(
        build_rt10b_nutrition_estimate_quality_fake_provider_artifact(output_path=args.output)
    )
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
