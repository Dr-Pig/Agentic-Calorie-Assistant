from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

PROMOTION_PAIRS = (
    {
        "queue_path": ROOT / "docs" / "quality" / "benchmarks" / "intake" / "intake_candidate_review_queue_v1.json",
        "official_pack_path": ROOT / "docs" / "quality" / "benchmarks" / "intake" / "intake_official_canonical_pack_v1.json",
    },
    {
        "queue_path": ROOT / "docs" / "quality" / "benchmarks" / "general_chat" / "general_chat_candidate_review_queue_v1.json",
        "official_pack_path": ROOT / "docs" / "quality" / "benchmarks" / "general_chat" / "general_chat_official_canonical_pack_v1.json",
    },
    {
        "queue_path": ROOT / "docs" / "quality" / "benchmarks" / "rescue" / "rescue_candidate_review_queue_v1.json",
        "official_pack_path": ROOT / "docs" / "quality" / "benchmarks" / "rescue" / "rescue_official_canonical_pack_v1.json",
    },
    {
        "queue_path": ROOT / "docs" / "quality" / "benchmarks" / "body_observation" / "body_observation_candidate_review_queue_v1.json",
        "official_pack_path": ROOT / "docs" / "quality" / "benchmarks" / "body_observation" / "body_observation_official_canonical_pack_v1.json",
    },
)
AGENT_ALLOWED_OFFICIAL_PACKS = (
    ROOT / "docs" / "quality" / "benchmarks" / "retrieval" / "retrieval_candidate_selection_golden_v1.json",
    ROOT / "docs" / "quality" / "benchmarks" / "context" / "context_packing_sufficiency_golden_v1.json",
    ROOT / "docs" / "quality" / "benchmarks" / "fallback" / "bounded_repair_gate_golden_v1.json",
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


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing artifact: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"artifact must be a JSON object: {path}")
    return payload


