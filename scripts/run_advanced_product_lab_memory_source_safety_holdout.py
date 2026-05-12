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
from app.advanced_shadow_lab.product_lab_memory_record_live_preflight import (  # noqa: E402
    build_memory_record_live_edd_preflight,
)
from app.advanced_shadow_lab.product_lab_memory_source_safety_artifact import (  # noqa: E402
    blocked_not_invoked_source_safety_artifact,
)
from app.advanced_shadow_lab.product_lab_memory_source_safety_holdout import (  # noqa: E402
    FakeMemorySourceSafetyProvider,
    run_memory_source_safety_holdout,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


ALLOW_ENV = "ADVANCED_PRODUCT_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run memory source safety holdout diagnostic."
    )
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
        artifact = run_memory_source_safety_holdout(
            provider=FakeMemorySourceSafetyProvider(),
            provider_mode="fake_provider_contract_test",
            live_invoked=False,
            provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
        )
        _attach_preflight(artifact, preflight, args.output)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "status": artifact.get("status"),
                "provider_mode": artifact.get("provider_mode"),
                "live_invoked": artifact.get("live_invoked"),
                "live_source_safety_holdout_pass": artifact.get(
                    "live_source_safety_holdout_pass"
                ),
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
        return _blocked(args, preflight, str(exc))
    if blockers:
        return _blocked(args, preflight, ";".join(blockers))
    if preflight["status"] != "pass":
        return _blocked(args, preflight, ";".join(str(item) for item in preflight["blockers"]))
    artifact = run_memory_source_safety_holdout(
        provider=_live_provider(profile),
        provider_mode=str(profile["provider_profile_id"]),
        live_invoked=True,
        provider_profile_id=str(profile["provider_profile_id"]),
    )
    _attach_preflight(artifact, preflight, args.output)
    return artifact


def _blocked(
    args: argparse.Namespace,
    preflight: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    artifact = blocked_not_invoked_source_safety_artifact(
        reason=reason,
        provider_profile_id=str(args.provider_profile_id),
    )
    _attach_preflight(artifact, preflight, args.output)
    return artifact


def _attach_preflight(
    artifact: dict[str, Any],
    preflight: dict[str, Any],
    output: Path,
) -> None:
    artifact["live_edd_preflight"] = {
        key: preflight[key]
        for key in (
            "artifact_type",
            "status",
            "reviewed_preflight_status",
            "provider_mode",
            "provider_profile_id",
            "live_provider_invocation_allowed",
            "live_milestone_preflight_ready",
            "blockers",
        )
    }
    write_json_artifact(output, artifact)


def _live_provider(profile: dict[str, object]) -> Any:
    from app.providers.builderspace_adapter import BuilderSpaceAdapter

    return BuilderSpaceAdapter(
        manager_model_override=str(profile["model_id"]),
        role_label=str(profile["role_label"]) + "_memory_source_safety",
    )


if __name__ == "__main__":
    raise SystemExit(main())
