from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.grokfast_websearch_packet_smoke import (  # noqa: E402
    GROKFAST_WEBSEARCH_PACKET_PROFILE,
    blocked_live_artifact,
    build_fixture_grokfast_websearch_manager_outputs,
    build_grokfast_websearch_packet_diagnostic,
    build_live_websearch_manager_payload,
)
from app.providers.builderspace_adapter import BuilderSpaceAdapter, BuilderSpaceResponseError  # noqa: E402
from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT  # noqa: E402
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE  # noqa: E402
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_MANAGER_PACKET = ROOT / "artifacts" / "accurate_intake_websearch_manager_packet_smoke.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_grokfast_websearch_packet_smoke.json"

WEBSEARCH_PACKET_MANAGER_SYSTEM_PROMPT = (
    SINGLE_MANAGER_SYSTEM_PROMPT
    + "\nWebSearch packet seam diagnostic: the user payload contains a compact, candidate-only "
    "WebSearch evidence packet. Use it only for source candidate review and disambiguation. "
    "Do not create nutrition truth, exact-card truth, FoodDB truth, item_results, ledger writes, "
    "or readiness claims.\n"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run GrokFast Manager + WebSearch packet seam smoke."
    )
    parser.add_argument("--mode", choices=("fixture", "live"), default="fixture")
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--manager-packet-artifact", default=str(DEFAULT_MANAGER_PACKET))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    packet_artifact = _load_packet_artifact(Path(args.manager_packet_artifact))
    output_path = Path(args.output)

    if args.mode == "live" and not args.allow_live:
        artifact = blocked_live_artifact()
        write_json_artifact(output_path, artifact)
        return 2

    if args.mode == "fixture":
        manager_outputs = build_fixture_grokfast_websearch_manager_outputs(
            packet_artifact=packet_artifact
        )
        artifact = build_grokfast_websearch_packet_diagnostic(
            packet_artifact=packet_artifact,
            manager_outputs=manager_outputs,
            live_provider_used=False,
        )
        write_json_artifact(output_path, artifact)
        _print_summary(output_path, artifact)
        return 0

    artifact, exit_code = asyncio.run(_run_live(packet_artifact=packet_artifact))
    write_json_artifact(output_path, artifact)
    _print_summary(output_path, artifact)
    return exit_code


async def _run_live(*, packet_artifact: dict[str, Any]) -> tuple[dict[str, Any], int]:
    adapter = BuilderSpaceAdapter(
        manager_model_override=GROKFAST_WEBSEARCH_PACKET_PROFILE["model"],
        role_label="websearch_packet_smoke_manager",
    )
    readiness = adapter.readiness()
    if readiness.get("configured") is not True:
        artifact = build_grokfast_websearch_packet_diagnostic(
            packet_artifact=packet_artifact,
            manager_outputs=[],
            live_provider_used=False,
            status="not_run_provider_not_configured",
            failure_family="provider_not_configured",
        )
        artifact["provider_readiness"] = readiness
        return artifact, 3

    manager_outputs: list[dict[str, Any]] = []
    for packet_case in packet_artifact.get("cases") or []:
        if not isinstance(packet_case, dict):
            continue
        try:
            parsed, trace = await adapter.complete_with_trace(
                system_prompt=WEBSEARCH_PACKET_MANAGER_SYSTEM_PROMPT,
                user_payload=build_live_websearch_manager_payload(packet_case=packet_case),
                stage=MANAGER_LOOP_STAGE,
                max_tokens=1600,
            )
        except BuilderSpaceResponseError as exc:
            manager_outputs.append(
                {
                    "case_id": packet_case.get("case_id"),
                    "manager_output": {},
                    "provider_trace": {
                        "provider_profile_id": GROKFAST_WEBSEARCH_PACKET_PROFILE[
                            "provider_profile_id"
                        ],
                        "provider_profile_model": GROKFAST_WEBSEARCH_PACKET_PROFILE["model"],
                        "failure_family": "provider_response_error",
                        "error": str(exc),
                        "trace": getattr(exc, "trace", {}),
                    },
                }
            )
            continue
        except Exception as exc:  # pragma: no cover - live diagnostic only
            manager_outputs.append(
                {
                    "case_id": packet_case.get("case_id"),
                    "manager_output": {},
                    "provider_trace": {
                        "provider_profile_id": GROKFAST_WEBSEARCH_PACKET_PROFILE[
                            "provider_profile_id"
                        ],
                        "provider_profile_model": GROKFAST_WEBSEARCH_PACKET_PROFILE["model"],
                        "failure_family": type(exc).__name__,
                        "error": str(exc),
                    },
                }
            )
            continue
        manager_outputs.append(
            {
                "case_id": packet_case.get("case_id"),
                "manager_output": parsed,
                "provider_trace": {
                    **(trace if isinstance(trace, dict) else {}),
                    "provider_profile_id": GROKFAST_WEBSEARCH_PACKET_PROFILE["provider_profile_id"],
                    "provider_profile_model": GROKFAST_WEBSEARCH_PACKET_PROFILE["model"],
                    "provider_profile_role": GROKFAST_WEBSEARCH_PACKET_PROFILE[
                        "provider_profile_role"
                    ],
                },
            }
        )

    artifact = build_grokfast_websearch_packet_diagnostic(
        packet_artifact=packet_artifact,
        manager_outputs=manager_outputs,
        live_provider_used=True,
    )
    artifact["provider_readiness"] = readiness
    return artifact, 0


def _load_packet_artifact(input_path: Path) -> dict[str, Any]:
    if input_path.exists():
        return read_json_artifact(input_path)

    from scripts.build_accurate_intake_websearch_manager_packet_smoke import (  # noqa: PLC0415
        main as build_manager_packet_smoke,
    )

    build_manager_packet_smoke(["--output", str(input_path)])
    return read_json_artifact(input_path)


def _print_summary(output_path: Path, artifact: dict[str, Any]) -> None:
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": artifact.get("status"),
                "classification": artifact.get("classification"),
                "live_provider_used": artifact.get("live_provider_used"),
                "live_websearch_used": artifact.get("live_websearch_used"),
                "summary": artifact.get("summary"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
