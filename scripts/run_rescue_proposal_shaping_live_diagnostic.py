from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.advanced_shadow_lab.model_profiles import (  # noqa: E402
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    resolve_live_diagnostic_profile,
)
from app.providers.builderspace_adapter import BuilderSpaceAdapter  # noqa: E402
from app.rescue.application.proposal_shaping_seam import (  # noqa: E402
    FakeRescueProposalShapingProvider,
    build_rescue_proposal_shaping_payload,
    run_rescue_proposal_shaping_provider_diagnostic,
)
from app.shared.infra.json_artifacts import (  # noqa: E402
    read_json_artifact,
    write_json_artifact,
)


ALLOW_ENV = "ADVANCED_SHADOW_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC"
DEFAULT_OUTPUT = ROOT / "artifacts" / "rescue_proposal_shaping_provider_diagnostic.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run rescue proposal-shaping provider diagnostic."
    )
    parser.add_argument("--proposal-shaping-payload", type=Path)
    parser.add_argument("--provider-mode", choices=("fake", "live"), default="fake")
    parser.add_argument("--allow-live-provider", action="store_true")
    parser.add_argument("--provider-profile-id", default=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    payload = (
        read_json_artifact(args.proposal_shaping_payload)
        if args.proposal_shaping_payload
        else _fixture_payload()
    )
    if args.provider_mode == "live":
        blocked = _live_blockers(
            provider_profile_id=str(args.provider_profile_id),
            allow_live_provider=bool(args.allow_live_provider),
            env=os.environ,
        )
        if blocked:
            artifact = _blocked_artifact(payload, str(args.provider_profile_id), blocked)
            write_json_artifact(args.output, artifact)
            print(json.dumps(artifact, ensure_ascii=False))
            return 1
        profile, _ = resolve_live_diagnostic_profile(str(args.provider_profile_id))
        provider = BuilderSpaceAdapter(
            manager_model_override=str(profile["model_id"]),
            role_label="rescue_proposal_shaping_diagnostic",
        )
        artifact = run_rescue_proposal_shaping_provider_diagnostic(
            proposal_shaping_payload=payload,
            provider=provider,
            provider_mode=str(args.provider_profile_id),
            live_llm_invoked=True,
        )
    else:
        artifact = run_rescue_proposal_shaping_provider_diagnostic(
            proposal_shaping_payload=payload,
            provider=FakeRescueProposalShapingProvider(_fixture_candidate()),
            provider_mode="fake",
            live_llm_invoked=False,
        )
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False))
    return 0 if artifact["status"] == "pass" else 1


def _live_blockers(
    *,
    provider_profile_id: str,
    allow_live_provider: bool,
    env: Mapping[str, str],
) -> list[str]:
    try:
        _, profile_blockers = resolve_live_diagnostic_profile(provider_profile_id)
    except ValueError as exc:
        return [str(exc)]
    blockers = [str(item) for item in profile_blockers]
    if not allow_live_provider or env.get(ALLOW_ENV) != "1":
        blockers.append("live_gate_not_enabled")
    if not str(env.get("AI_BUILDER_TOKEN") or "").strip():
        blockers.append("ai_builder_token_missing")
    return blockers


def _blocked_artifact(
    payload: Mapping[str, Any],
    provider_profile_id: str,
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "artifact_type": "rescue_proposal_shaping_provider_diagnostic",
        "status": "blocked",
        "owner": "scripts/run_rescue_proposal_shaping_live_diagnostic.py",
        "provider_mode": provider_profile_id,
        "provider_called": False,
        "live_llm_invoked": False,
        "live_provider_used": False,
        "source_payload_status": str(payload.get("status") or ""),
        "blockers": blockers,
        "mainline_activation_enabled": False,
        "runtime_effect_allowed": False,
        "canonical_mutation_changed": False,
    }


def _fixture_payload() -> dict[str, Any]:
    return build_rescue_proposal_shaping_payload(
        independent_message_flow={
            "artifact_type": "reactive_rescue_independent_message_flow",
            "status": "pass",
            "rescue_message_created": True,
            "independent_message": {"message_id": "rescue-message-fixture"},
            "runtime_effect_allowed": False,
            "canonical_mutation_changed": False,
            "production_scheduler_delivery_allowed": False,
        },
        option_generation_result={
            "artifact_type": "rescue_option_generation_result",
            "status": "pass",
            "selected_option": {
                "recommended_days": 2,
                "daily_kcal_adjustment": -225,
                "cap_mode": "standard_15_percent",
                "special_posture": "strained_standard_spread",
            },
            "runtime_effect_allowed": False,
            "canonical_mutation_changed": False,
            "production_scheduler_delivery_allowed": False,
        },
        budget_context={"local_date": "2026-05-13", "overshoot_kcal": 450},
        rescue_history_context={"recent_rescue_count": 0},
    )


def _fixture_candidate() -> dict[str, Any]:
    return {
        "proposal_headline": "A small two-day recovery plan is ready.",
        "proposal_summary": "Shift 225 kcal from each of the next two days.",
        "coaching_frame": "Keep this as planning, not punishment.",
        "quick_action_posture": "accept_or_adjust",
        "recommended_days": 2,
        "daily_kcal_adjustment": -225,
        "cap_mode": "standard_15_percent",
        "claim_scope": "lab_proposal_shaping_only",
        "action_request": False,
        "delivery_request": False,
        "mutation_request": False,
        "reason_codes": ["future_oriented", "no_shame"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
