from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.recommendation.application.three_node_live_diagnostic import (  # noqa: E402
    FakeRecommendationThreeNodeDiagnosticProvider,
    run_recommendation_three_node_live_diagnostic,
)
from app.recommendation.application.three_node_live_provider_gate import (  # noqa: E402
    build_recommendation_three_node_live_provider_gate,
)
from app.recommendation.application.three_node_live_preflight import (  # noqa: E402
    build_recommendation_three_node_live_preflight,
)
from app.advanced_shadow_lab.model_profiles import (  # noqa: E402
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
)


def write_recommendation_three_node_live_diagnostic(
    output_path: Path,
    *,
    live: bool = False,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
) -> Path:
    preflight = build_recommendation_three_node_live_preflight(
        provider_profile_id=provider_profile_id
    )
    provider = FakeRecommendationThreeNodeDiagnosticProvider()
    provider_mode = "fake_provider_contract_test"
    live_invoked = False
    provider_gate: dict[str, object] = {}
    pre_run_blockers: list[str] = []
    if live:
        provider_gate = build_recommendation_three_node_live_provider_gate(
            provider_profile_id=provider_profile_id
        )
        pre_run_blockers = [str(item) for item in provider_gate.get("blockers") or []]
        live_provider = None
        if not pre_run_blockers:
            live_provider, readiness_blockers = _build_live_provider(provider_gate)
            pre_run_blockers.extend(readiness_blockers)
        provider_mode = (
            "live_builderspace_grokfast_diagnostic"
            if live_provider is not None
            else "live_provider_diagnostic_blocked"
        )
        provider = live_provider or provider
        live_invoked = live_provider is not None

    artifact = run_recommendation_three_node_live_diagnostic(
        preflight=preflight,
        provider=provider,
        provider_mode=provider_mode,
        live_invoked=live_invoked,
        live_requested=live,
        pre_run_blockers=pre_run_blockers,
        provider_gate=provider_gate,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def _build_live_provider(provider_gate: dict[str, object]) -> tuple[object | None, list[str]]:
    from app.providers.builderspace_adapter import BuilderSpaceAdapter

    provider = BuilderSpaceAdapter(
        manager_model_override=str(provider_gate.get("model_id") or ""),
        role_label=str(provider_gate.get("role_label") or "recommendation_live_diagnostic"),
    )
    readiness = provider.readiness()
    provider_gate["provider_readiness"] = {
        "provider": str(readiness.get("provider") or ""),
        "configured": readiness.get("configured") is True,
        "manager_model": str(readiness.get("manager_model") or ""),
        "role": str(readiness.get("role") or ""),
    }
    if readiness.get("configured") is not True:
        return None, ["provider.not_configured"]
    return provider, []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run dormant recommendation three-node diagnostic."
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--live", action="store_true")
    parser.add_argument(
        "--provider-profile-id",
        default=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    )
    args = parser.parse_args(argv)
    write_recommendation_three_node_live_diagnostic(
        Path(args.output),
        live=args.live,
        provider_profile_id=args.provider_profile_id,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main", "write_recommendation_three_node_live_diagnostic"]
