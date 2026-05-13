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
from app.nutrition.application.fooddb_live_diagnostic_source_refs import (  # noqa: E402
    attach_fooddb_live_upstream_refs,
)
from app.nutrition.application.grokfast_fooddb_live_runner_readiness_checks import (  # noqa: E402
    input_artifact_blockers,
    live_runner_readiness_input_blockers,
)
from app.providers.builderspace_adapter import BuilderSpaceAdapter, BuilderSpaceResponseError  # noqa: E402
from app.providers.builderspace_runtime_contract import validate_manager_payload  # noqa: E402
from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT  # noqa: E402
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE  # noqa: E402
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_PACKET_SMOKE = ROOT / "artifacts" / "accurate_intake_fooddb_manager_packet_smoke.json"
DEFAULT_TOOL_EVIDENCE_RESULT = ROOT / "artifacts" / "accurate_intake_tool_evidence_result_smoke.json"
DEFAULT_PREFLIGHT = ROOT / "artifacts" / "accurate_intake_grokfast_fooddb_diagnostic_preflight.json"
DEFAULT_ROUTER_READINESS = (
    ROOT / "artifacts" / "accurate_intake_food_evidence_retriever_router_readiness.json"
)
DEFAULT_LIVE_RUNNER_READINESS = (
    ROOT / "artifacts" / "accurate_intake_grokfast_fooddb_live_runner_readiness_packet.json"
)
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_grokfast_fooddb_packet_smoke.json"

