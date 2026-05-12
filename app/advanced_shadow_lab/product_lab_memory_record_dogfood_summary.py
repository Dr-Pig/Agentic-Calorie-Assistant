from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_simulated_summary import (
    build_simulated_dogfood_summary,
)


def build_memory_record_dogfood_summary(
    session_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    summary = build_simulated_dogfood_summary(session_artifact)
    summary.update(
        {
            "artifact_type": "advanced_product_lab_memory_record_dogfood_summary",
            "owner": "scripts/run_advanced_product_lab_memory_record_dogfood.py",
            "memory_record_session_replay_enabled": bool(
                session_artifact.get("memory_record_session_replay_enabled")
            ),
            "memory_record_context_pack_used": bool(
                session_artifact.get("memory_record_context_pack_used")
            ),
            "memory_record_write_artifact_count": len(
                session_artifact.get("memory_record_write_artifacts") or []
            ),
        }
    )
    return summary


__all__ = ["build_memory_record_dogfood_summary"]
