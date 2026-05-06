from __future__ import annotations

from typing import Any

from .fooddb_live_artifact_digest import (
    ARTIFACT_DIGEST_ALGORITHM,
    ARTIFACT_DIGEST_SCOPE,
    fooddb_semantic_artifact_digest,
)


def attach_fooddb_live_upstream_refs(
    *,
    diagnostic_artifact: dict[str, Any],
    preflight_artifact: dict[str, Any] | None,
    router_readiness_artifact: dict[str, Any] | None,
    live_runner_readiness_artifact: dict[str, Any] | None,
) -> dict[str, Any]:
    artifact = dict(diagnostic_artifact)
    if isinstance(preflight_artifact, dict):
        artifact["preflight_ref"] = build_fooddb_preflight_ref(preflight_artifact)
    if isinstance(router_readiness_artifact, dict):
        artifact["router_readiness_ref"] = build_fooddb_router_readiness_ref(
            router_readiness_artifact
        )
    if isinstance(live_runner_readiness_artifact, dict):
        artifact["live_runner_readiness_ref"] = build_fooddb_live_runner_readiness_ref(
            live_runner_readiness_artifact
        )
    return artifact


def build_fooddb_preflight_ref(preflight_artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": preflight_artifact.get("artifact_type"),
        "status": preflight_artifact.get("status"),
        "clear_to_run_live_diagnostic": preflight_artifact.get(
            "clear_to_run_live_diagnostic"
        )
        is True,
        "next_required_slice": preflight_artifact.get("next_required_slice"),
        "preflight_artifact_digest_algorithm": ARTIFACT_DIGEST_ALGORITHM,
        "preflight_artifact_digest_scope": ARTIFACT_DIGEST_SCOPE,
        "preflight_artifact_digest": fooddb_semantic_artifact_digest(preflight_artifact),
    }


def build_fooddb_router_readiness_ref(
    router_readiness_artifact: dict[str, Any],
) -> dict[str, Any]:
    summary = _summary(router_readiness_artifact)
    return {
        "artifact_type": router_readiness_artifact.get("artifact_type"),
        "status": router_readiness_artifact.get("status"),
        "fail_count": int(summary.get("fail_count", 0) or 0),
        "next_required_slice": summary.get("next_required_slice"),
        "router_artifact_digest_algorithm": ARTIFACT_DIGEST_ALGORITHM,
        "router_artifact_digest_scope": ARTIFACT_DIGEST_SCOPE,
        "router_artifact_digest": fooddb_semantic_artifact_digest(
            router_readiness_artifact
        ),
    }


def build_fooddb_live_runner_readiness_ref(
    live_runner_readiness_artifact: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": live_runner_readiness_artifact.get("artifact_type"),
        "status": live_runner_readiness_artifact.get("status"),
        "ready_for_grokfast_fooddb_packet_live_diagnostic": (
            live_runner_readiness_artifact.get(
                "ready_for_grokfast_fooddb_packet_live_diagnostic"
            )
            is True
        ),
        "ready_for_runtime_truth": (
            live_runner_readiness_artifact.get("ready_for_runtime_truth") is True
        ),
        "next_required_slice": live_runner_readiness_artifact.get("next_required_slice"),
        "live_runner_artifact_digest_algorithm": ARTIFACT_DIGEST_ALGORITHM,
        "live_runner_artifact_digest_scope": ARTIFACT_DIGEST_SCOPE,
        "live_runner_artifact_digest": fooddb_semantic_artifact_digest(
            live_runner_readiness_artifact
        ),
    }


def _summary(artifact: dict[str, Any]) -> dict[str, Any]:
    summary = artifact.get("summary")
    return dict(summary) if isinstance(summary, dict) else {}


__all__ = [
    "attach_fooddb_live_upstream_refs",
    "build_fooddb_live_runner_readiness_ref",
    "build_fooddb_preflight_ref",
    "build_fooddb_router_readiness_ref",
]
