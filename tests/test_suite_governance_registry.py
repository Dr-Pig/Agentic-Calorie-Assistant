from __future__ import annotations

import json
from pathlib import Path

from scripts import check_suite_promotion_contract


ROOT = Path(__file__).resolve().parents[1]
RUNNER_REGISTRY_PATH = ROOT / "docs" / "quality" / "AUDIT_RUNNER_REGISTRY.json"
FIXTURE_REGISTRY_PATH = ROOT / "docs" / "quality" / "AUDIT_FIXTURE_REGISTRY.json"
INTAKE_OFFICIAL_PACK_PATH = (
    ROOT
    / "docs"
    / "quality"
    / "benchmarks"
    / "intake"
    / "intake_official_canonical_pack_v1.json"
)
RESCUE_OFFICIAL_PACK_PATH = (
    ROOT
    / "docs"
    / "quality"
    / "benchmarks"
    / "rescue"
    / "rescue_official_canonical_pack_v1.json"
)
GENERAL_CHAT_OFFICIAL_PACK_PATH = (
    ROOT
    / "docs"
    / "quality"
    / "benchmarks"
    / "general_chat"
    / "general_chat_official_canonical_pack_v1.json"
)
BODY_OBSERVATION_OFFICIAL_PACK_PATH = (
    ROOT
    / "docs"
    / "quality"
    / "benchmarks"
    / "body_observation"
    / "body_observation_official_canonical_pack_v1.json"
)
AGENT_ALLOWED_PACKS = (
    (
        ROOT
        / "docs"
        / "quality"
        / "benchmarks"
        / "retrieval"
        / "retrieval_candidate_selection_golden_v1.json",
        "retrieval_candidate_selection_golden_v1",
        "capability_service",
    ),
    (
        ROOT
        / "docs"
        / "quality"
        / "benchmarks"
        / "context"
        / "context_packing_sufficiency_golden_v1.json",
        "context_packing_sufficiency_golden_v1",
        "capability_service",
    ),
    (
        ROOT
        / "docs"
        / "quality"
        / "benchmarks"
        / "fallback"
        / "bounded_repair_gate_golden_v1.json",
        "bounded_repair_gate_golden_v1",
        "capability_service",
    ),
)

ALLOWED_AUTHORITY_TIERS = {
    "Official Golden",
    "Provisional Exploratory",
    "Smoke / Infra",
}
ALLOWED_VALIDATION_LAYERS = {
    "workflow_canonical_action",
    "pass_or_node_decision",
    "cross_turn_progression",
    "cross_workflow_boundary",
    "capability_service",
    "response_contract",
    "degraded_or_fallback",
    "smoke_infra",
}
REQUIRED_METADATA_FIELDS = (
    "suite_id",
    "authority_tier",
    "workflow_family",
    "capability_family",
    "validation_layer",
    "suite_archetype",
    "approval_mode",
    "truth_source",
)
ALLOWED_SUITE_ARCHETYPES = {
    "utterance_governed",
    "executable_workflow",
    "capability_service",
}
ALLOWED_APPROVAL_MODES = {
    "user_required",
    "agent_allowed",
}
ALLOWED_TRUTH_SOURCES = {
    "product_semantic_decision",
    "canonical_spec_derivation",
    "runtime_contract_derivation",
}


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def test_audit_registries_include_l5d_metadata() -> None:
    for registry_path in (RUNNER_REGISTRY_PATH, FIXTURE_REGISTRY_PATH):
        payload = _load_json(registry_path)
        assert isinstance(payload, list)
        assert payload

        seen_paths: set[str] = set()
        for entry in payload:
            assert isinstance(entry, dict)
            path = entry["path"]
            assert path not in seen_paths
            seen_paths.add(path)

            for field in REQUIRED_METADATA_FIELDS:
                assert isinstance(entry[field], str)
                assert entry[field]

            assert entry["authority_tier"] in ALLOWED_AUTHORITY_TIERS
            assert entry["validation_layer"] in ALLOWED_VALIDATION_LAYERS
            assert entry["suite_archetype"] in ALLOWED_SUITE_ARCHETYPES
            assert entry["approval_mode"] in ALLOWED_APPROVAL_MODES
            assert entry["truth_source"] in ALLOWED_TRUTH_SOURCES


