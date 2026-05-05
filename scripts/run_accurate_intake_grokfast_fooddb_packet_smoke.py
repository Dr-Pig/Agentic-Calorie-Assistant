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

from app.nutrition.application.grokfast_fooddb_packet_smoke import (  # noqa: E402
    GROKFAST_FOODDB_PACKET_PROFILE,
    build_fixture_manager_outputs,
    build_grokfast_fooddb_packet_diagnostic,
    build_live_manager_payload,
    build_packet_artifact_from_tool_evidence_result,
)
from app.nutrition.application.grokfast_fooddb_diagnostic_preflight import (  # noqa: E402
    is_grokfast_fooddb_preflight_clear,
)
from app.nutrition.application.grokfast_fooddb_profile_schema import (  # noqa: E402
    build_grokfast_fooddb_profile_schema,
    is_grokfast_fooddb_profile_constraints,
    profile_schema_transport_meta,
)
from app.providers.builderspace_adapter import BuilderSpaceAdapter, BuilderSpaceResponseError  # noqa: E402
from app.providers.builderspace_runtime_contract import response_schema_for_stage, validate_manager_payload  # noqa: E402
from app.providers.builderspace_transport import response_format_request_for_stage  # noqa: E402
from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT  # noqa: E402
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE  # noqa: E402
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_PACKET_SMOKE = ROOT / "artifacts" / "accurate_intake_fooddb_manager_packet_smoke.json"
DEFAULT_TOOL_EVIDENCE_RESULT = ROOT / "artifacts" / "accurate_intake_tool_evidence_result_smoke.json"
DEFAULT_PREFLIGHT = ROOT / "artifacts" / "accurate_intake_grokfast_fooddb_diagnostic_preflight.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_grokfast_fooddb_packet_smoke.json"

FOODDB_PACKET_MANAGER_SYSTEM_PROMPT = (
    SINGLE_MANAGER_SYSTEM_PROMPT
    + "\nFoodDB packet seam diagnostic: the user payload contains a read-only "
    "ToolEvidenceResult with compact FoodDB evidence packets. Use only packet evidence. Do not invent source IDs. "
    "Do not write ledger state. This is diagnostic-only and not readiness evidence.\n"
)


