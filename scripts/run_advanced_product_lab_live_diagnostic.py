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
    advanced_lab_model_profile_policy,
    resolve_live_diagnostic_profile,
)
from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS  # noqa: E402
from app.advanced_shadow_lab.product_lab_live_diagnostic import (  # noqa: E402
    ARTIFACT_TYPE,
    run_product_lab_live_diagnostic,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


ALLOW_ENV = "ADVANCED_PRODUCT_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC"


class FakeProductLabDiagnosticProvider:
    def readiness(self) -> dict[str, Any]:
        return {"provider": "fake-product-lab-live-diagnostic", "configured": True}

    async def complete_with_trace(self, **_: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        return {
            "diagnostic_notes": "The simulated lab session preserved control behavior.",
            "risk_notes": "Use this as diagnostic evidence only.",
            "claim_scope": "diagnostic_only",
            "action_request": False,
            "delivery_request": False,
            "mutation_request": False,
            "reason_codes": ["review_only"],
        }, {"stage": "advanced_product_lab_live_diagnostic", "provider": "fake"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the advanced product-lab Grokfast live diagnostic."
    )
    parser.add_argument("--summary", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--provider-mode", choices=("fake", "live"), default="fake")
    parser.add_argument("--allow-live-provider", action="store_true")
    parser.add_argument("--provider-profile-id", default=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID)
    args = parser.parse_args(argv)

    output = Path(args.output)
    if args.provider_mode == "live":
        artifact = _live_artifact(args=args, output=output)
    else:
        artifact = run_product_lab_live_diagnostic(
            summary_artifact=read_json_artifact(Path(args.summary)),
            output_path=output,
            provider=FakeProductLabDiagnosticProvider(),
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


def _live_artifact(*, args: argparse.Namespace, output: Path) -> dict[str, Any]:
    try:
        profile, blockers = resolve_live_diagnostic_profile(str(args.provider_profile_id))
    except ValueError as exc:
        return _blocked_not_invoked(
            output=output,
            provider_profile_id=str(args.provider_profile_id),
            reason=str(exc),
        )
    if blockers:
        return _blocked_not_invoked(
            output=output,
            provider_profile_id=str(args.provider_profile_id),
            reason=";".join(blockers),
        )
    if not args.allow_live_provider or os.getenv(ALLOW_ENV) != "1":
        return _blocked_not_invoked(
            output=output,
            provider_profile_id=str(args.provider_profile_id),
            reason="live_gate_not_enabled",
        )
    return run_product_lab_live_diagnostic(
        summary_artifact=read_json_artifact(Path(args.summary)),
        output_path=output,
        provider=_live_provider(profile),
        provider_mode=str(profile["provider_profile_id"]),
        live_invoked=True,
    )


def _blocked_not_invoked(
    *, output: Path, provider_profile_id: str, reason: str
) -> dict[str, Any]:
    artifact = {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "blocked",
        **dict(FALSE_FLAGS),
        "provider_mode": "not_invoked",
        "provider_profile_id": provider_profile_id,
        "live_invoked": False,
        "live_provider_used": False,
        "provider_invoked": False,
        "model_profile_policy": advanced_lab_model_profile_policy(),
        "provider_trace_summary": {
            "stage": "not_invoked",
            "provider": "not_invoked",
            "usage_present": False,
        },
        "provider_error": {},
        "model_output_summary": {
            "diagnostic_notes_present": False,
            "risk_notes_present": False,
            "claim_scope": "",
        },
        "output_guard": {"status": "not_invoked", "blockers": []},
        "blockers": [reason],
        "non_claims": [
            "not_user_facing_activation",
            "not_mainline_runtime_activation",
            "not_scheduler_delivery",
            "not_durable_product_memory",
            "not_canonical_mutation",
            "not_kimi_activation",
            "not_provider_semantic_ownership",
        ],
        "mainline_runtime_connected": False,
        "production_db_migration_allowed": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "user_facing_behavior_changed": False,
    }
    write_json_artifact(output, artifact)
    return artifact


def _live_provider(profile: dict[str, object]) -> Any:
    from app.providers.builderspace_adapter import BuilderSpaceAdapter

    return BuilderSpaceAdapter(
        manager_model_override=str(profile["model_id"]),
        role_label=str(profile["role_label"]) + "_product_lab",
    )


if __name__ == "__main__":
    raise SystemExit(main())