def _validate_queue(queue_payload: dict[str, Any], *, path: Path) -> dict[str, dict[str, Any]]:
    if queue_payload.get("authority_level") != "candidate_only":
        raise ValueError(f"{path} must use authority_level=candidate_only")
    if queue_payload.get("review_unit") != "per_case_primary_outcome":
        raise ValueError(f"{path} must use review_unit=per_case_primary_outcome")
    if queue_payload.get("suite_archetype") != "utterance_governed":
        raise ValueError(f"{path} must use suite_archetype=utterance_governed")
    if queue_payload.get("approval_mode") != "user_required":
        raise ValueError(f"{path} must use approval_mode=user_required")
    if queue_payload.get("truth_source") != "product_semantic_decision":
        raise ValueError(f"{path} must use truth_source=product_semantic_decision")

    cases = queue_payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{path} must contain a non-empty cases list")

    normalized: dict[str, dict[str, Any]] = {}
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError(f"{path} contains a non-object case entry")
        case_id = case.get("candidate_case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"{path} contains a case missing candidate_case_id")
        if case_id in normalized:
            raise ValueError(f"{path} contains duplicate candidate_case_id: {case_id}")

        review_status = case.get("review_status")
        if review_status not in {"pending_user_approval", "approved_for_promotion"}:
            raise ValueError(f"{path} case {case_id} has unsupported review_status: {review_status}")

        if review_status == "approved_for_promotion":
            notes = case.get("approval_notes")
            if not isinstance(notes, str) or not notes:
                raise ValueError(f"{path} case {case_id} is approved_for_promotion but missing approval_notes")

        for field in (
            "candidate_suite_id",
            "candidate_target_object_type",
            "candidate_target_workflow_family",
            "candidate_disposition",
            "candidate_workflow_effect",
        ):
            value = case.get(field)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{path} case {case_id} missing required field {field}")

        candidate_required_read_surfaces = case.get("candidate_required_read_surfaces")
        if candidate_required_read_surfaces is not None:
            if not isinstance(candidate_required_read_surfaces, list) or not all(
                isinstance(item, str) for item in candidate_required_read_surfaces
            ):
                raise ValueError(
                    f"{path} case {case_id} has invalid candidate_required_read_surfaces"
                )

        for field in (
            "candidate_meal_link_action",
            "candidate_decision_next_action",
            "candidate_commit_posture",
            "candidate_observation_action",
        ):
            value = case.get(field)
            if value is not None and (not isinstance(value, str) or not value):
                raise ValueError(f"{path} case {case_id} has invalid optional field {field}")

        candidate_adjust_direction = case.get("candidate_adjust_direction")
        if candidate_adjust_direction is not None:
            if case.get("candidate_disposition") != "adjust":
                raise ValueError(
                    f"{path} case {case_id} uses candidate_adjust_direction outside candidate_disposition=adjust"
                )
            if candidate_adjust_direction not in {"shorter", "longer"}:
                raise ValueError(
                    f"{path} case {case_id} has unsupported candidate_adjust_direction: {candidate_adjust_direction}"
                )

        candidate_special_posture = case.get("candidate_special_posture")
        if candidate_special_posture is not None:
            if candidate_special_posture not in {"logging_first", "escalate", "standard_spread"}:
                raise ValueError(
                    f"{path} case {case_id} has unsupported candidate_special_posture: {candidate_special_posture}"
                )

        normalized[case_id] = case
    return normalized


def _validate_official_governance_metadata(official_payload: dict[str, Any], *, path: Path) -> None:
    suite_archetype = official_payload.get("suite_archetype")
    approval_mode = official_payload.get("approval_mode")
    truth_source = official_payload.get("truth_source")
    if suite_archetype not in ALLOWED_SUITE_ARCHETYPES:
        raise ValueError(f"{path} has unsupported suite_archetype: {suite_archetype}")
    if approval_mode not in ALLOWED_APPROVAL_MODES:
        raise ValueError(f"{path} has unsupported approval_mode: {approval_mode}")
    if truth_source not in ALLOWED_TRUTH_SOURCES:
        raise ValueError(f"{path} has unsupported truth_source: {truth_source}")


def _validate_official_pack(
    official_payload: dict[str, Any],
    *,
    path: Path,
    queue_cases: dict[str, dict[str, Any]],
) -> None:
    if official_payload.get("pack_mode") != "official_canonical":
        raise ValueError(f"{path} must use pack_mode=official_canonical")
    if official_payload.get("authority_level") != "canonical":
        raise ValueError(f"{path} must use authority_level=canonical")
    _validate_official_governance_metadata(official_payload, path=path)
    approval_mode = official_payload["approval_mode"]

    cases = official_payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{path} must contain a non-empty cases list")

    seen_case_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError(f"{path} contains a non-object case entry")

        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"{path} contains a case missing case_id")
        if case_id in seen_case_ids:
            raise ValueError(f"{path} contains duplicate case_id: {case_id}")
        seen_case_ids.add(case_id)

        promoted_from = case.get("promoted_from_candidate_case_id")
        if approval_mode == "user_required":
            if not isinstance(promoted_from, str) or not promoted_from:
                raise ValueError(f"{path} case {case_id} missing promoted_from_candidate_case_id")
            if promoted_from not in queue_cases:
                raise ValueError(f"{path} case {case_id} points to unknown candidate {promoted_from}")

            queue_case = queue_cases[promoted_from]
            if queue_case["review_status"] != "approved_for_promotion":
                raise ValueError(f"{path} case {case_id} points to non-approved candidate {promoted_from}")

            comparisons = (
                ("suite_id", "candidate_suite_id"),
                ("expected_target_object_type", "candidate_target_object_type"),
                ("expected_target_workflow_family", "candidate_target_workflow_family"),
                ("expected_disposition", "candidate_disposition"),
                ("expected_workflow_effect", "candidate_workflow_effect"),
            )
            for official_field, queue_field in comparisons:
                if case.get(official_field) != queue_case.get(queue_field):
                    raise ValueError(
                        f"{path} case {case_id} mismatch: {official_field} != {queue_field} "
                        f"({case.get(official_field)!r} vs {queue_case.get(queue_field)!r})"
                    )
            queue_adjust_direction = queue_case.get("candidate_adjust_direction")
            official_adjust_direction = case.get("expected_adjust_direction")
            if queue_adjust_direction is not None or official_adjust_direction is not None:
                if queue_case.get("candidate_disposition") != "adjust":
                    raise ValueError(
                        f"{path} case {case_id} carries adjust direction but queue disposition is not adjust"
                    )
                if official_adjust_direction != queue_adjust_direction:
                    raise ValueError(
                        f"{path} case {case_id} mismatch: expected_adjust_direction != candidate_adjust_direction "
                        f"({official_adjust_direction!r} vs {queue_adjust_direction!r})"
                    )
            optional_comparisons = (
                ("expected_required_read_surfaces", "candidate_required_read_surfaces"),
                ("expected_meal_link_action", "candidate_meal_link_action"),
                ("expected_decision_next_action", "candidate_decision_next_action"),
                ("expected_commit_posture", "candidate_commit_posture"),
                ("expected_observation_action", "candidate_observation_action"),
                ("expected_special_posture", "candidate_special_posture"),
            )
            for official_field, queue_field in optional_comparisons:
                queue_value = queue_case.get(queue_field)
                official_value = case.get(official_field)
                if queue_value is None and official_value is None:
                    continue
                if official_value != queue_value:
                    raise ValueError(
                        f"{path} case {case_id} mismatch: {official_field} != {queue_field} "
                        f"({official_value!r} vs {queue_value!r})"
                    )
        elif promoted_from not in (None, ""):
            raise ValueError(
                f"{path} case {case_id} should not carry promoted_from_candidate_case_id when approval_mode=agent_allowed"
            )


