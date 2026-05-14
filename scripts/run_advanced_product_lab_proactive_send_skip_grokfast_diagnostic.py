from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.advanced_shadow_lab.model_profiles import (  # noqa: E402
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    resolve_live_diagnostic_profile,
)
from app.advanced_shadow_lab.product_lab_fixture_inputs import (  # noqa: E402
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_proactive import run_product_lab_proactive  # noqa: E402
from app.advanced_shadow_lab.product_lab_proactive_send_skip_live_diagnostic import (  # noqa: E402
    blocked_not_invoked_proactive_send_skip_live_artifact,
    run_product_lab_proactive_send_skip_live_diagnostic,
)


ALLOW_ENV = "ADVANCED_PRODUCT_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC"


class FakeProactiveSendSkipProvider:
    def readiness(self) -> dict[str, object]:
        return {"provider": "fake-proactive-send-skip", "configured": True}

    async def complete_with_trace(self, **_: object) -> tuple[dict[str, object], dict[str, object]]:
        return {
            "claim_scope": "diagnostic_only",
            "provider_decisions": [
                {
                    "candidate_id": "recommendation_prompt:0",
                    "send_or_skip": "send",
                    "reason_summary": "App-open recommendation prompt is useful.",
                    "chat_first_copy": "要不要我幫你挑一個現在可行的選項？",
                    "skip_reason": "",
                    "reason_codes": ["app_open", "qualified_offer"],
                    "delivery_request": False,
                    "scheduler_request": False,
                    "notification_request": False,
                    "mutation_request": False,
                },
                {
                    "candidate_id": "rescue_nudge:1",
                    "send_or_skip": "skip",
                    "reason_summary": "Rescue nudge should wait for explicit consent.",
                    "chat_first_copy": "",
                    "skip_reason": "permission_posture_not_ready",
                    "reason_codes": ["explicit_consent_required"],
                    "delivery_request": False,
                    "scheduler_request": False,
                    "notification_request": False,
                    "mutation_request": False,
                },
            ],
        }, {
            "stage": "advanced_product_lab_proactive_send_skip_grokfast_diagnostic",
            "provider": "fake",
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run proactive contextual send/skip Grokfast diagnostic."
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--provider-mode", choices=("fake", "live"), default="fake")
    parser.add_argument("--allow-live-provider", action="store_true")
    parser.add_argument("--provider-profile-id", default=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID)
    args = parser.parse_args(argv)

    artifact = _live_artifact(args) if args.provider_mode == "live" else _fake_artifact(args)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "status": artifact.get("status"),
                "provider_mode": artifact.get("provider_mode"),
                "live_invoked": artifact.get("live_invoked"),
                "live_grokfast_diagnostic_pass": artifact.get(
                    "live_grokfast_diagnostic_pass"
                ),
                "blockers": artifact.get("blockers"),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _fake_artifact(args: argparse.Namespace) -> dict[str, Any]:
    return run_product_lab_proactive_send_skip_live_diagnostic(
        pre_delivery_review=_pre_delivery_review(),
        provider=FakeProactiveSendSkipProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        provider_profile_id=str(args.provider_profile_id),
        output_path=args.output,
    )


def _live_artifact(args: argparse.Namespace) -> dict[str, Any]:
    try:
        profile, blockers = resolve_live_diagnostic_profile(str(args.provider_profile_id))
    except ValueError as exc:
        return _blocked(args, str(exc))
    if blockers:
        return _blocked(args, ";".join(blockers))
    if not args.allow_live_provider or os.getenv(ALLOW_ENV) != "1":
        return _blocked(args, "live_gate_not_enabled")
    return run_product_lab_proactive_send_skip_live_diagnostic(
        pre_delivery_review=_pre_delivery_review(),
        provider=_live_provider(profile),
        provider_mode=str(profile["provider_profile_id"]),
        live_invoked=True,
        provider_profile_id=str(profile["provider_profile_id"]),
        output_path=args.output,
    )


def _blocked(args: argparse.Namespace, reason: str) -> dict[str, Any]:
    return blocked_not_invoked_proactive_send_skip_live_artifact(
        reason=reason,
        provider_profile_id=str(args.provider_profile_id),
        output_path=args.output,
    )


def _pre_delivery_review() -> dict[str, Any]:
    return run_product_lab_proactive(
        turn={"session_id": "live-proactive-send-skip", "turn_id": "t1", "surface": "chat"},
        fixture_inputs=build_product_lab_fixture_inputs(),
        memory_context_pack=_memory_pack(),
        recommendation_artifact=_recommendation_artifact(),
        rescue_artifact=_rescue_artifact(),
    )["pre_delivery_review"]


def _memory_pack() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_memory_context_pack",
        "status": "pass",
        "selected_record_ids": ["memory-oatmeal"],
        "entries": [{"record_id": "memory-oatmeal", "intended_consumers": ["proactive"]}],
    }


def _recommendation_artifact() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_recommendation_runtime_artifact",
        "status": "pass",
        "recommendation_served_to_lab": True,
        "proactive_recommendation_candidate_allowed": True,
        "offer_synthesis": {"selected_primary": {"candidate_id": "memory-oatmeal"}},
    }


def _rescue_artifact() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_rescue_runtime_artifact",
        "status": "pass",
        "proposal_card": {"card_kind": "same_day_rescue_lab"},
    }


def _live_provider(profile: dict[str, object]) -> Any:
    from app.providers.builderspace_adapter import BuilderSpaceAdapter

    return BuilderSpaceAdapter(
        manager_model_override=str(profile["model_id"]),
        role_label=str(profile["role_label"]) + "_proactive_send_skip",
    )


if __name__ == "__main__":
    raise SystemExit(main())
