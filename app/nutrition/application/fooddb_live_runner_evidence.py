from __future__ import annotations

from typing import Any

from .fooddb_live_artifact_digest import (
    ARTIFACT_DIGEST_ALGORITHM,
    ARTIFACT_DIGEST_SCOPE,
    safe_fooddb_artifact_digest,
    verify_fooddb_artifact_digest,
)
from .grokfast_fooddb_diagnostic_preflight import is_grokfast_fooddb_preflight_clear
from .grokfast_fooddb_live_runner_readiness_checks import (
    input_artifact_blockers,
    live_runner_readiness_input_blockers,
)

EXPECTED_PREFLIGHT_TYPE = "accurate_intake_grokfast_fooddb_diagnostic_preflight_v1"
EXPECTED_ROUTER_TYPE = "accurate_intake_food_evidence_retriever_router_readiness_v1"
EXPECTED_LIVE_RUNNER_TYPE = "accurate_intake_grokfast_fooddb_live_runner_readiness_packet_v1"


def summarize_fooddb_live_runner_evidence(
    *,
    diagnostic_artifact: dict[str, Any],
    preflight_artifact: dict[str, Any] | None,
    router_readiness_artifact: dict[str, Any] | None,
    live_runner_readiness_artifact: dict[str, Any] | None,
) -> dict[str, Any]:
    preflight_ref = _mapping(diagnostic_artifact.get("preflight_ref"))
    router_ref = _mapping(diagnostic_artifact.get("router_readiness_ref"))
    live_runner_ref = _mapping(diagnostic_artifact.get("live_runner_readiness_ref"))

    preflight_digest = safe_fooddb_artifact_digest(preflight_ref.get("preflight_artifact_digest"))
    router_digest = safe_fooddb_artifact_digest(router_ref.get("router_artifact_digest"))
    live_runner_digest = safe_fooddb_artifact_digest(
        live_runner_ref.get("live_runner_artifact_digest")
    )

    preflight_digest_verified = verify_fooddb_artifact_digest(
        digest=preflight_digest,
        artifact=preflight_artifact,
    )
    router_digest_verified = verify_fooddb_artifact_digest(
        digest=router_digest,
        artifact=router_readiness_artifact,
    )
    live_runner_digest_verified = verify_fooddb_artifact_digest(
        digest=live_runner_digest,
        artifact=live_runner_readiness_artifact,
    )

    preflight_integrity_clear = _preflight_integrity_clear(preflight_artifact)
    router_integrity_clear = _router_integrity_clear(
        preflight_artifact=preflight_artifact,
        router_readiness_artifact=router_readiness_artifact,
    )
    live_runner_integrity_clear = _live_runner_integrity_clear(
        preflight_artifact=preflight_artifact,
        router_readiness_artifact=router_readiness_artifact,
        live_runner_readiness_artifact=live_runner_readiness_artifact,
    )

    return {
        "present": bool(preflight_ref and router_ref and live_runner_ref),
        "preflight_artifact_type": _safe_artifact_type(
            preflight_ref.get("artifact_type"),
            expected=EXPECTED_PREFLIGHT_TYPE,
            missing="missing_preflight_ref",
        ),
        "preflight_status": _safe_status(preflight_ref.get("status")),
        "preflight_clear_to_run_live_diagnostic": (
            preflight_ref.get("clear_to_run_live_diagnostic") is True
        ),
        "preflight_next_required_slice": _safe_optional_string(
            preflight_ref.get("next_required_slice")
        ),
        "preflight_artifact_digest_algorithm": _safe_algorithm(
            preflight_ref.get("preflight_artifact_digest_algorithm")
        ),
        "preflight_artifact_digest_scope": _safe_scope(
            preflight_ref.get("preflight_artifact_digest_scope")
        ),
        "preflight_artifact_digest": preflight_digest,
        "preflight_artifact_digest_verified": preflight_digest_verified,
        "preflight_artifact_integrity_clear": preflight_integrity_clear,
        "router_artifact_type": _safe_artifact_type(
            router_ref.get("artifact_type"),
            expected=EXPECTED_ROUTER_TYPE,
            missing="missing_router_readiness_ref",
        ),
        "router_status": _safe_status(router_ref.get("status")),
        "router_fail_count": _safe_non_negative_int(router_ref.get("fail_count")),
        "router_next_required_slice": _safe_optional_string(
            router_ref.get("next_required_slice")
        ),
        "router_artifact_digest_algorithm": _safe_algorithm(
            router_ref.get("router_artifact_digest_algorithm")
        ),
        "router_artifact_digest_scope": _safe_scope(
            router_ref.get("router_artifact_digest_scope")
        ),
        "router_artifact_digest": router_digest,
        "router_artifact_digest_verified": router_digest_verified,
        "router_artifact_integrity_clear": router_integrity_clear,
        "live_runner_artifact_type": _safe_artifact_type(
            live_runner_ref.get("artifact_type"),
            expected=EXPECTED_LIVE_RUNNER_TYPE,
            missing="missing_live_runner_readiness_ref",
        ),
        "live_runner_status": _safe_status(live_runner_ref.get("status")),
        "ready_for_grokfast_fooddb_packet_live_diagnostic": (
            live_runner_ref.get("ready_for_grokfast_fooddb_packet_live_diagnostic") is True
        ),
        "ready_for_runtime_truth": live_runner_ref.get("ready_for_runtime_truth") is True,
        "live_runner_next_required_slice": _safe_optional_string(
            live_runner_ref.get("next_required_slice")
        ),
        "live_runner_artifact_digest_algorithm": _safe_algorithm(
            live_runner_ref.get("live_runner_artifact_digest_algorithm")
        ),
        "live_runner_artifact_digest_scope": _safe_scope(
            live_runner_ref.get("live_runner_artifact_digest_scope")
        ),
        "live_runner_artifact_digest": live_runner_digest,
        "live_runner_artifact_digest_verified": live_runner_digest_verified,
        "live_runner_artifact_integrity_clear": live_runner_integrity_clear,
    }