class FoodDBPacketProfileBuilderSpaceAdapter(BuilderSpaceAdapter):
    def _response_schema_for_stage(
        self,
        stage: str,
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return build_grokfast_fooddb_profile_schema(
            stage=stage,
            base_schema=response_schema_for_stage(stage, constraints),
            constraints=constraints,
        )

    def _response_format_request_for_stage(
        self,
        stage: str,
        constraints: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        response_format, transport_meta = response_format_request_for_stage(
            stage,
            constraints=constraints,
            schema=self._response_schema_for_stage(stage, constraints),
        )
        if is_grokfast_fooddb_profile_constraints(constraints):
            _apply_fooddb_profile_schema_name(response_format)
            transport_meta.update(profile_schema_transport_meta())
        return response_format, transport_meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run GrokFast Manager + FoodDB packet seam smoke."
    )
    parser.add_argument("--mode", choices=("fixture", "live"), default="fixture")
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--packet-smoke", default=str(DEFAULT_PACKET_SMOKE))
    parser.add_argument("--tool-evidence-result", default=None)
    parser.add_argument("--preflight-artifact", default=str(DEFAULT_PREFLIGHT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    packet_artifact = _load_packet_artifact(args)
    output_path = Path(args.output)

    if args.mode == "live" and not args.allow_live:
        artifact = {
            "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
            "classification": "live_diagnostic_only",
            "status": "blocked",
            "failure_family": "live_mode_requires_explicit_allow_live",
            "live_provider_used": False,
            "readiness_claimed": False,
            "self_use_approved": False,
            "production_selected": False,
            "runtime_mutation_attempted": False,
            "runtime_truth_changed": False,
            "provider_profile": dict(GROKFAST_FOODDB_PACKET_PROFILE),
        }
        write_json_artifact(output_path, artifact)
        return 2

    if args.mode == "live":
        preflight_path = Path(args.preflight_artifact)
        if not preflight_path.exists():
            artifact = _blocked_live_artifact(
                failure_family="missing_clear_grokfast_fooddb_preflight",
                preflight_artifact=str(preflight_path),
            )
            write_json_artifact(output_path, artifact)
            return 2
        preflight = read_json_artifact(preflight_path)
        if not is_grokfast_fooddb_preflight_clear(preflight):
            artifact = _blocked_live_artifact(
                failure_family="grokfast_fooddb_preflight_not_clear",
                preflight_artifact=str(preflight_path),
                preflight_status=preflight.get("status"),
                preflight_blockers=list(preflight.get("blockers") or []),
            )
            write_json_artifact(output_path, artifact)
            return 2

    if args.mode == "fixture":
        manager_outputs = build_fixture_manager_outputs(packet_artifact=packet_artifact)
        artifact = build_grokfast_fooddb_packet_diagnostic(
            packet_artifact=packet_artifact,
            manager_outputs=manager_outputs,
            live_provider_used=False,
            manager_contract_validator=_manager_contract_validation_errors,
        )
        write_json_artifact(output_path, artifact)
        _print_summary(output_path, artifact)
        return 0

    artifact, exit_code = asyncio.run(_run_live(packet_artifact=packet_artifact))
    write_json_artifact(output_path, artifact)
    _print_summary(output_path, artifact)
    return exit_code


async def _run_live(*, packet_artifact: dict[str, Any]) -> tuple[dict[str, Any], int]:
    adapter = FoodDBPacketProfileBuilderSpaceAdapter(
        manager_model_override=GROKFAST_FOODDB_PACKET_PROFILE["model"],
        role_label="fooddb_packet_smoke_manager",
    )
    readiness = adapter.readiness()
    if readiness.get("configured") is not True:
        artifact = build_grokfast_fooddb_packet_diagnostic(
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
                system_prompt=FOODDB_PACKET_MANAGER_SYSTEM_PROMPT,
                user_payload=build_live_manager_payload(packet_case=packet_case),
                stage=MANAGER_LOOP_STAGE,
                max_tokens=1800,
            )
        except BuilderSpaceResponseError as exc:
            manager_outputs.append(
                {
                    "case_id": packet_case.get("case_id"),
                    "manager_output": {},
                    "provider_trace": {
                        "provider_profile_id": GROKFAST_FOODDB_PACKET_PROFILE["provider_profile_id"],
                        "provider_profile_model": GROKFAST_FOODDB_PACKET_PROFILE["model"],
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
                        "provider_profile_id": GROKFAST_FOODDB_PACKET_PROFILE["provider_profile_id"],
                        "provider_profile_model": GROKFAST_FOODDB_PACKET_PROFILE["model"],
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
                    "provider_profile_id": GROKFAST_FOODDB_PACKET_PROFILE["provider_profile_id"],
                    "provider_profile_model": GROKFAST_FOODDB_PACKET_PROFILE["model"],
                    "provider_profile_role": GROKFAST_FOODDB_PACKET_PROFILE["provider_profile_role"],
                },
            }
        )

    artifact = build_grokfast_fooddb_packet_diagnostic(
        packet_artifact=packet_artifact,
        manager_outputs=manager_outputs,
        live_provider_used=True,
        manager_contract_validator=_manager_contract_validation_errors,
    )
    artifact["provider_readiness"] = readiness
    return artifact, 0


def _apply_fooddb_profile_schema_name(response_format: dict[str, Any]) -> None:
    if response_format.get("type") != "json_schema":
        return
    json_schema = response_format.get("json_schema")
    if not isinstance(json_schema, dict):
        return
    meta = profile_schema_transport_meta()
    json_schema["name"] = meta["schema_name"]


def _manager_contract_validation_errors(
    packet_case: dict[str, Any],
    manager_output: dict[str, Any],
) -> list[str]:
    try:
        validate_manager_payload(
            MANAGER_LOOP_STAGE,
            manager_output,
            constraints=build_live_manager_payload(packet_case=packet_case)["constraints"],
        )
    except Exception as exc:
        return [f"{type(exc).__name__}: {exc}"]
    return []


def _print_summary(output_path: Path, artifact: dict[str, Any]) -> None:
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": artifact.get("status"),
                "classification": artifact.get("classification"),
                "live_provider_used": artifact.get("live_provider_used"),
                "summary": artifact.get("summary"),
            },
            ensure_ascii=False,
        )
    )


def _blocked_live_artifact(
    *,
    failure_family: str,
    preflight_artifact: str,
    preflight_status: str | None = None,
    preflight_blockers: list[Any] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "classification": "live_diagnostic_only",
        "status": "blocked",
        "failure_family": failure_family,
        "live_provider_used": False,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
        "runtime_mutation_attempted": False,
        "runtime_truth_changed": False,
        "provider_profile": dict(GROKFAST_FOODDB_PACKET_PROFILE),
        "preflight_artifact": preflight_artifact,
        "preflight_status": preflight_status,
        "preflight_blockers": preflight_blockers or [],
    }


def _load_packet_artifact(args: argparse.Namespace) -> dict[str, Any]:
    if args.tool_evidence_result:
        return build_packet_artifact_from_tool_evidence_result(
            tool_evidence_artifact=read_json_artifact(Path(args.tool_evidence_result))
        )
    return read_json_artifact(Path(args.packet_smoke))


if __name__ == "__main__":
    raise SystemExit(main())
