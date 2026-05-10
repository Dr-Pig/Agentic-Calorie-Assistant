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

from app.advanced_shadow_lab.llm_node_contract import (  # noqa: E402
    blocked_llm_node_artifact,
    build_recommendation_offer_synthesis_node_input,
    run_advanced_shadow_llm_node,
)
from app.advanced_shadow_lab.llm_node_fake_provider import (  # noqa: E402
    FakeAdvancedShadowLLMNodeProvider,
)
from app.advanced_shadow_lab.model_profiles import (  # noqa: E402
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    resolve_live_diagnostic_profile,
)


ALLOW_ENV = "ADVANCED_SHADOW_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC"
DEFAULT_OUTPUT = ROOT / "artifacts" / "advanced_shadow_llm_node_diagnostic.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one dormant advanced shadow-lab LLM node diagnostic."
    )
    parser.add_argument("--vertical-proof-json", required=True)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--provider-mode", choices=("fake", "live"), default="fake")
    parser.add_argument("--allow-live-provider", action="store_true")
    parser.add_argument("--provider-profile-id", default=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID)
    args = parser.parse_args(argv)

    output = Path(args.output)
    if args.provider_mode == "live":
        blocked = _live_blocker(
            allow_live_provider=bool(args.allow_live_provider),
            provider_profile_id=str(args.provider_profile_id),
        )
        if blocked:
            artifact = blocked_llm_node_artifact(
                reason=blocked,
                provider_profile_id=str(args.provider_profile_id),
                output_path=output,
            )
            print(_summary(output, artifact))
            return 0
        profile, _ = resolve_live_diagnostic_profile(str(args.provider_profile_id))
        provider = _live_provider(profile)
        provider_mode = str(profile["provider_profile_id"])
        live_invoked = True
    else:
        profile = _fake_profile()
        provider = FakeAdvancedShadowLLMNodeProvider()
        provider_mode = "fake_provider_contract_test"
        live_invoked = False

    artifact = run_advanced_shadow_llm_node(
        node_input=build_recommendation_offer_synthesis_node_input(
            _read_json(Path(args.vertical_proof_json))
        ),
        provider=provider,
        provider_profile=profile,
        provider_mode=provider_mode,
        live_invoked=live_invoked,
        output_path=output,
    )
    print(_summary(output, artifact))
    return 0


def _live_blocker(*, allow_live_provider: bool, provider_profile_id: str) -> str:
    try:
        _, blockers = resolve_live_diagnostic_profile(provider_profile_id)
    except ValueError as exc:
        return str(exc)
    if blockers:
        return ";".join(blockers)
    if not allow_live_provider or os.getenv(ALLOW_ENV) != "1":
        return "live_gate_not_enabled"
    return ""


def _live_provider(profile: dict[str, object]) -> Any:
    from app.providers.builderspace_adapter import BuilderSpaceAdapter

    return BuilderSpaceAdapter(
        manager_model_override=str(profile["model_id"]),
        role_label=str(profile["role_label"]) + "_advanced_shadow_llm_node",
    )


def _fake_profile() -> dict[str, object]:
    return {
        "provider_profile_id": "fake-advanced-shadow-node",
        "provider_family": "fake",
        "model_id": "fake-llm",
        "role": "diagnostic_live_llm",
        "live_diagnostic_allowed": False,
        "kimi_live_calls_allowed": False,
        "production_selected": False,
        "provider_specific_product_semantics_allowed": False,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _summary(path: Path, artifact: dict[str, Any]) -> str:
    return json.dumps(
        {
            "artifact": str(path),
            "status": artifact.get("status"),
            "provider_mode": artifact.get("provider_mode"),
            "live_invoked": artifact.get("live_invoked"),
            "live_provider_used": artifact.get("live_provider_used"),
            "blockers": artifact.get("blockers"),
        },
        ensure_ascii=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