def _preflight_integrity_clear(artifact: dict[str, Any] | None) -> bool:
    if not isinstance(artifact, dict):
        return False
    try:
        return is_grokfast_fooddb_preflight_clear(artifact)
    except (TypeError, ValueError):
        return False


def _router_integrity_clear(
    *,
    preflight_artifact: dict[str, Any] | None,
    router_readiness_artifact: dict[str, Any] | None,
) -> bool:
    if not isinstance(preflight_artifact, dict) or not isinstance(
        router_readiness_artifact, dict
    ):
        return False
    return not input_artifact_blockers(
        preflight_artifact=preflight_artifact,
        router_readiness_artifact=router_readiness_artifact,
    )


def _live_runner_integrity_clear(
    *,
    preflight_artifact: dict[str, Any] | None,
    router_readiness_artifact: dict[str, Any] | None,
    live_runner_readiness_artifact: dict[str, Any] | None,
) -> bool:
    if (
        not isinstance(preflight_artifact, dict)
        or not isinstance(router_readiness_artifact, dict)
        or not isinstance(live_runner_readiness_artifact, dict)
    ):
        return False
    return not live_runner_readiness_input_blockers(
        readiness_artifact=live_runner_readiness_artifact,
        preflight_artifact=preflight_artifact,
        router_readiness_artifact=router_readiness_artifact,
    )


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_artifact_type(value: Any, *, expected: str, missing: str) -> str:
    text = str(value or "").strip()
    if not text:
        return missing
    return expected if text == expected else "unsupported_artifact"


def _safe_status(value: Any) -> str:
    text = str(value or "").strip()
    return text or "missing"


def _safe_algorithm(value: Any) -> str:
    text = str(value or "").strip()
    return ARTIFACT_DIGEST_ALGORITHM if text == ARTIFACT_DIGEST_ALGORITHM else "unsupported_digest_algorithm"


def _safe_scope(value: Any) -> str:
    text = str(value or "").strip()
    return ARTIFACT_DIGEST_SCOPE if text == ARTIFACT_DIGEST_SCOPE else "unsupported_digest_scope"


def _safe_optional_string(value: Any) -> str | None:
    return str(value or "").strip() or None


def _safe_non_negative_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(0, value)


__all__ = [
    "ARTIFACT_DIGEST_ALGORITHM",
    "ARTIFACT_DIGEST_SCOPE",
    "EXPECTED_LIVE_RUNNER_TYPE",
    "EXPECTED_PREFLIGHT_TYPE",
    "EXPECTED_ROUTER_TYPE",
    "summarize_fooddb_live_runner_evidence",
]
