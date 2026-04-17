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
)


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


def test_workflow_official_packs_are_promoted_canonical_artifacts() -> None:
    for pack_path, expected_pack_id in (
        (INTAKE_OFFICIAL_PACK_PATH, "intake_official_canonical_pack_v1"),
        (RESCUE_OFFICIAL_PACK_PATH, "rescue_official_canonical_pack_v1"),
    ):
        payload = _load_json(pack_path)
        assert payload["pack_id"] == expected_pack_id
        assert payload["pack_mode"] == "official_canonical"
        assert payload["authority_level"] == "canonical"
        assert payload["approval_status"] == "batch_1_approved"
        assert payload["canonical_primary_oracle_fields"] == [
            "expected_target_object_type",
            "expected_target_workflow_family",
            "expected_disposition",
            "expected_workflow_effect",
        ]
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


def test_suite_promotion_contract_passes_for_intake_and_rescue() -> None:
    assert check_suite_promotion_contract.main() == 0
