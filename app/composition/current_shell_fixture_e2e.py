from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.current_shell_fixture_e2e_checks import (
    COMPLETED_CURRENT_SHELL_STEPS,
    object_dict,
    overclaim_blockers,
    status as input_status,
    validate_browser_realistic,
    validate_context_replay,
    validate_fake_provider_smoke,
    validate_one_day_wall,
    validate_reopen_continuity,
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def build_current_shell_fixture_e2e_artifact(
    *,
    one_day_wall: dict[str, Any],
    reopen_continuity: dict[str, Any],
    browser_realistic: dict[str, Any],
    context_replay: dict[str, Any],
    fake_provider_context_smoke: dict[str, Any],
) -> dict[str, Any]:
    inputs = {
        "one_day_wall": object_dict(one_day_wall),
        "reopen_continuity": object_dict(reopen_continuity),
        "browser_realistic": object_dict(browser_realistic),
        "context_replay": object_dict(context_replay),
        "fake_provider_context_smoke": object_dict(fake_provider_context_smoke),
    }
    blockers: list[str] = []
    for artifact_id, payload in inputs.items():
        blockers.extend(overclaim_blockers(artifact_id, payload))
    blockers.extend(validate_one_day_wall(inputs["one_day_wall"]))
    blockers.extend(validate_reopen_continuity(inputs["reopen_continuity"]))
    browser_blockers, browser_executed = validate_browser_realistic(inputs["browser_realistic"])
    blockers.extend(browser_blockers)
    blockers.extend(validate_context_replay(inputs["context_replay"]))
    blockers.extend(validate_fake_provider_smoke(inputs["fake_provider_context_smoke"]))

    if any("." in blocker for blocker in blockers):
        status = "fail"
    elif blockers == ["browser_realistic_not_executed"]:
        status = "blocked_browser_execution_unavailable"
    elif blockers:
        status = "fail"
    else:
        status = "current_shell_fixture_e2e_diagnostic_pass"

    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_current_shell_fixture_e2e",
            "claim_scope": "current_shell_fixture_e2e_diagnostic",
            "status": status,
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "blockers": blockers,
            "completed_current_shell_steps": list(COMPLETED_CURRENT_SHELL_STEPS)
            if status == "current_shell_fixture_e2e_diagnostic_pass"
            else [
                step
                for step in COMPLETED_CURRENT_SHELL_STEPS
                if step not in {"browser_render_same_truth"}
            ],
            "browser_executed": browser_executed,
            "local_only": True,
            "diagnostic_only": True,
            "ready_for_fdb_integration": False,
            "fixture_evidence_used": True,
            "fooddb_evidence_used": False,
            "websearch_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_db_used": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_truth_updated": False,
            "manager_context_packet_schema_changed": False,
            "frontend_semantic_owner": False,
            "semantic_owner_summary": {
                "user_intent": "fixture_manager_structured_decision",
                "food_semantics": "fixture_evidence_only",
                "mutation_legality": "runtime_guard",
                "persistence_truth": "local_sqlite_canonical_state",
                "frontend": "render_only",
            },
            "input_statuses": {
                artifact_id: {
                    "status": input_status(payload),
                    "artifact_type": payload.get("artifact_type")
                    or payload.get("scenario_wall_id")
                    or payload.get("continuity_id")
                    or "unknown",
                }
                for artifact_id, payload in inputs.items()
            },
        }
    )


__all__ = [
    "build_current_shell_fixture_e2e_artifact",
]
