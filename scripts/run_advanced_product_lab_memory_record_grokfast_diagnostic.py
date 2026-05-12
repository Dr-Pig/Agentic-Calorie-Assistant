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
from app.advanced_shadow_lab.product_lab_memory_record_live_diagnostic import (  # noqa: E402
    blocked_not_invoked_artifact,
    run_memory_record_live_diagnostic,
)
from app.shared.infra.json_artifacts import read_json_artifact  # noqa: E402


ALLOW_ENV = "ADVANCED_PRODUCT_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC"


class FakeMemoryRecordDiagnosticProvider:
    def readiness(self) -> dict[str, Any]:
        return {"provider": "fake-memory-record-diagnostic", "configured": True}

    async def complete_with_trace(self, **_: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        return {
            "diagnostic_notes": "The MemoryRecord integrated lab chain is reviewable.",
            "risk_notes": "Diagnostic only; no outside-lab delivery or mutation.",
            "claim_scope": "diagnostic_only",
            "action_request": False,
            "delivery_request": False,
            "mutation_request": False,
            "reason_codes": ["memory_record_integrated_e2e"],
        }, {"stage": "memory_record_live_diagnostic", "provider": "fake"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the MemoryRecord integrated Grokfast diagnostic."
    )
    parser.add_argument("--integrated-e2e-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--provider-mode", choices=("fake", "live"), default="fake")
    parser.add_argument("--allow-live-provider", action="store_true")
    parser.add_argument("--provider-profile-id", default=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID)
    args = parser.parse_args(argv)

    if args.provider_mode == "live":
        artifact = _live_artifact(args)
    else:
        artifact = run_memory_record_live_diagnostic(
            integrated_e2e_artifact=read_json_artifact(args.integrated_e2e_json),
            output_path=args.output,
            provider=FakeMemoryRecordDiagnosticProvider(),
            provider_mode="fake_provider_contract_test",
            provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
            live_invoked=False,
            source_integrated_e2e_path=args.integrated_e2e_json,
        )
    print(
        json.dumps(
            {
                "artifact": str(args.output),
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


def _live_artifact(args: argparse.Namespace) -> dict[str, Any]:
    try:
        profile, blockers = resolve_live_diagnostic_profile(str(args.provider_profile_id))
    except ValueError as exc:
        return blocked_not_invoked_artifact(
            output_path=args.output,
            provider_profile_id=str(args.provider_profile_id),
            reason=str(exc),
        )
    if blockers:
        return blocked_not_invoked_artifact(
            output_path=args.output,
            provider_profile_id=str(args.provider_profile_id),
            reason=";".join(blockers),
        )
    if not args.allow_live_provider or os.getenv(ALLOW_ENV) != "1":
        return blocked_not_invoked_artifact(
            output_path=args.output,
            provider_profile_id=str(args.provider_profile_id),
            reason="live_gate_not_enabled",
        )
    return run_memory_record_live_diagnostic(
        integrated_e2e_artifact=read_json_artifact(args.integrated_e2e_json),
        output_path=args.output,
        provider=_live_provider(profile),
        provider_mode=str(profile["provider_profile_id"]),
        provider_profile_id=str(profile["provider_profile_id"]),
        live_invoked=True,
        source_integrated_e2e_path=args.integrated_e2e_json,
    )


def _live_provider(profile: dict[str, object]) -> Any:
    from app.providers.builderspace_adapter import BuilderSpaceAdapter

    return BuilderSpaceAdapter(
        manager_model_override=str(profile["model_id"]),
        role_label=str(profile["role_label"]) + "_memory_record_product_lab",
    )


if __name__ == "__main__":
    raise SystemExit(main())