FOODDB_PACKET_MANAGER_SYSTEM_PROMPT = (
    SINGLE_MANAGER_SYSTEM_PROMPT
    + "\nFoodDB packet seam diagnostic: the user payload contains a read-only "
    "ToolEvidenceResult with compact FoodDB evidence packets. Use only packet evidence. Do not invent source IDs. "
    "Do not write ledger state. This is diagnostic-only and not readiness evidence.\n"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run GrokFast Manager + FoodDB packet seam smoke."
    )
    parser.add_argument("--mode", choices=("fixture", "live"), default="fixture")
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--packet-smoke", default=str(DEFAULT_PACKET_SMOKE))
    parser.add_argument("--tool-evidence-result", default=None)
    parser.add_argument("--case-id", action="append", default=None)
    parser.add_argument("--preflight-artifact", default=str(DEFAULT_PREFLIGHT))
    parser.add_argument("--router-readiness-artifact", default=str(DEFAULT_ROUTER_READINESS))
    parser.add_argument(
        "--live-runner-readiness-artifact",
        default=str(DEFAULT_LIVE_RUNNER_READINESS),
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    packet_artifact = _load_packet_artifact(args)
    output_path = Path(args.output)
    include_upstream_refs = _should_include_upstream_refs(args)
    preflight: dict[str, Any] | None = None
    router_readiness: dict[str, Any] | None = None
    live_runner_readiness: dict[str, Any] | None = None

    selected_case_ids = _selected_case_ids(args.case_id)
    if selected_case_ids:
        packet_artifact, selection_blockers = _select_packet_cases(
            packet_artifact,
            selected_case_ids=selected_case_ids,
        )
        if selection_blockers:
            artifact = _blocked_case_selection_artifact(
                failure_family="unknown_case_id_selection",
                selected_case_ids=selected_case_ids,
                selection_blockers=selection_blockers,
            )
            write_json_artifact(output_path, artifact)
            _print_summary(output_path, artifact)
            return 2

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
        router_readiness_path = Path(args.router_readiness_artifact)
        live_runner_readiness_path = Path(args.live_runner_readiness_artifact)
        if not preflight_path.exists():
            artifact = _blocked_live_artifact(
                failure_family="missing_clear_grokfast_fooddb_preflight",
                preflight_artifact=str(preflight_path),
                router_readiness_artifact=str(router_readiness_path),
                live_runner_readiness_artifact=str(live_runner_readiness_path),
            )
            write_json_artifact(output_path, artifact)
            return 2
        preflight = read_json_artifact(preflight_path)
        if not is_grokfast_fooddb_preflight_clear(preflight):
            artifact = _blocked_live_artifact(
                failure_family="grokfast_fooddb_preflight_not_clear",
                preflight_artifact=str(preflight_path),
                router_readiness_artifact=str(router_readiness_path),
                live_runner_readiness_artifact=str(live_runner_readiness_path),
                preflight_status=preflight.get("status"),
                preflight_blockers=list(preflight.get("blockers") or []),
            )
            write_json_artifact(output_path, artifact)
            return 2
        if not router_readiness_path.exists():
            artifact = _blocked_live_artifact(
                failure_family="missing_clear_food_evidence_retriever_router_readiness",
                preflight_artifact=str(preflight_path),
                router_readiness_artifact=str(router_readiness_path),
                live_runner_readiness_artifact=str(live_runner_readiness_path),
            )
            write_json_artifact(output_path, artifact)
            return 2
        router_readiness = read_json_artifact(router_readiness_path)
        readiness_blockers = input_artifact_blockers(
            preflight_artifact=preflight,
            router_readiness_artifact=router_readiness,
        )
        if readiness_blockers:
            artifact = _blocked_live_artifact(
                failure_family="food_evidence_retriever_router_readiness_not_clear",
                preflight_artifact=str(preflight_path),
                router_readiness_artifact=str(router_readiness_path),
                live_runner_readiness_artifact=str(live_runner_readiness_path),
                router_readiness_status=router_readiness.get("status"),
                router_readiness_blockers=readiness_blockers,
            )
            write_json_artifact(output_path, artifact)
            return 2
        if not live_runner_readiness_path.exists():
            artifact = _blocked_live_artifact(
                failure_family="missing_clear_grokfast_fooddb_live_runner_readiness_packet",
                preflight_artifact=str(preflight_path),
                router_readiness_artifact=str(router_readiness_path),
                live_runner_readiness_artifact=str(live_runner_readiness_path),
            )
            write_json_artifact(output_path, artifact)
            return 2
        live_runner_readiness = read_json_artifact(live_runner_readiness_path)
        live_runner_blockers = live_runner_readiness_input_blockers(
            readiness_artifact=live_runner_readiness,
            preflight_artifact=preflight,
            router_readiness_artifact=router_readiness,
        )
        if live_runner_blockers:
            artifact = _blocked_live_artifact(
                failure_family="grokfast_fooddb_live_runner_readiness_packet_mismatch",
                preflight_artifact=str(preflight_path),
                router_readiness_artifact=str(router_readiness_path),
                live_runner_readiness_artifact=str(live_runner_readiness_path),
                readiness_status=live_runner_readiness.get("status"),
                readiness_blockers=live_runner_blockers,
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
        artifact = _attach_optional_upstream_refs(
            artifact=artifact,
            include_upstream_refs=include_upstream_refs,
            preflight_artifact=preflight,
            router_readiness_artifact=router_readiness,
            live_runner_readiness_artifact=live_runner_readiness,
            args=args,
        )
        write_json_artifact(output_path, artifact)
        _print_summary(output_path, artifact)
        return 0

    artifact, exit_code = asyncio.run(
        _run_live(
            packet_artifact=packet_artifact,
            preflight_artifact=preflight,
            router_readiness_artifact=router_readiness,
            live_runner_readiness_artifact=live_runner_readiness,
        )
    )
    write_json_artifact(output_path, artifact)
    _print_summary(output_path, artifact)
    return exit_code


async def _run_live(
    *,
    packet_artifact: dict[str, Any],
    preflight_artifact: dict[str, Any] | None,
    router_readiness_artifact: dict[str, Any] | None,
    live_runner_readiness_artifact: dict[str, Any] | None,
) -> tuple[dict[str, Any], int]:
    adapter = BuilderSpaceAdapter(
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
        artifact = attach_fooddb_live_upstream_refs(
            diagnostic_artifact=artifact,
            preflight_artifact=preflight_artifact,
            router_readiness_artifact=router_readiness_artifact,
            live_runner_readiness_artifact=live_runner_readiness_artifact,
        )
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
    artifact = attach_fooddb_live_upstream_refs(
        diagnostic_artifact=artifact,
        preflight_artifact=preflight_artifact,
        router_readiness_artifact=router_readiness_artifact,
        live_runner_readiness_artifact=live_runner_readiness_artifact,
    )
    return artifact, 0


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
    router_readiness_artifact: str | None = None,
    live_runner_readiness_artifact: str | None = None,
    preflight_status: str | None = None,
    preflight_blockers: list[Any] | None = None,
    router_readiness_status: str | None = None,
    router_readiness_blockers: list[Any] | None = None,
    readiness_status: str | None = None,
    readiness_blockers: list[Any] | None = None,
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
        "router_readiness_artifact": router_readiness_artifact,
        "router_readiness_status": router_readiness_status,
        "router_readiness_blockers": router_readiness_blockers or [],
        "live_runner_readiness_artifact": live_runner_readiness_artifact,
        "readiness_status": readiness_status,
        "readiness_blockers": readiness_blockers or [],
    }


def _blocked_case_selection_artifact(
    *,
    failure_family: str,
    selected_case_ids: list[str],
    selection_blockers: list[str],
) -> dict[str, Any]:
    return {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "classification": "live_diagnostic_only",
        "status": "blocked",
        "failure_family": failure_family,
        "selected_case_ids": selected_case_ids,
        "selection_blockers": selection_blockers,
        "live_provider_used": False,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
        "runtime_mutation_attempted": False,
        "runtime_truth_changed": False,
        "provider_profile": dict(GROKFAST_FOODDB_PACKET_PROFILE),
    }


def _load_packet_artifact(args: argparse.Namespace) -> dict[str, Any]:
    if args.tool_evidence_result:
        return build_packet_artifact_from_tool_evidence_result(
            tool_evidence_artifact=read_json_artifact(Path(args.tool_evidence_result))
        )
    return read_json_artifact(Path(args.packet_smoke))


def _selected_case_ids(values: list[str] | None) -> list[str]:
    selected: list[str] = []
    for value in values or []:
        case_id = str(value or "").strip()
        if case_id and case_id not in selected:
            selected.append(case_id)
    return selected


def _select_packet_cases(
    packet_artifact: dict[str, Any],
    *,
    selected_case_ids: list[str],
) -> tuple[dict[str, Any], list[str]]:
    available_case_ids = {
        str(case.get("case_id") or "").strip()
        for case in packet_artifact.get("cases") or []
        if isinstance(case, dict)
    }
    blockers = [f"unknown_case_id:{case_id}" for case_id in selected_case_ids if case_id not in available_case_ids]
    if blockers:
        return packet_artifact, blockers
    filtered_cases = [
        case
        for case in packet_artifact.get("cases") or []
        if isinstance(case, dict) and str(case.get("case_id") or "").strip() in selected_case_ids
    ]
    summary = dict(packet_artifact.get("summary") or {})
    summary["selected_case_count"] = len(filtered_cases)
    return {
        **packet_artifact,
        "cases": filtered_cases,
        "selected_case_ids": list(selected_case_ids),
        "summary": summary,
    }, []


def _should_include_upstream_refs(args: argparse.Namespace) -> bool:
    if args.mode == "live":
        return True
    return any(
        value != default
        for value, default in (
            (str(args.preflight_artifact), str(DEFAULT_PREFLIGHT)),
            (str(args.router_readiness_artifact), str(DEFAULT_ROUTER_READINESS)),
            (
                str(args.live_runner_readiness_artifact),
                str(DEFAULT_LIVE_RUNNER_READINESS),
            ),
        )
    )


def _attach_optional_upstream_refs(
    *,
    artifact: dict[str, Any],
    include_upstream_refs: bool,
    preflight_artifact: dict[str, Any] | None,
    router_readiness_artifact: dict[str, Any] | None,
    live_runner_readiness_artifact: dict[str, Any] | None,
    args: argparse.Namespace,
) -> dict[str, Any]:
    if not include_upstream_refs:
        return artifact
    return attach_fooddb_live_upstream_refs(
        diagnostic_artifact=artifact,
        preflight_artifact=preflight_artifact or _read_optional_artifact(args.preflight_artifact),
        router_readiness_artifact=router_readiness_artifact
        or _read_optional_artifact(args.router_readiness_artifact),
        live_runner_readiness_artifact=live_runner_readiness_artifact
        or _read_optional_artifact(args.live_runner_readiness_artifact),
    )


def _read_optional_artifact(path_value: str) -> dict[str, Any] | None:
    path = Path(path_value)
    return read_json_artifact(path) if path.exists() else None


if __name__ == "__main__":
    raise SystemExit(main())
