from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.grokfast_websearch_packet_diagnostic import (  # noqa: E402
    GROKFAST_WEBSEARCH_PACKET_PROFILE,
    build_fixture_manager_outputs,
    build_grokfast_websearch_packet_diagnostic,
    build_live_manager_payload,
)
from app.nutrition.application.websearch_live_extract_preflight import (  # noqa: E402
    is_websearch_live_extract_preflight_clear,
)
from app.nutrition.application.websearch_live_runner_readiness_packet import (  # noqa: E402
    live_runner_readiness_input_blockers,
)
from app.nutrition.application.websearch_preflight_digest import (  # noqa: E402
    websearch_live_extract_preflight_digest,
)
from app.providers.builderspace_adapter import BuilderSpaceAdapter, BuilderSpaceResponseError  # noqa: E402
from app.providers.builderspace_runtime_contract import validate_manager_payload  # noqa: E402
from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT  # noqa: E402
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE  # noqa: E402
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_REVIEW_PACKET = (
    ROOT / "artifacts" / "accurate_intake_websearch_exact_candidate_review_packet.json"
)
DEFAULT_PREFLIGHT = ROOT / "artifacts" / "accurate_intake_websearch_live_extract_preflight.json"
DEFAULT_CHAIN_STATUS = (
    ROOT / "artifacts" / "accurate_intake_websearch_exact_candidate_chain_status.json"
)
DEFAULT_RUNNER_READINESS = (
    ROOT / "artifacts" / "accurate_intake_websearch_live_runner_readiness_packet.json"
)
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_grokfast_websearch_packet_smoke.json"

