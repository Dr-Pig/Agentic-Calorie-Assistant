from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.intake_manager_tool_batch import macro_summary  # noqa: E402
from app.composition.payload_builders import build_payload  # noqa: E402
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
from app.nutrition.application.retrieval_intent import RetrievalIntent, build_retrieval_intent  # noqa: E402
from app.nutrition.application.small_anchor_store import lookup_anchor_candidates  # noqa: E402
from app.schemas import EstimateRequest  # noqa: E402
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt10a_nutrition_estimate_quality_deterministic.json"


def _anchor_item_for_logging(user_input: str) -> tuple[dict[str, Any], dict[str, Any]]:
    intent = build_retrieval_intent(user_input)
    anchor_result = lookup_anchor_candidates(intent)
    packets = tuple(
        add_hard_recheck_metadata(build_candidate_packet(seed))
        for seed in packetizer_input_seeds_from_anchor_lookup_result(anchor_result)
    )
    consumption = consume_rechecked_packets(packets)
    manager_pass = synthesize_local_manager_pass(
        intent,
        consumption,
        clarify_support=anchor_result.clarify_support,
    )
    item = manager_pass["item_results"][0]
    mapping = map_final_item_result(
        item,
        canonical_write_decision={"can_write_canonical": True},
        interaction_type="food_logging",
    )
    return item, mapping


def _blocking_clarify_item(user_input: str) -> tuple[dict[str, Any], dict[str, Any]]:
    intent = build_retrieval_intent(user_input)
    anchor_result = lookup_anchor_candidates(intent)
    manager_pass = synthesize_local_manager_pass(
        intent,
        consume_rechecked_packets(()),
        clarify_support=anchor_result.clarify_support,
    )
    item = manager_pass["item_results"][0]
    mapping = map_final_item_result(
        item,
        canonical_write_decision={"can_write_canonical": True},
        interaction_type="food_logging",
    )
    return item, mapping


def _exact_item_for_logging(user_input: str) -> tuple[dict[str, Any], dict[str, Any]]:
    intent = build_retrieval_intent(user_input)
    exact_result = lookup_exact_item_card_candidates(intent)
    packets = tuple(
        add_hard_recheck_metadata(build_candidate_packet(seed))
        for seed in packetizer_input_seeds_from_exact_item_lookup_result(exact_result)
    )
    consumption = consume_rechecked_packets(packets)
    manager_pass = synthesize_local_manager_pass(intent, consumption)
    item = manager_pass["item_results"][0]
    mapping = map_final_item_result(
        item,
        canonical_write_decision={"can_write_canonical": True},
        interaction_type="food_logging",
    )
    return item, mapping