def test_workflow_official_packs_are_promoted_canonical_artifacts() -> None:
    for pack_path, expected_pack_id in (
        (INTAKE_OFFICIAL_PACK_PATH, "intake_official_canonical_pack_v1"),
        (GENERAL_CHAT_OFFICIAL_PACK_PATH, "general_chat_official_canonical_pack_v1"),
        (BODY_OBSERVATION_OFFICIAL_PACK_PATH, "body_observation_official_canonical_pack_v1"),
        (RESCUE_OFFICIAL_PACK_PATH, "rescue_official_canonical_pack_v1"),
    ):
        payload = _load_json(pack_path)
        assert payload["pack_id"] == expected_pack_id
        assert payload["pack_mode"] == "official_canonical"
        assert payload["authority_level"] == "canonical"
        assert payload["approval_status"] in {"batch_1_approved", "batch_2_approved"}
        assert payload["suite_archetype"] == "utterance_governed"
        assert payload["approval_mode"] == "user_required"
        assert payload["truth_source"] == "product_semantic_decision"
        canonical_primary_oracle_fields = payload["canonical_primary_oracle_fields"]
        assert canonical_primary_oracle_fields in (
            [
                "expected_target_object_type",
                "expected_target_workflow_family",
                "expected_disposition",
                "expected_workflow_effect",
            ],
            [
                "expected_target_object_type",
                "expected_target_workflow_family",
                "expected_disposition",
                "expected_workflow_effect",
                "expected_observation_action",
            ],
            [
                "expected_target_object_type",
                "expected_target_workflow_family",
                "expected_disposition",
                "expected_workflow_effect",
                "expected_adjust_direction",
            ],
            [
                "expected_target_object_type",
                "expected_target_workflow_family",
                "expected_disposition",
                "expected_workflow_effect",
                "expected_required_read_surfaces",
            ],
        )
        assert payload["cases"]
        for case in payload["cases"]:
            assert case["suite_id"]
            assert case["promoted_from_candidate_case_id"]
            assert case["expected_target_object_type"] in {"meal_thread", "proposal", "body_observation", "none"}
            assert case["expected_target_workflow_family"] in {
                "intake",
                "rescue",
                "calibration",
                "recommendation",
                "body_observation",
                "general_chat",
            }
            assert case["expected_disposition"] in {
                "create",
                "continue",
                "correct",
                "accept",
                "reject",
                "defer",
                "adjust",
                "answer_only",
                "open_new_workflow",
            }
            assert case["expected_workflow_effect"]
            if "expected_required_read_surfaces" in case:
                assert isinstance(case["expected_required_read_surfaces"], list)
                assert all(isinstance(item, str) for item in case["expected_required_read_surfaces"])
            if "expected_meal_link_action" in case:
                assert case["expected_meal_link_action"] in {"link_existing_thread", "create_new_meal"}
            if "expected_decision_next_action" in case:
                assert case["expected_decision_next_action"] in {
                    "run_clarify",
                    "run_tool_lookup",
                    "run_nutrition_resolution",
                }
            if "expected_commit_posture" in case:
                assert case["expected_commit_posture"] in {"commit", "no_commit"}
            if "expected_observation_action" in case:
                assert case["expected_observation_action"] in {
                    "create_observation",
                    "answer_existing_state",
                    "handoff_to_calibration",
                }
            if "expected_adjust_direction" in case:
                assert case["expected_disposition"] == "adjust"
                assert case["expected_adjust_direction"] in {"shorter", "longer"}
            if "expected_special_posture" in case:
                assert case["expected_special_posture"] in {"logging_first", "escalate", "standard_spread"}


def test_suite_promotion_contract_passes_for_intake_and_rescue() -> None:
    assert check_suite_promotion_contract.main() == 0


def test_agent_allowed_official_packs_are_non_semantic_derivations() -> None:
    for pack_path, expected_pack_id, expected_archetype in AGENT_ALLOWED_PACKS:
        payload = _load_json(pack_path)
        assert payload["pack_id"] == expected_pack_id
        assert payload["pack_mode"] == "official_canonical"
        assert payload["authority_level"] == "canonical"
        assert payload["approval_mode"] == "agent_allowed"
        assert payload["truth_source"] == "canonical_spec_derivation"
        assert payload["suite_archetype"] == expected_archetype
        assert payload["approval_status"] == "agent_promoted_v1"
        assert payload["cases"]
        for case in payload["cases"]:
            assert not case.get("promoted_from_candidate_case_id")
            assert isinstance(case["derivation_basis"], list)
            assert case["derivation_basis"]
            assert isinstance(case["expected_service_outcome"], dict)
            assert case["expected_service_outcome"]