WEBSEARCH_PACKET_MANAGER_SYSTEM_PROMPT = (
    SINGLE_MANAGER_SYSTEM_PROMPT
    + "\nWebSearch packet seam diagnostic: the user payload contains a read-only "
    "exact-card review packet with candidate extracted fields. Use only packet references. "
    "Do not create exact-card truth, do not write ledger state, and do not claim readiness.\n"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run GrokFast Manager + WebSearch review packet seam smoke."
    )
    parser.add_argument("--mode", choices=("fixture", "live"), default="fixture")
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--review-packet-artifact", default=str(DEFAULT_REVIEW_PACKET))
    parser.add_argument("--preflight-artifact", default=str(DEFAULT_PREFLIGHT))
    parser.add_argument("--exact-candidate-chain-status-artifact", default=str(DEFAULT_CHAIN_STATUS))
    parser.add_argument("--live-runner-readiness-artifact", default=str(DEFAULT_RUNNER_READINESS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    review_packet_artifact = read_json_artifact(Path(args.review_packet_artifact))
    output_path = Path(args.output)
    preflight_ref: dict[str, Any] | None = None
    chain_status_ref: dict[str, Any] | None = None

    if args.mode == "live" and not args.allow_live:
        artifact = _blocked_live_artifact(
            failure_family="live_mode_requires_explicit_allow_live",
            preflight_artifact=str(args.preflight_artifact),
        )
        write_json_artifact(output_path, artifact)
        return 2

    if args.mode == "live":
        preflight_path = Path(args.preflight_artifact)
        chain_status_path = Path(args.exact_candidate_chain_status_artifact)
        readiness_path = Path(args.live_runner_readiness_artifact)
        if not preflight_path.exists():
            artifact = _blocked_live_artifact(
                failure_family="missing_clear_websearch_live_extract_preflight",
                preflight_artifact=str(preflight_path),
                exact_candidate_chain_status_artifact=str(chain_status_path),
                live_runner_readiness_artifact=str(readiness_path),
            )
            write_json_artifact(output_path, artifact)
            return 2
        preflight = read_json_artifact(preflight_path)
        if not is_websearch_live_extract_preflight_clear(preflight):
            artifact = _blocked_live_artifact(
                failure_family="websearch_live_extract_preflight_not_clear",
                preflight_artifact=str(preflight_path),
                exact_candidate_chain_status_artifact=str(chain_status_path),
                live_runner_readiness_artifact=str(readiness_path),
                preflight_status=preflight.get("status"),
                preflight_blockers=list(preflight.get("blockers") or []),
            )
            write_json_artifact(output_path, artifact)
            return 2
        if not _preflight_authorizes_review_packet(
            preflight=preflight,
            review_packet_artifact=review_packet_artifact,
        ):
            artifact = _blocked_live_artifact(
                failure_family="websearch_live_preflight_review_packet_mismatch",
                preflight_artifact=str(preflight_path),
                exact_candidate_chain_status_artifact=str(chain_status_path),
                live_runner_readiness_artifact=str(readiness_path),
                preflight_status=preflight.get("status"),
                preflight_blockers=["preflight_review_packet_refs_mismatch"],
            )
            write_json_artifact(output_path, artifact)
            return 2
        preflight_ref = _preflight_ref(preflight)
        if not chain_status_path.exists():
            artifact = _blocked_live_artifact(
                failure_family="missing_clear_websearch_exact_candidate_chain_status",
                preflight_artifact=str(preflight_path),
                exact_candidate_chain_status_artifact=str(chain_status_path),
                live_runner_readiness_artifact=str(readiness_path),
            )
            write_json_artifact(output_path, artifact)
            return 2
        chain_status = read_json_artifact(chain_status_path)
        if not _is_exact_candidate_chain_status_clear(chain_status):
            artifact = _blocked_live_artifact(
                failure_family="websearch_exact_candidate_chain_status_not_clear",
                preflight_artifact=str(preflight_path),
                exact_candidate_chain_status_artifact=str(chain_status_path),
                live_runner_readiness_artifact=str(readiness_path),
                chain_status_status=chain_status.get("status"),
                chain_status_blockers=list(chain_status.get("blockers") or []),
            )
            write_json_artifact(output_path, artifact)
            return 2
        if not _chain_status_authorizes_review_packet(
            chain_status=chain_status,
            review_packet_artifact=review_packet_artifact,
        ):
            artifact = _blocked_live_artifact(
                failure_family="websearch_exact_candidate_chain_review_packet_mismatch",
                preflight_artifact=str(preflight_path),
                exact_candidate_chain_status_artifact=str(chain_status_path),
                live_runner_readiness_artifact=str(readiness_path),
                chain_status_status=chain_status.get("status"),
                chain_status_blockers=["chain_status_review_packet_refs_mismatch"],
            )
            write_json_artifact(output_path, artifact)
            return 2
        chain_status_ref = _chain_status_ref(chain_status)
        if not readiness_path.exists():
            artifact = _blocked_live_artifact(
                failure_family="missing_clear_websearch_live_runner_readiness_packet",
                preflight_artifact=str(preflight_path),
                exact_candidate_chain_status_artifact=str(chain_status_path),
                live_runner_readiness_artifact=str(readiness_path),
            )
            write_json_artifact(output_path, artifact)
            return 2
        readiness = read_json_artifact(readiness_path)
        readiness_blockers = live_runner_readiness_input_blockers(
            readiness_artifact=readiness,
            review_packet_artifact=review_packet_artifact,
            preflight_artifact=preflight,
            exact_candidate_chain_status_artifact=chain_status,
        )
        if readiness_blockers:
            artifact = _blocked_live_artifact(
                failure_family="websearch_live_runner_readiness_packet_mismatch",
                preflight_artifact=str(preflight_path),
                exact_candidate_chain_status_artifact=str(chain_status_path),
                live_runner_readiness_artifact=str(readiness_path),
                readiness_status=readiness.get("status"),
                readiness_blockers=readiness_blockers,
            )
            write_json_artifact(output_path, artifact)
            return 2

    if args.mode == "fixture":
        manager_outputs = build_fixture_manager_outputs(
            review_packet_artifact=review_packet_artifact
        )
        artifact = build_grokfast_websearch_packet_diagnostic(
            review_packet_artifact=review_packet_artifact,
            manager_outputs=manager_outputs,
            live_provider_used=False,
            manager_contract_validator=_manager_contract_validation_errors,
        )
        write_json_artifact(output_path, artifact)
        _print_summary(output_path, artifact)
        return 0

    artifact, exit_code = asyncio.run(
        _run_live(
            review_packet_artifact=review_packet_artifact,
            preflight_ref=preflight_ref,
            chain_status_ref=chain_status_ref,
        )
    )
    write_json_artifact(output_path, artifact)
    _print_summary(output_path, artifact)
    return exit_code


async def _run_live(
    *,
    review_packet_artifact: dict[str, Any],
    preflight_ref: dict[str, Any] | None,
    chain_status_ref: dict[str, Any] | None,
) -> tuple[dict[str, Any], int]:
    adapter = BuilderSpaceAdapter(
        manager_model_override=GROKFAST_WEBSEARCH_PACKET_PROFILE["model"],
        role_label="websearch_packet_smoke_manager",
    )
    readiness = adapter.readiness()
    if readiness.get("configured") is not True:
        artifact = build_grokfast_websearch_packet_diagnostic(
            review_packet_artifact=review_packet_artifact,
            manager_outputs=[],
            live_provider_used=False,
            status="not_run_provider_not_configured",
            failure_family="provider_not_configured",
        )
        artifact["provider_readiness"] = readiness
        artifact["preflight_ref"] = preflight_ref or {}
        artifact["exact_candidate_chain_ref"] = chain_status_ref or {}
        return artifact, 3

    manager_outputs: list[dict[str, Any]] = []
    for packet in review_packet_artifact.get("review_packets") or []:
        if not isinstance(packet, dict):
            continue
        try:
            parsed, trace = await adapter.complete_with_trace(
                system_prompt=WEBSEARCH_PACKET_MANAGER_SYSTEM_PROMPT,
                user_payload=build_live_manager_payload(review_packet=packet),
                stage=MANAGER_LOOP_STAGE,
                max_tokens=1400,
            )
        except BuilderSpaceResponseError as exc:
            manager_outputs.append(_provider_error_output(packet=packet, exc=exc))
            continue
        except Exception as exc:  # pragma: no cover - live diagnostic only
            manager_outputs.append(
                {
                    "packet_id": packet.get("packet_id"),
                    "manager_output": {},
                    "provider_trace": {
                        "provider_profile_id": GROKFAST_WEBSEARCH_PACKET_PROFILE["provider_profile_id"],
                        "provider_profile_model": GROKFAST_WEBSEARCH_PACKET_PROFILE["model"],
                        "failure_family": type(exc).__name__,
                        "error": str(exc),
                    },
                }
            )
            continue
        manager_outputs.append(
            {
                "packet_id": packet.get("packet_id"),
                "manager_output": parsed,
                "provider_trace": {
                    **(trace if isinstance(trace, dict) else {}),
                    "provider_profile_id": GROKFAST_WEBSEARCH_PACKET_PROFILE["provider_profile_id"],
                    "provider_profile_model": GROKFAST_WEBSEARCH_PACKET_PROFILE["model"],
                    "provider_profile_role": GROKFAST_WEBSEARCH_PACKET_PROFILE["provider_profile_role"],
                },
            }
        )

    artifact = build_grokfast_websearch_packet_diagnostic(
        review_packet_artifact=review_packet_artifact,
        manager_outputs=manager_outputs,
        live_provider_used=True,
        manager_contract_validator=_manager_contract_validation_errors,
    )
    artifact["provider_readiness"] = readiness
    artifact["preflight_ref"] = preflight_ref or {}
    artifact["exact_candidate_chain_ref"] = chain_status_ref or {}
    return artifact, 0


def _provider_error_output(*, packet: dict[str, Any], exc: BuilderSpaceResponseError) -> dict[str, Any]:
    return {
        "packet_id": packet.get("packet_id"),
        "manager_output": {},
        "provider_trace": {
            "provider_profile_id": GROKFAST_WEBSEARCH_PACKET_PROFILE["provider_profile_id"],
            "provider_profile_model": GROKFAST_WEBSEARCH_PACKET_PROFILE["model"],
            "failure_family": "provider_response_error",
            "error": str(exc),
            "trace": getattr(exc, "trace", {}),
        },
    }


def _manager_contract_validation_errors(
    review_packet: dict[str, Any],
    manager_output: dict[str, Any],
) -> list[str]:
    try:
        validate_manager_payload(
            MANAGER_LOOP_STAGE,
            manager_output,
            constraints=build_live_manager_payload(review_packet=review_packet)["constraints"],
        )
    except Exception as exc:
        return [f"{type(exc).__name__}: {exc}"]
    return []


def _preflight_authorizes_review_packet(
    *,
    preflight: dict[str, Any],
    review_packet_artifact: dict[str, Any],
) -> bool:
    preflight_refs = {
        (
            str(item.get("packet_id") or "").strip(),
            str(item.get("source_url") or "").strip(),
            str(item.get("canonical_name") or "").strip(),
            str(item.get("packet_digest") or "").strip(),
        )
        for item in preflight.get("review_packet_refs") or []
        if isinstance(item, dict)
    }
    review_refs = {
        (
            str(item.get("packet_id") or "").strip(),
            str(item.get("source_url") or "").strip(),
            str(item.get("canonical_name") or "").strip(),
            _review_packet_digest(item),
        )
        for item in review_packet_artifact.get("review_packets") or []
        if isinstance(item, dict)
    }
    return bool(preflight_refs) and preflight_refs == review_refs


def _preflight_ref(preflight: dict[str, Any]) -> dict[str, Any]:
    summary = preflight.get("summary") if isinstance(preflight.get("summary"), dict) else {}
    return {
        "preflight_ref_source": "run_accurate_intake_grokfast_websearch_packet_smoke",
        "artifact_type": preflight.get("artifact_type"),
        "status": preflight.get("status"),
        "ready_for_live_extract_diagnostic": preflight.get("ready_for_live_extract_diagnostic"),
        "ready_for_runtime_truth": preflight.get("ready_for_runtime_truth"),
        "review_packet_authorized": True,
        "review_packet_count": summary.get("review_packet_count"),
        "case_matrix_case_count": summary.get("case_matrix_case_count"),
        "case_matrix_fixed_required_cases": summary.get("case_matrix_fixed_required_cases"),
        "case_matrix_negative_case_count": summary.get("case_matrix_negative_case_count"),
        "case_matrix_modifier_guard_cases": summary.get("case_matrix_modifier_guard_cases"),
        "case_matrix_live_provider_invoked": summary.get("case_matrix_live_provider_invoked"),
        "case_matrix_websearch_invoked": summary.get("case_matrix_websearch_invoked"),
        "preflight_artifact_digest_algorithm": "sha256",
        "preflight_artifact_digest_scope": "semantic_preflight_without_generated_at_utc",
        "preflight_artifact_digest": websearch_live_extract_preflight_digest(preflight),
    }


def _is_exact_candidate_chain_status_clear(chain_status: dict[str, Any]) -> bool:
    return (
        chain_status.get("artifact_type")
        == "accurate_intake_websearch_exact_candidate_chain_status_v1"
        and chain_status.get("status") == "pass"
        and chain_status.get("ready_for_live_diagnostic") is True
        and chain_status.get("ready_for_runtime_truth") is False
        and chain_status.get("runtime_truth_changed") is False
        and chain_status.get("runtime_mutation_allowed") is False
        and chain_status.get("live_websearch_used") is False
        and chain_status.get("live_extract_used") is False
        and chain_status.get("live_provider_used") is False
        and chain_status.get("readiness_claimed") is False
    )


def _chain_status_authorizes_review_packet(
    *,
    chain_status: dict[str, Any],
    review_packet_artifact: dict[str, Any],
) -> bool:
    proof = chain_status.get("chain_proof") if isinstance(chain_status.get("chain_proof"), dict) else {}
    chain_review_ids = {
        str(packet_id or "").strip()
        for packet_id in proof.get("review_packet_ids") or []
        if str(packet_id or "").strip()
    }
    review_ids = {
        str(item.get("packet_id") or "").strip()
        for item in review_packet_artifact.get("review_packets") or []
        if isinstance(item, dict) and str(item.get("packet_id") or "").strip()
    }
    return bool(chain_review_ids) and chain_review_ids == review_ids


def _chain_status_ref(chain_status: dict[str, Any]) -> dict[str, Any]:
    summary = chain_status.get("summary") if isinstance(chain_status.get("summary"), dict) else {}
    return {
        "chain_ref_source": "run_accurate_intake_grokfast_websearch_packet_smoke",
        "artifact_type": chain_status.get("artifact_type"),
        "status": chain_status.get("status"),
        "ready_for_live_diagnostic": chain_status.get("ready_for_live_diagnostic"),
        "ready_for_runtime_truth": chain_status.get("ready_for_runtime_truth"),
        "review_packet_authorized": True,
        "review_packet_count": summary.get("review_packet_count"),
        "preflight_review_ref_count": summary.get("preflight_review_ref_count"),
    }


def _review_packet_digest(packet: dict[str, Any]) -> str:
    payload = json.dumps(packet, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _blocked_live_artifact(
    *,
    failure_family: str,
    preflight_artifact: str,
    exact_candidate_chain_status_artifact: str | None = None,
    live_runner_readiness_artifact: str | None = None,
    preflight_status: str | None = None,
    preflight_blockers: list[Any] | None = None,
    chain_status_status: str | None = None,
    chain_status_blockers: list[Any] | None = None,
    readiness_status: str | None = None,
    readiness_blockers: list[Any] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "classification": "live_diagnostic_only",
        "status": "blocked",
        "failure_family": failure_family,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
        "runtime_mutation_attempted": False,
        "runtime_truth_changed": False,
        "provider_profile": dict(GROKFAST_WEBSEARCH_PACKET_PROFILE),
        "preflight_artifact": preflight_artifact,
        "preflight_status": preflight_status,
        "preflight_blockers": preflight_blockers or [],
        "exact_candidate_chain_status_artifact": exact_candidate_chain_status_artifact,
        "exact_candidate_chain_status": chain_status_status,
        "exact_candidate_chain_blockers": chain_status_blockers or [],
        "live_runner_readiness_artifact": live_runner_readiness_artifact,
        "live_runner_readiness_status": readiness_status,
        "live_runner_readiness_blockers": readiness_blockers or [],
    }


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


if __name__ == "__main__":
    raise SystemExit(main())
