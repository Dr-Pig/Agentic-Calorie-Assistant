from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .websearch_grokfast_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS,
    REQUIRED_MODIFIER_GUARD_CASE_COUNT,
    REQUIRED_NEGATIVE_CASE_COUNT,
)
from .websearch_live_extract_preflight import is_websearch_live_extract_preflight_clear

PREFLIGHT_DIGEST_ALGORITHM = "sha256"
PREFLIGHT_DIGEST_SCOPE = "semantic_preflight_without_generated_at_utc"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def websearch_live_extract_preflight_digest(artifact: dict[str, Any]) -> str:
    payload = {
        key: value
        for key, value in artifact.items()
        if key != "generated_at_utc"
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def summarize_websearch_preflight_evidence(
    *,
    diagnostic_artifact: dict[str, Any],
    preflight_artifact: dict[str, Any] | None,
) -> dict[str, Any]:
    preflight = diagnostic_artifact.get("preflight_ref")
    if not isinstance(preflight, dict):
        return _missing_preflight_evidence()
    digest = _safe_preflight_digest(preflight.get("preflight_artifact_digest"))
    digest_verified = _preflight_digest_verified(
        digest=digest,
        preflight_artifact=preflight_artifact,
    )
    integrity_clear = _preflight_artifact_integrity_clear(preflight_artifact)
    evidence = {
        "present": True,
        "preflight_ref_source": _safe_preflight_ref_source(preflight.get("preflight_ref_source")),
        "artifact_type": _safe_preflight_artifact_type(preflight.get("artifact_type")),
        "status": "pass" if preflight.get("status") == "pass" else "blocked",
        "ready_for_live_extract_diagnostic": preflight.get("ready_for_live_extract_diagnostic") is True,
        "ready_for_runtime_truth": preflight.get("ready_for_runtime_truth") is True,
        "review_packet_authorized": preflight.get("review_packet_authorized") is True,
        "review_packet_count": _safe_non_negative_int(preflight.get("review_packet_count")),
        "case_matrix_fixed_required_cases": preflight.get("case_matrix_fixed_required_cases") is True,
        "case_matrix_case_count": _safe_non_negative_int(preflight.get("case_matrix_case_count")),
        "case_matrix_negative_case_count": _safe_non_negative_int(
            preflight.get("case_matrix_negative_case_count")
        ),
        "case_matrix_modifier_guard_cases": _safe_non_negative_int(
            preflight.get("case_matrix_modifier_guard_cases")
        ),
        "case_matrix_live_provider_invoked": preflight.get("case_matrix_live_provider_invoked") is not False,
        "case_matrix_websearch_invoked": preflight.get("case_matrix_websearch_invoked") is not False,
        "preflight_artifact_digest_algorithm": _safe_preflight_digest_algorithm(
            preflight.get("preflight_artifact_digest_algorithm")
        ),
        "preflight_artifact_digest_scope": _safe_preflight_digest_scope(
            preflight.get("preflight_artifact_digest_scope")
        ),
        "preflight_artifact_digest": digest,
        "preflight_artifact_digest_verified": digest_verified,
        "preflight_artifact_integrity_clear": integrity_clear,
    }
    if digest_verified and integrity_clear:
        evidence.update(_verified_preflight_artifact_evidence(preflight_artifact))
    return evidence


def is_websearch_preflight_evidence_healthy(preflight: dict[str, Any]) -> bool:
    return (
        preflight.get("present") is True
        and preflight.get("preflight_ref_source")
        == "run_accurate_intake_grokfast_websearch_packet_smoke"
        and preflight.get("artifact_type") == "accurate_intake_websearch_live_extract_preflight_v1"
        and preflight.get("status") == "pass"
        and preflight.get("ready_for_live_extract_diagnostic") is True
        and preflight.get("ready_for_runtime_truth") is False
        and preflight.get("review_packet_authorized") is True
        and preflight.get("review_packet_count") >= 1
        and preflight.get("case_matrix_fixed_required_cases") is True
        and preflight.get("case_matrix_case_count") == len(REQUIRED_CASE_IDS)
        and preflight.get("case_matrix_negative_case_count") == REQUIRED_NEGATIVE_CASE_COUNT
        and preflight.get("case_matrix_modifier_guard_cases")
        == REQUIRED_MODIFIER_GUARD_CASE_COUNT
        and preflight.get("case_matrix_live_provider_invoked") is False
        and preflight.get("case_matrix_websearch_invoked") is False
        and preflight.get("preflight_artifact_digest_algorithm") == PREFLIGHT_DIGEST_ALGORITHM
        and preflight.get("preflight_artifact_digest_scope") == PREFLIGHT_DIGEST_SCOPE
        and preflight.get("preflight_artifact_digest_verified") is True
        and preflight.get("preflight_artifact_integrity_clear") is True
    )


def _missing_preflight_evidence() -> dict[str, Any]:
    return {
        "present": False,
        "preflight_ref_source": "missing",
        "artifact_type": "missing_preflight_ref",
        "status": "missing",
        "ready_for_live_extract_diagnostic": False,
        "ready_for_runtime_truth": False,
        "review_packet_authorized": False,
        "review_packet_count": 0,
        "case_matrix_fixed_required_cases": False,
        "case_matrix_case_count": 0,
        "case_matrix_negative_case_count": 0,
        "case_matrix_modifier_guard_cases": 0,
        "case_matrix_live_provider_invoked": True,
        "case_matrix_websearch_invoked": True,
        "preflight_artifact_digest_algorithm": "missing",
        "preflight_artifact_digest_scope": "missing",
        "preflight_artifact_digest": "missing",
        "preflight_artifact_digest_verified": False,
        "preflight_artifact_integrity_clear": False,
    }


def _safe_preflight_ref_source(value: Any) -> str:
    if str(value or "") == "run_accurate_intake_grokfast_websearch_packet_smoke":
        return "run_accurate_intake_grokfast_websearch_packet_smoke"
    return "unsupported_preflight_ref_source"


def _safe_preflight_artifact_type(value: Any) -> str:
    if str(value or "") == "accurate_intake_websearch_live_extract_preflight_v1":
        return "accurate_intake_websearch_live_extract_preflight_v1"
    return "unsupported_preflight_artifact"


def _safe_preflight_digest_algorithm(value: Any) -> str:
    return PREFLIGHT_DIGEST_ALGORITHM if str(value or "") == PREFLIGHT_DIGEST_ALGORITHM else "unsupported_digest_algorithm"


def _safe_preflight_digest_scope(value: Any) -> str:
    if str(value or "") == PREFLIGHT_DIGEST_SCOPE:
        return PREFLIGHT_DIGEST_SCOPE
    return "unsupported_digest_scope"


def _safe_preflight_digest(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if _SHA256_RE.match(text) else "invalid_preflight_artifact_digest"


def _preflight_digest_verified(
    *,
    digest: str,
    preflight_artifact: dict[str, Any] | None,
) -> bool:
    if not isinstance(preflight_artifact, dict) or not _SHA256_RE.match(digest):
        return False
    return websearch_live_extract_preflight_digest(preflight_artifact) == digest


def _preflight_artifact_integrity_clear(preflight_artifact: dict[str, Any] | None) -> bool:
    if not isinstance(preflight_artifact, dict):
        return False
    try:
        return is_websearch_live_extract_preflight_clear(preflight_artifact)
    except (TypeError, ValueError):
        return False


def _verified_preflight_artifact_evidence(
    preflight_artifact: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(preflight_artifact, dict):
        return {}
    summary = preflight_artifact.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    review_packet_count = _safe_non_negative_int(summary.get("review_packet_count"))
    review_packet_refs = preflight_artifact.get("review_packet_refs")
    return {
        "artifact_type": _safe_preflight_artifact_type(preflight_artifact.get("artifact_type")),
        "status": "pass" if preflight_artifact.get("status") == "pass" else "blocked",
        "ready_for_live_extract_diagnostic": (
            preflight_artifact.get("ready_for_live_extract_diagnostic") is True
        ),
        "ready_for_runtime_truth": preflight_artifact.get("ready_for_runtime_truth") is True,
        "review_packet_authorized": (
            review_packet_count >= 1
            and isinstance(review_packet_refs, list)
            and len(review_packet_refs) >= 1
        ),
        "review_packet_count": review_packet_count,
        "case_matrix_fixed_required_cases": (
            summary.get("case_matrix_fixed_required_cases") is True
        ),
        "case_matrix_case_count": _safe_non_negative_int(
            summary.get("case_matrix_case_count")
        ),
        "case_matrix_negative_case_count": _safe_non_negative_int(
            summary.get("case_matrix_negative_case_count")
        ),
        "case_matrix_modifier_guard_cases": _safe_non_negative_int(
            summary.get("case_matrix_modifier_guard_cases")
        ),
        "case_matrix_live_provider_invoked": (
            summary.get("case_matrix_live_provider_invoked") is not False
        ),
        "case_matrix_websearch_invoked": (
            summary.get("case_matrix_websearch_invoked") is not False
        ),
    }


def _safe_non_negative_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(0, value)


__all__ = [
    "PREFLIGHT_DIGEST_ALGORITHM",
    "PREFLIGHT_DIGEST_SCOPE",
    "is_websearch_preflight_evidence_healthy",
    "summarize_websearch_preflight_evidence",
    "websearch_live_extract_preflight_digest",
]
