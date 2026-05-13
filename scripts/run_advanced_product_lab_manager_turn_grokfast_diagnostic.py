from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.advanced_shadow_lab.model_profiles import (  # noqa: E402
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    resolve_live_diagnostic_profile,
)
from app.advanced_shadow_lab.product_lab_manager_turn_grokfast_diagnostic import (  # noqa: E402
    blocked_not_invoked_manager_turn_grokfast_artifact,
    run_manager_turn_grokfast_diagnostic,
)
from app.advanced_shadow_lab.product_lab_manager_turn_live_fixture import (  # noqa: E402
    build_manager_turn_live_runtime_artifact,
)


ALLOW_ENV = "ADVANCED_PRODUCT_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC"


class FakeManagerTurnProvider:
    def readiness(self) -> dict[str, object]:
        return {"provider": "fake-manager-turn-grokfast", "configured": True}

    async def complete_with_trace(self, **_: object) -> tuple[dict[str, object], dict[str, object]]:
        return {
            "claim_scope": "diagnostic_only",
            "selected_capabilities": ["memory", "reusable_meal", "rescue"],
            "tool_call_order": ["memory.search", "reusable_meal.search", "rescue.run"],
            "manager_turn_summary": "Memory, reusable meal, and rescue returned to Manager.",
            "action_request": False,
            "delivery_request": False,
            "mutation_request": False,
            "risk_notes": "Diagnostic evidence only.",
        }, {"stage": "advanced_product_lab_manager_turn_diagnostic", "provider": "fake"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the advanced product-lab Manager-turn Grokfast diagnostic."
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--provider-mode", choices=("fake", "live"), default="fake")
    parser.add_argument("--allow-live-provider", action="store_true")
    parser.add_argument("--provider-profile-id", default=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID)
    args = parser.parse_args(argv)

    if args.provider_mode == "live":
        artifact = _live_artifact(args)
    else:
        artifact = _run_with_provider(
            args=args,
            provider=FakeManagerTurnProvider(),
            provider_mode="fake_provider_contract_test",
            live_invoked=False,
        )
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "status": artifact.get("status"),
                "provider_mode": artifact.get("provider_mode"),
                "live_invoked": artifact.get("live_invoked"),
                "live_grokfast_diagnostic_pass": artifact.get("live_grokfast_diagnostic_pass"),
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
        return _blocked(args, str(exc))
    if blockers:
        return _blocked(args, ";".join(blockers))
    if not args.allow_live_provider or os.getenv(ALLOW_ENV) != "1":
        return _blocked(args, "live_gate_not_enabled")
    return _run_with_provider(
        args=args,
        provider=_live_provider(profile),
        provider_mode=str(profile["provider_profile_id"]),
        live_invoked=True,
    )


def _run_with_provider(
    *,
    args: argparse.Namespace,
    provider: Any,
    provider_mode: str,
    live_invoked: bool,
) -> dict[str, Any]:
    with TemporaryDirectory(prefix="advanced-product-lab-manager-turn-") as tmp:
        runtime_artifact = build_manager_turn_live_runtime_artifact(Path(tmp))
        return run_manager_turn_grokfast_diagnostic(
            runtime_artifact=runtime_artifact,
            provider=provider,
            provider_mode=provider_mode,
            live_invoked=live_invoked,
            provider_profile_id=str(args.provider_profile_id),
            output_path=args.output,
        )


def _blocked(args: argparse.Namespace, reason: str) -> dict[str, Any]:
    return blocked_not_invoked_manager_turn_grokfast_artifact(
        reason=reason,
        provider_profile_id=str(args.provider_profile_id),
        output_path=args.output,
    )


def _live_provider(profile: dict[str, object]) -> Any:
    from app.providers.builderspace_adapter import BuilderSpaceAdapter

    return BuilderSpaceAdapter(
        manager_model_override=str(profile["model_id"]),
        role_label=str(profile["role_label"]) + "_manager_turn",
    )


if __name__ == "__main__":
    raise SystemExit(main())
