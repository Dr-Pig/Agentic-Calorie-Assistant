from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


TFDA_SOURCE_FLAG = "tfda_source_evidence"


def build_tfda_anchor_integrity_report(
    *,
    small_anchor_payload: dict[str, Any],
    tfda_source_payload: dict[str, Any],
) -> dict[str, Any]:
    source_by_id = {
        str(row.get("source_evidence_id")): row
        for row in tfda_source_payload.get("records") or []
        if isinstance(row, dict) and row.get("source_evidence_id")
    }
    rows = [
        _check_anchor(anchor, source_by_id)
        for anchor in small_anchor_payload.get("anchors") or []
        if _is_tfda_runtime_anchor(anchor)
    ]
    blockers = [
        f"{row['anchor_id']}:{check}"
        for row in rows
        for check, value in row.items()
        if check.endswith("_ok") and value is False
    ]
    blockers.extend(
        f"{row['anchor_id']}:{check}"
        for row in rows
        for check in (
            "source_ref_found",
            "source_kcal_matches",
            "macro_hidden_not_invented",
            "cjk_name_valid",
        )
        if row[check] is False
    )

    return {
        "artifact_type": "accurate_intake_fooddb_tfda_anchor_integrity_report",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "claim_scope": "tfda_runtime_anchor_integrity_only",
        "status": "pass" if not blockers else "blocked",
        "runtime_truth_changed": False,
        "summary": {
            "tfda_runtime_anchor_count": len(rows),
            "source_ref_match_count": sum(1 for row in rows if row["source_ref_found"]),
            "macro_hidden_count": sum(1 for row in rows if row["macro_hidden_not_invented"]),
            "cjk_name_valid_count": sum(1 for row in rows if row["cjk_name_valid"]),
            "blocker_count": len(blockers),
        },
        "anchor_checks": rows,
        "blockers": blockers,
        "non_claims": [
            "no_runtime_truth_write",
            "no_new_fooddb_records",
            "no_macro_invention",
            "no_product_readiness",
        ],
    }


def _is_tfda_runtime_anchor(anchor: Any) -> bool:
    return (
        isinstance(anchor, dict)
        and anchor.get("record_kind") == "generic_anchor"
        and anchor.get("runtime_truth_allowed") is True
        and TFDA_SOURCE_FLAG in set(anchor.get("source_posture_flags") or [])
    )


def _check_anchor(anchor: dict[str, Any], source_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    source_ref = _first_source_ref(anchor)
    source_id = str(source_ref.get("source_evidence_id") or "")
    source_row = source_by_id.get(source_id)
    return {
        "anchor_id": str(anchor.get("anchor_id") or ""),
        "canonical_name": str(anchor.get("canonical_name") or ""),
        "source_evidence_id": source_id,
        "source_ref_found": source_row is not None,
        "source_role_boundary_ok": _source_role_boundary_ok(source_ref),
        "source_kcal_matches": _source_kcal_matches(source_ref, source_row),
        "macro_hidden_not_invented": _macro_hidden_not_invented(anchor),
        "cjk_name_valid": _cjk_name_valid(anchor),
    }


def _first_source_ref(anchor: dict[str, Any]) -> dict[str, Any]:
    refs = anchor.get("source_refs") or []
    if refs and isinstance(refs[0], dict):
        return refs[0]
    return {}


def _source_role_boundary_ok(source_ref: dict[str, Any]) -> bool:
    return (
        source_ref.get("runtime_role") == "source_evidence_only"
        and source_ref.get("serving_basis") == "per_100g"
        and source_ref.get("external_source_role") == "source_evidence_only"
    )


def _source_kcal_matches(source_ref: dict[str, Any], source_row: dict[str, Any] | None) -> bool:
    if source_row is None:
        return False
    try:
        ref_kcal = float(source_ref.get("kcal_per_100g"))
        source_kcal = float(source_row.get("kcal_per_100g"))
    except (TypeError, ValueError):
        return False
    return abs(ref_kcal - source_kcal) < 0.001


def _macro_hidden_not_invented(anchor: dict[str, Any]) -> bool:
    macro_fields = ("protein_g", "carbs_g", "carb_g", "fat_g")
    return all(anchor.get(field) in (None, "") for field in macro_fields)


def _cjk_name_valid(anchor: dict[str, Any]) -> bool:
    values = [str(anchor.get("canonical_name") or "")]
    values.extend(str(alias or "") for alias in anchor.get("aliases") or [])
    return all(value and "?" not in value for value in values)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_tfda_anchor_integrity_report"]