def _listed_component_for_logging(item_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
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
    consumption = consume_rechecked_packets((packet,))
    manager_pass = synthesize_local_manager_pass(intent, consumption)
    item = manager_pass["item_results"][0]
    mapping = map_final_item_result(
        item,
        canonical_write_decision={"can_write_canonical": True},
        interaction_type="food_logging",
    )
    return item, mapping


def _macro_payload_summary(*, explicit_display: bool) -> dict[str, Any]:
    parsed: dict[str, Any] = {
        "title": "pearl milk tea",
        "components": ["milk tea", "pearls"],
        "protein_g": 3,
        "carb_g": 80,
        "fat_g": 8,
        "estimated_kcal": 450,
        "uncertainty_factors": ["size and sugar unknown"],
        "followup_question": "What size and sugar level was it?",
        "follow_up_needed": True,
        "response_mode_hint": "rough_estimate_ok",
        "unresolved_info": [],
        "blocking_slots": [],
    }
    if explicit_display:
        parsed["answer_payload"] = {
            "display_macro_breakdown": {
                "protein_g": 20,
                "carb_g": 50,
                "fat_g": 18,
                "macro_source": "derived_consistent",
            }
        }
    payload = build_payload(
        EstimateRequest(text="I had a pearl milk tea"),
        request_id="rt10a-macro",
        parsed=parsed,
        risk_packet={},
        action_taken="answer_with_uncertainty",
        route_target="direct_answer",
        route_reason="manager_estimate_with_refinement",
        debug_steps=[],
        llm_traces=[],
        retrieval_triggered=False,
        retrieval_query=None,
        retrieved_knowledge=[],
        quality_signals={},
        retry_triggered=False,
        retry_reason=None,
        best_answer_source="llm",
        private_only=False,
        used_search=False,
        search_query=None,
        search_quality=None,
        sources=[],
    )
    return macro_summary(payload)


def _status(blockers: list[str]) -> str:
    return "pass" if not blockers else "fail"


def build_rt10a_nutrition_estimate_quality_deterministic_artifact(
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    exact_item, exact_mapping = _exact_item_for_logging("\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f")
    exact_blockers: list[str] = []
    if exact_item["exactness_posture"] != "exact":
        exact_blockers.append("exact_item.not_exact")
    if exact_item["likely_kcal"] != 154.0:
        exact_blockers.append("exact_item.kcal_mismatch")
    if exact_item["suggested_followup_question"] is not None:
        exact_blockers.append("exact_item.followup_present")
    if exact_mapping["external_outcome"] != "logged":
        exact_blockers.append("exact_item.not_loggable")

    generic_item, generic_mapping = _anchor_item_for_logging("\u6211\u5403\u4e86\u8336\u8449\u86cb")
    generic_blockers: list[str] = []
    if generic_item["exactness_posture"] != "estimated":
        generic_blockers.append("generic_item.not_estimated")
    if generic_item["likely_kcal"] is None:
        generic_blockers.append("generic_item.missing_kcal")
    if generic_item["suggested_followup_question"] is not None:
        generic_blockers.append("generic_item.unexpected_followup")
    if generic_mapping["external_outcome"] != "logged":
        generic_blockers.append("generic_item.not_loggable")

    refinement_item, refinement_mapping = _anchor_item_for_logging("\u6211\u559d\u4e86\u73cd\u73e0\u5976\u8336")
    refinement_blockers: list[str] = []
    if refinement_item["exactness_posture"] != "estimated":
        refinement_blockers.append("optional_refinement.not_estimated")
    if not refinement_item["suggested_followup_question"]:
        refinement_blockers.append("optional_refinement.missing_followup")
    if refinement_mapping["external_outcome"] != "logged":
        refinement_blockers.append("optional_refinement.not_logged")
    if refinement_mapping["followup_role"] != "precision_refinement":
        refinement_blockers.append("optional_refinement.followup_role_mismatch")

    clarify_item, clarify_mapping = _blocking_clarify_item("\u6211\u5403\u4e86\u6ef7\u5473")
    clarify_blockers: list[str] = []
    if clarify_item["exactness_posture"] != "unresolved":
        clarify_blockers.append("blocking_clarify.not_unresolved")
    if clarify_item["likely_kcal"] is not None:
        clarify_blockers.append("blocking_clarify.kcal_present")
    if not clarify_item["suggested_followup_question"]:
        clarify_blockers.append("blocking_clarify.missing_followup")
    if clarify_mapping["external_outcome"] != "draft":
        clarify_blockers.append("blocking_clarify.not_draft")
    if clarify_mapping["ledger_status"] != "excluded_pending_info":
        clarify_blockers.append("blocking_clarify.ledger_status_mismatch")

    listed_item, listed_mapping = _listed_component_for_logging("\u8c46\u5e72")
    listed_blockers: list[str] = []
    if listed_item["assumed_composition"] != "listed item":
        listed_blockers.append("listed_component.composition_mismatch")
    if listed_item["exactness_posture"] != "estimated":
        listed_blockers.append("listed_component.not_estimated")
    if listed_mapping["external_outcome"] != "logged":
        listed_blockers.append("listed_component.not_logged")

    macro_hidden = _macro_payload_summary(explicit_display=False)
    macro_visible = _macro_payload_summary(explicit_display=True)
    macro_blockers: list[str] = []
    if macro_hidden["display_status"] != "hide":
        macro_blockers.append("macro_hidden.visibility_mismatch")
    if macro_hidden["guard_reason"] != "no_macro_data":
        macro_blockers.append("macro_hidden.guard_reason_mismatch")
    if macro_visible["display_status"] != "show":
        macro_blockers.append("macro_visible.visibility_mismatch")
    if macro_visible["guard_reason"] != "committed_and_aligned":
        macro_blockers.append("macro_visible.guard_reason_mismatch")

    cases = [
        {
            "case_id": "exact_item_keeps_exact_posture_with_official_card",
            "family": "exact_item",
            "status": _status(exact_blockers),
            "blockers": exact_blockers,
            "exactness_posture": exact_item["exactness_posture"],
            "likely_kcal": exact_item["likely_kcal"],
            "kcal_range": exact_item["kcal_range"],
            "mapping_external_outcome": exact_mapping["external_outcome"],
        },
        {
            "case_id": "generic_single_item_uses_honest_estimate_not_fake_exactness",
            "family": "generic_common_food",
            "status": _status(generic_blockers),
            "blockers": generic_blockers,
            "exactness_posture": generic_item["exactness_posture"],
            "likely_kcal": generic_item["likely_kcal"],
            "suggested_followup_question": generic_item["suggested_followup_question"],
            "mapping_external_outcome": generic_mapping["external_outcome"],
        },
        {
            "case_id": "optional_refinement_commits_estimate_and_keeps_refinement_posture",
            "family": "optional_refinement",
            "status": _status(refinement_blockers),
            "blockers": refinement_blockers,
            "exactness_posture": refinement_item["exactness_posture"],
            "suggested_followup_question": refinement_item["suggested_followup_question"],
            "followup_role": refinement_mapping["followup_role"],
            "mapping_external_outcome": refinement_mapping["external_outcome"],
        },
        {
            "case_id": "blocking_clarify_stays_unresolved_without_canonical_truth",
            "family": "blocking_clarify",
            "status": _status(clarify_blockers),
            "blockers": clarify_blockers,
            "exactness_posture": clarify_item["exactness_posture"],
            "likely_kcal": clarify_item["likely_kcal"],
            "suggested_followup_question": clarify_item["suggested_followup_question"],
            "mapping_external_outcome": clarify_mapping["external_outcome"],
            "ledger_status": clarify_mapping["ledger_status"],
        },
        {
            "case_id": "listed_component_estimate_remains_component_grounded",
            "family": "listed_component",
            "status": _status(listed_blockers),
            "blockers": listed_blockers,
            "assumed_composition": listed_item["assumed_composition"],
            "exactness_posture": listed_item["exactness_posture"],
            "mapping_external_outcome": listed_mapping["external_outcome"],
        },
        {
            "case_id": "macro_visibility_stays_honest_when_display_data_is_missing_or_explicit",
            "family": "macro_visibility",
            "status": _status(macro_blockers),
            "blockers": macro_blockers,
            "hidden_display_status": macro_hidden["display_status"],
            "hidden_guard_reason": macro_hidden["guard_reason"],
            "visible_display_status": macro_visible["display_status"],
            "visible_guard_reason": macro_visible["guard_reason"],
        },
    ]
    passed_case_count = sum(1 for case in cases if case["status"] == "pass")
    blockers = [f"{case['case_id']}.{blocker}" for case in cases for blocker in case["blockers"]]
    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return {
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output_path.name,
        "artifact_path": str(resolved_output_path),
        "claim_scope": "deterministic_nutrition_quality_gate",
        "launch_scope": "current_shell_v1",
        "producer_track": "CurrentShell/ManagerRuntime",
        "target_manager_runtime_gate": "rt10a_nutrition_estimate_quality_deterministic",
        "pass_type": "fixture",
        "runtime_backed": False,
        "live_llm_invoked": False,
        "web_tavily_invoked": False,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "supports_journeys": ["B", "C", "D"],
        "status": _status(blockers),
        "blockers": blockers,
        "summary": {
            "case_count": len(cases),
            "passed_case_count": passed_case_count,
        },
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the RT10a deterministic nutrition estimate quality artifact."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to write the JSON artifact.",
    )
    args = parser.parse_args(argv)
    artifact = build_rt10a_nutrition_estimate_quality_deterministic_artifact(output_path=args.output)
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
