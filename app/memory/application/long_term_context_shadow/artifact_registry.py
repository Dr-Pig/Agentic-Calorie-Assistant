from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import (
    _base_artifact,
    artifact_review_contract,
)


def build_artifact_registry_manifest(
    fixture_payload: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    from app.memory.application.long_term_context_shadow.fixture_reader import (
        _normalize_dogfood_export_payload,
    )

    fixture = (
        dict(fixture_payload)
        if "_input_reader" in fixture_payload
        else _normalize_dogfood_export_payload(fixture_payload)
    )
    return _artifact_registry_manifest_artifact(
        fixture,
        {
            artifact_key: artifact
            for artifact_key, artifact in artifacts.items()
            if artifact_key != "artifact_registry_manifest"
        },
    )


def _artifact_registry_manifest_artifact(
    fixture: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    entries = [
        _artifact_registry_entry(
            artifact_key="artifact_registry_manifest",
            artifact_type="artifact_registry_manifest",
            artifact=artifact_review_contract("artifact_registry_manifest"),
        )
    ]
    entries.extend(
        _artifact_registry_entry(
            artifact_key=artifact_key,
            artifact_type=str(artifact.get("artifact_type") or artifact_key),
            artifact=artifact,
        )
        for artifact_key, artifact in artifacts.items()
    )
    artifacts_without_consumers = [
        entry["artifact_key"] for entry in entries if not entry["intended_consumers"]
    ]
    pseudo_runtime_truth_risks = [
        entry["artifact_key"]
        for entry in entries
        if entry["runtime_effect_allowed"] or not entry["why_this_is_not_runtime_truth"]
    ]
    return _base_artifact(
        artifact_type="artifact_registry_manifest",
        fixture=fixture,
        extra={
            "manifest_scope": "batch_1_shadow_lab_artifact_registry",
            "artifact_count": len(entries),
            "artifact_registry_entries": entries,
            "artifacts_without_consumers": artifacts_without_consumers,
            "pseudo_runtime_truth_risks": pseudo_runtime_truth_risks,
            "all_artifacts_have_future_consumers": not artifacts_without_consumers,
            "all_artifacts_block_runtime_truth": not pseudo_runtime_truth_risks,
        },
    )


def _artifact_registry_entry(
    *,
    artifact_key: str,
    artifact_type: str,
    artifact: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_key": artifact_key,
        "artifact_type": artifact_type,
        "intended_consumers": list(artifact.get("intended_consumers") or []),
        "consumer_use_hints": dict(artifact.get("consumer_use_hints") or {}),
        "risk_if_wrong": str(artifact.get("risk_if_wrong") or ""),
        "promotion_path": str(artifact.get("promotion_path") or ""),
        "runtime_effect_allowed": bool(artifact.get("runtime_effect_allowed") is True),
        "why_this_is_not_runtime_truth": str(
            artifact.get("why_this_is_not_runtime_truth") or ""
        ),
        "manager_context_injection_allowed": False,
        "durable_memory_write_allowed": False,
        "future_consumer_declared": bool(artifact.get("intended_consumers")),
    }
