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

from app.advanced_shadow_lab.rescue_copy_live_diagnostic import (  # noqa: E402
    run_rescue_copy_live_diagnostic,
)


ALLOW_ENV = "ADVANCED_SHADOW_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC"
DEFAULT_OUTPUT = ROOT / "artifacts" / "advanced_shadow_rescue_copy_live_diagnostic.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, artifact: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")


def _blocked_not_invoked(*, output: Path, reason: str) -> dict[str, Any]:
    artifact = {
        "artifact_type": "advanced_shadow_rescue_copy_live_diagnostic_artifact",
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
        "rescue_committed": False,
        "proposal_committed": False,
        "manager_context_packet_changed": False,
        "durable_product_memory_written": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
    }
    _write_json(output, artifact)
    return artifact


def _live_provider(model: str) -> Any:
    from app.providers.builderspace_adapter import BuilderSpaceAdapter

    return BuilderSpaceAdapter(
        manager_model_override=model,
        role_label="advanced_shadow_lab_rescue_copy_live_diagnostic",
    )


class FakeRescueCopyDiagnosticProvider:
    def readiness(self) -> dict[str, Any]:
        return {"provider": "fake-rescue-copy", "configured": True}

    async def complete_with_trace(self, **_: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        return {
            "proposal_headline": "Recover the rest of the week with a small adjustment.",
            "proposal_summary": "Use a review-only offset and keep the tone neutral.",
            "coaching_frame": "Frame this as planning, not punishment.",
            "recommended_days": 2,
            "daily_kcal_adjustment": -150,
            "cap_mode": "standard_15_percent",
            "special_posture": "standard_spread",
            "claim_scope": "diagnostic_copy_only",
            "action_request": False,
            "delivery_request": False,
            "mutation_request": False,
            "reason_codes": ["review_only"],
        }, {"stage": "advanced_shadow_rescue_copy_live_diagnostic", "provider": "fake"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run advanced shadow-lab rescue copy live diagnostic."
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--provider-mode", choices=("fake", "live"), default="fake")
    parser.add_argument("--allow-live-provider", action="store_true")
    parser.add_argument("--model", default=os.getenv("BUILDERSPACE_MANAGER_MODEL", "grok-4-fast"))
    args = parser.parse_args()

    output = Path(args.output)
    if args.provider_mode == "live":
        if not args.allow_live_provider or os.getenv(ALLOW_ENV) != "1":
            artifact = _blocked_not_invoked(output=output, reason="live_gate_not_enabled")
        else:
            artifact = run_rescue_copy_live_diagnostic(
                rescue_shaping_input_packet=_read_json(Path(args.input)),
                output_path=output,
                provider=_live_provider(str(args.model)),
                provider_mode="builderspace_live_diagnostic",
                live_invoked=True,
            )
    else:
        artifact = run_rescue_copy_live_diagnostic(
            rescue_shaping_input_packet=_read_json(Path(args.input)),
            output_path=output,
            provider=FakeRescueCopyDiagnosticProvider(),
            provider_mode="fake_provider_contract_test",
            live_invoked=False,
        )
    print(json.dumps({
        "artifact": str(output),
        "status": artifact.get("status"),
        "provider_mode": artifact.get("provider_mode"),
        "live_invoked": artifact.get("live_invoked"),
        "live_provider_used": artifact.get("live_provider_used"),
        "blockers": artifact.get("blockers"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