def _validate_agent_allowed_pack(official_payload: dict[str, Any], *, path: Path) -> None:
    if official_payload.get("pack_mode") != "official_canonical":
        raise ValueError(f"{path} must use pack_mode=official_canonical")
    if official_payload.get("authority_level") != "canonical":
        raise ValueError(f"{path} must use authority_level=canonical")
    _validate_official_governance_metadata(official_payload, path=path)
    if official_payload.get("approval_mode") != "agent_allowed":
        raise ValueError(f"{path} must use approval_mode=agent_allowed")
    if official_payload.get("truth_source") != "canonical_spec_derivation":
        raise ValueError(f"{path} must use truth_source=canonical_spec_derivation")
    if official_payload.get("suite_archetype") not in {"capability_service", "executable_workflow"}:
        raise ValueError(f"{path} must use suite_archetype=capability_service or executable_workflow")

    oracle_fields = official_payload.get("canonical_primary_oracle_fields")
    if not isinstance(oracle_fields, list) or not oracle_fields:
        raise ValueError(f"{path} must define non-empty canonical_primary_oracle_fields")

    cases = official_payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{path} must contain a non-empty cases list")

    seen_case_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError(f"{path} contains a non-object case entry")
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"{path} contains a case missing case_id")
        if case_id in seen_case_ids:
            raise ValueError(f"{path} contains duplicate case_id: {case_id}")
        seen_case_ids.add(case_id)
        if case.get("promoted_from_candidate_case_id") not in (None, ""):
            raise ValueError(f"{path} case {case_id} must not carry promoted_from_candidate_case_id")
        suite_id = case.get("suite_id")
        if not isinstance(suite_id, str) or not suite_id:
            raise ValueError(f"{path} case {case_id} missing suite_id")
        derivation_basis = case.get("derivation_basis")
        if not isinstance(derivation_basis, list) or not derivation_basis or not all(
            isinstance(item, str) and item for item in derivation_basis
        ):
            raise ValueError(f"{path} case {case_id} must define non-empty derivation_basis")
        for oracle_field in oracle_fields:
            value = case.get(oracle_field)
            if not isinstance(value, (dict, list, str, int, float, bool)) or value in ("", []):
                raise ValueError(f"{path} case {case_id} missing canonical field {oracle_field}")


def main() -> int:
    try:
        for pair in PROMOTION_PAIRS:
            official_payload = _load_json(pair["official_pack_path"])
            approval_mode = official_payload.get("approval_mode")
            queue_cases: dict[str, dict[str, Any]] = {}
            if approval_mode == "user_required":
                queue_payload = _load_json(pair["queue_path"])
                queue_cases = _validate_queue(queue_payload, path=pair["queue_path"])
            elif approval_mode != "agent_allowed":
                raise ValueError(
                    f"{pair['official_pack_path']} has unsupported approval_mode: {approval_mode}"
                )
            _validate_official_pack(
                official_payload,
                path=pair["official_pack_path"],
                queue_cases=queue_cases,
            )
        for pack_path in AGENT_ALLOWED_OFFICIAL_PACKS:
            official_payload = _load_json(pack_path)
            _validate_agent_allowed_pack(official_payload, path=pack_path)
    except ValueError as exc:
        print(f"[FAIL] suite promotion contract check failed: {exc}", file=sys.stderr)
        return 1

    print("[OK] suite promotion contract check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
