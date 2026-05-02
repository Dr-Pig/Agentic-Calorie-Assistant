from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CorrectionTargetRef:
    meal_thread_id: int
    meal_item_id: int
    canonical_name: str


def validate_correction_target_ref(correction_target: Any | None) -> dict[str, Any]:
    if not isinstance(correction_target, dict) or not correction_target:
        return {
            "resolved": None,
            "failure_family": None,
            "truth_owner": "meal_item_id",
            "reason": "no_target_evidence",
        }
    source = str(correction_target.get("target_resolution_source") or "").strip().lower()
    if source in {"", "none", "unknown"}:
        return {
            "resolved": None,
            "failure_family": None,
            "truth_owner": "meal_item_id",
            "reason": "no_target_evidence",
        }
    if correction_target.get("meal_thread_id") is None:
        return {
            "resolved": False,
            "failure_family": "correction_thread_target_missing",
            "truth_owner": "meal_item_id",
            "reason": "meal_thread_id_required",
        }
    if correction_target.get("meal_item_id") is None:
        return {
            "resolved": False,
            "failure_family": "correction_item_target_missing",
            "truth_owner": "meal_item_id",
            "reason": "meal_item_id_required",
        }

    expected_name = str(correction_target.get("canonical_name") or "").strip()
    observed_name = str(correction_target.get("observed_canonical_name") or "").strip()
    if expected_name and observed_name and expected_name.casefold() != observed_name.casefold():
        return {
            "resolved": False,
            "failure_family": "correction_canonical_name_mismatch",
            "truth_owner": "meal_item_id",
            "reason": "canonical_name_validation_failed",
            "canonical_name": expected_name,
            "observed_canonical_name": observed_name,
        }

    return {
        "resolved": True,
        "failure_family": None,
        "truth_owner": "meal_item_id",
        "reason": "stable_item_target_present",
        "meal_thread_id": correction_target.get("meal_thread_id"),
        "meal_item_id": correction_target.get("meal_item_id"),
        "canonical_name": expected_name,
    }


__all__ = ["CorrectionTargetRef", "validate_correction_target_ref"]
