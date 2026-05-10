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

from app.advanced_shadow_lab.recommendation_copy_live_diagnostic import (  # noqa: E402
    run_recommendation_copy_live_diagnostic,
)
from app.advanced_shadow_lab.model_profiles import (  # noqa: E402
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    resolve_live_diagnostic_profile,
)


ALLOW_ENV = "ADVANCED_SHADOW_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC"
DEFAULT_OUTPUT = ROOT / "artifacts" / "advanced_shadow_recommendation_copy_live_diagnostic.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, artifact: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")


def _blocked_not_invoked(*, output: Path, reason: str) -> dict[str, Any]:
    artifact = {
        "artifact_type": "advanced_shadow_recommendation_copy_live_diagnostic_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked",
        "provider_mode": "not_invoked",
        "live_invoked": False,
        "live_provider_used": False,
        "provider_invoked": False,
        "blockers": [reason],
        "non_claims": [
            "not_runtime_activation_evidence",
            "not_product_readiness_evidence",
            "not_user_facing_activation",
        ],
        "mainline_runtime_connected": False,
        "mainline_route_or_api_mount_allowed": False,
        "delivery_attempted": False,
        "proactive_sent": False,
        "recommendation_served": False,
        "manager_context_packet_changed": False,
        "durable_product_memory_written": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
    }
    _write_json(output, artifact)
    return artifact


def _live_provider(profile: dict[str, object]) -> Any:
    from app.providers.builderspace_adapter import BuilderSpaceAdapter

    return BuilderSpaceAdapter(
        manager_model_override=str(profile["model_id"]),
        role_label=str(profile["role_label"]) + "_recommendation_copy",
    )


class FakeRecommendationCopyDiagnosticProvider:
    def readiness(self) -> dict[str, Any]:
        return {"provider": "fake-recommendation-copy", "configured": True}

    async def complete_with_trace(self, **_: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        return {
            "candidate_id": "golden-1",
            "draft_prompt": "Consider the selected option as a low-friction choice.",
            "reason_summary": "It matches the shadow candidate signals and remains review-only.",
            "claim_scope": "diagnostic_copy_only",
            "action_request": False,
            "delivery_request": False,
            "mutation_request": False,
            "reason_codes": ["review_only"],
        }, {"stage": "advanced_shadow_recommendation_copy_live_diagnostic", "provider": "fake"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run advanced shadow-lab recommendation copy live diagnostic."
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--provider-mode", choices=("fake", "live"), default="fake")
    parser.add_argument("--allow-live-provider", action="store_true")
    parser.add_argument("--provider-profile-id", default=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID)
    args = parser.parse_args()

    output = Path(args.output)
    if args.provider_mode == "live":
        try:
            profile, blockers = resolve_live_diagnostic_profile(str(args.provider_profile_id))
        except ValueError as exc:
            artifact = _blocked_not_invoked(output=output, reason=str(exc))
            print(
                json.dumps(
                    {
                        "artifact": str(output),
                        "status": artifact.get("status"),
                        "provider_mode": artifact.get("provider_mode"),
                        "live_invoked": artifact.get("live_invoked"),
                        "live_provider_used": artifact.get("live_provider_used"),
                        "blockers": artifact.get("blockers"),
                    },
                    ensure_ascii=False,
                )
            )
            return 0
        if blockers:
            artifact = _blocked_not_invoked(output=output, reason=";".join(blockers))
        elif not args.allow_live_provider or os.getenv(ALLOW_ENV) != "1":
            artifact = _blocked_not_invoked(output=output, reason="live_gate_not_enabled")
        else:
            artifact = run_recommendation_copy_live_diagnostic(
                recommendation_summary_report=_read_json(Path(args.input)),
                output_path=output,
                provider=_live_provider(profile),
                provider_mode=str(profile["provider_profile_id"]),
                live_invoked=True,
            )
    else:
        artifact = run_recommendation_copy_live_diagnostic(
            recommendation_summary_report=_read_json(Path(args.input)),
            output_path=output,
            provider=FakeRecommendationCopyDiagnosticProvider(),
            provider_mode="fake_provider_contract_test",
            live_invoked=False,
        )
    print(
        json.dumps(
            {
                "artifact": str(output),
                "status": artifact.get("status"),
                "provider_mode": artifact.get("provider_mode"),
                "live_invoked": artifact.get("live_invoked"),
                "live_provider_used": artifact.get("live_provider_used"),
                "blockers": artifact.get("blockers"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
