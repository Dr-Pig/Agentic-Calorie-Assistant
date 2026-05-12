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
from app.advanced_shadow_lab.product_lab_memory_record_live_edd_gate import (  # noqa: E402
    review_memory_record_live_edd_gate,
)
from app.advanced_shadow_lab.product_lab_memory_record_live_preflight import (  # noqa: E402
    build_memory_record_live_edd_preflight,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


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
        preflight = build_memory_record_live_edd_preflight(
            provider_mode="fake",
            allow_live_provider=False,
            env_live_gate_enabled=False,
            provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
        )
        artifact = run_memory_record_live_diagnostic(
            integrated_e2e_artifact=read_json_artifact(args.integrated_e2e_json),
            output_path=None,
            provider=FakeMemoryRecordDiagnosticProvider(),
            provider_mode="fake_provider_contract_test",
            provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
            live_invoked=False,
            source_integrated_e2e_path=args.integrated_e2e_json,
        )
        artifact = _attach_live_edd_gate(
            artifact=artifact,
            preflight=preflight,
            output_path=args.output,
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
    preflight = build_memory_record_live_edd_preflight(
        provider_mode="live",
        allow_live_provider=bool(args.allow_live_provider),
        env_live_gate_enabled=os.getenv(ALLOW_ENV) == "1",
        provider_profile_id=str(args.provider_profile_id),
    )
    try:
        profile, blockers = resolve_live_diagnostic_profile(str(args.provider_profile_id))
    except ValueError as exc:
        artifact = blocked_not_invoked_artifact(
            output_path=args.output,
            provider_profile_id=str(args.provider_profile_id),
            reason=str(exc),
        )
        return _attach_live_edd_gate(
            artifact=artifact,
            preflight=preflight,
            output_path=args.output,
        )
    if blockers:
        artifact = blocked_not_invoked_artifact(
            output_path=args.output,
            provider_profile_id=str(args.provider_profile_id),
            reason=";".join(blockers),
        )
        return _attach_live_edd_gate(
            artifact=artifact,
            preflight=preflight,
            output_path=args.output,
        )
    if preflight["status"] != "pass":
        artifact = blocked_not_invoked_artifact(
            output_path=args.output,
            provider_profile_id=str(args.provider_profile_id),
            reason=";".join(str(item) for item in preflight["blockers"]),
        )
        return _attach_live_edd_gate(
            artifact=artifact,
            preflight=preflight,
            output_path=args.output,
        )
    artifact = run_memory_record_live_diagnostic(
        integrated_e2e_artifact=read_json_artifact(args.integrated_e2e_json),
        output_path=None,
        provider=_live_provider(profile),
        provider_mode=str(profile["provider_profile_id"]),
        provider_profile_id=str(profile["provider_profile_id"]),
        live_invoked=True,
        source_integrated_e2e_path=args.integrated_e2e_json,
    )
    return _attach_live_edd_gate(
        artifact=artifact,
        preflight=preflight,
        output_path=args.output,
    )


def _attach_live_edd_gate(
    *,
    artifact: dict[str, Any],
    preflight: dict[str, Any],
    output_path: Path,
) -> dict[str, Any]:
    gate = review_memory_record_live_edd_gate(
        preflight_artifact=preflight,
        live_diagnostic_artifact=artifact,
    )
    artifact["live_edd_preflight"] = _preflight_summary(preflight)
    artifact["live_edd_gate"] = _gate_summary(gate)
    write_json_artifact(output_path, artifact)
    return artifact


def _preflight_summary(preflight: dict[str, Any]) -> dict[str, Any]:
    return {
        key: preflight[key]
        for key in (
            "artifact_type",
            "status",
            "reviewed_preflight_status",
            "provider_mode",
            "provider_profile_id",
            "fake_contract_preflight_pass",
            "live_provider_invocation_allowed",
            "live_milestone_preflight_ready",
            "blockers",
        )
    }


def _gate_summary(gate: dict[str, Any]) -> dict[str, Any]:
    return {
        key: gate[key]
        for key in (
            "artifact_type",
            "status",
            "reviewed_live_status",
            "diagnostic_evidence_class",
            "fake_contract_reviewed",
            "blocked_not_invoked_reviewed",
            "live_grokfast_reviewed",
            "live_milestone_complete",
            "live_completion_claim_allowed",
            "blockers",
        )
    }


def _live_provider(profile: dict[str, object]) -> Any:
    from app.providers.builderspace_adapter import BuilderSpaceAdapter

    return BuilderSpaceAdapter(
        manager_model_override=str(profile["model_id"]),
        role_label=str(profile["role_label"]) + "_memory_record_product_lab",
    )


if __name__ == "__main__":
    raise SystemExit(main())
