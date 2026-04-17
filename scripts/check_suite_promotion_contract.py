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
        "queue_path": ROOT / "docs" / "quality" / "benchmarks" / "rescue" / "rescue_candidate_review_queue_v1.json",
        "official_pack_path": ROOT / "docs" / "quality" / "benchmarks" / "rescue" / "rescue_official_canonical_pack_v1.json",
    },
)


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

        normalized[case_id] = case
    return normalized


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


def main() -> int:
    try:
        for pair in PROMOTION_PAIRS:
            queue_payload = _load_json(pair["queue_path"])
            queue_cases = _validate_queue(queue_payload, path=pair["queue_path"])
            official_payload = _load_json(pair["official_pack_path"])
            _validate_official_pack(
                official_payload,
                path=pair["official_pack_path"],
                queue_cases=queue_cases,
            )
    except ValueError as exc:
        print(f"[FAIL] suite promotion contract check failed: {exc}", file=sys.stderr)
        return 1

    print("[OK] suite promotion contract check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
