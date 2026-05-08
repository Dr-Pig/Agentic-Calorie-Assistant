from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_context_live_diagnostic_anti_overfit_guard import (  # noqa: E402
    build_context_live_diagnostic_anti_overfit_guard_artifact,
)
from app.composition.accurate_intake_context_live_diagnostic_canary import (  # noqa: E402
    DEFAULT_CONTEXT_LIVE_PROVIDER_PROFILE_ID,
    build_missing_token_report,
)
from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (  # noqa: E402
    build_context_live_diagnostic_case_matrix_artifact,
)
from app.composition.accurate_intake_context_live_diagnostic_holdout_plan import (  # noqa: E402
    build_context_live_diagnostic_holdout_plan_artifact,
)
from app.composition.accurate_intake_context_live_diagnostic_review_pack import (  # noqa: E402
    build_context_live_diagnostic_review_pack_artifact,
)
from app.composition.accurate_intake_context_live_diagnostic_stage_gate import (  # noqa: E402
    LIVE_STAGES,
    build_context_live_diagnostic_stage_gate_artifact,
)
from app.composition.accurate_intake_context_live_provider_input_preflight import (  # noqa: E402
    build_context_live_provider_input_preflight_artifact,
)
from app.composition.accurate_intake_context_live_response_contract_dry_run import (  # noqa: E402
    build_context_live_response_contract_dry_run_artifact,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402
from scripts.run_accurate_intake_context_live_diagnostic_canary import (  # noqa: E402
    run_context_live_diagnostic_canary,
    select_context_live_provider_inputs,
)


DEFAULT_ARTIFACT_DIR = ROOT / "artifacts"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_context_live_diagnostic_gate.json"


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _load_local_env(path: Path) -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(path, override=False, encoding="utf-8-sig")
        return
    except ModuleNotFoundError:
        pass
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _not_allowed_report(
    *,
    context_live_provider_input_preflight: dict[str, Any],
    provider_profile_id: str,
) -> dict[str, Any]:
    report = build_missing_token_report(
        context_live_provider_input_preflight=context_live_provider_input_preflight,
        provider_profile_id=provider_profile_id,
    )
    report.update(
        {
            "failure_family": "live_provider_not_allowed_by_gate",
            "blockers": ["live_provider_not_allowed_by_gate"],
            "live_provider_allowed": False,
        }
    )
    return _json_safe(report)


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return dict(payload) if isinstance(payload, dict) else {"artifact_type": "invalid_json_shape"}


def _live_preflight_for_stage(
    preflight: dict[str, Any],
    *,
    live_stage: str,
    live_case_id: str,
) -> dict[str, Any]:
    return select_context_live_provider_inputs(
        preflight,
        case_id=live_case_id,
        all_cases=live_stage == "full-matrix",
    )


async def _live_canary(
    *,
    context_live_provider_input_preflight: dict[str, Any],
    provider_profile_id: str,
    token: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    return await run_context_live_diagnostic_canary(
        context_live_provider_input_preflight=context_live_provider_input_preflight,
        token=token,
        provider_profile_id=provider_profile_id,
        timeout_seconds=timeout_seconds,
    )


def _write_artifacts(
    *,
    artifact_dir: Path,
    matrix: dict[str, Any],
    anti_overfit: dict[str, Any],
    holdout_plan: dict[str, Any],
    preflight: dict[str, Any],
    dry_run: dict[str, Any],
    canary: dict[str, Any],
    review_pack: dict[str, Any],
    stage_gate: dict[str, Any] | None = None,
) -> dict[str, str]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "context_live_diagnostic_case_matrix": artifact_dir
        / "accurate_intake_context_live_diagnostic_case_matrix.json",
        "context_live_diagnostic_anti_overfit_guard": artifact_dir
        / "accurate_intake_context_live_diagnostic_anti_overfit_guard.json",
        "context_live_diagnostic_holdout_plan": artifact_dir
        / "accurate_intake_context_live_diagnostic_holdout_plan.json",
        "context_live_provider_input_preflight": artifact_dir
        / "accurate_intake_context_live_provider_input_preflight.json",
        "context_live_response_contract_dry_run": artifact_dir
        / "accurate_intake_context_live_response_contract_dry_run.json",
        "context_live_diagnostic_canary": artifact_dir
        / "accurate_intake_context_live_diagnostic_canary.json",
        "context_live_diagnostic_review_pack": artifact_dir
        / "accurate_intake_context_live_diagnostic_review_pack.json",
    }
    if stage_gate is not None:
        paths["context_live_diagnostic_stage_gate"] = (
            artifact_dir / "accurate_intake_context_live_diagnostic_stage_gate.json"
        )
    payloads = {
        "context_live_diagnostic_case_matrix": matrix,
        "context_live_diagnostic_anti_overfit_guard": anti_overfit,
        "context_live_diagnostic_holdout_plan": holdout_plan,
        "context_live_provider_input_preflight": preflight,
        "context_live_response_contract_dry_run": dry_run,
        "context_live_diagnostic_canary": canary,
        "context_live_diagnostic_review_pack": review_pack,
    }
    if stage_gate is not None:
        payloads["context_live_diagnostic_stage_gate"] = stage_gate
    for group_id, path in paths.items():
        write_json_artifact(path, payloads[group_id])
    return {group_id: str(path) for group_id, path in paths.items()}


def build_context_live_diagnostic_gate_artifact(
    *,
    artifact_dir: Path,
    allow_live_provider: bool = False,
    require_live_provider: bool = False,
    provider_profile_id: str = DEFAULT_CONTEXT_LIVE_PROVIDER_PROFILE_ID,
    timeout_seconds: int = 60,
    live_stage: str = "single-case",
    live_case_id: str = "context_live_001_general_chat_no_mutation",
    prior_single_case_stage_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    matrix = build_context_live_diagnostic_case_matrix_artifact()
    anti_overfit = build_context_live_diagnostic_anti_overfit_guard_artifact(matrix)
    holdout_plan = build_context_live_diagnostic_holdout_plan_artifact(
        context_live_diagnostic_case_matrix=matrix,
        context_live_diagnostic_anti_overfit_guard=anti_overfit,
    )
    preflight = build_context_live_provider_input_preflight_artifact(matrix, anti_overfit)
    dry_run = build_context_live_response_contract_dry_run_artifact(preflight)

    token = os.getenv("AI_BUILDER_TOKEN", "").strip()
    if allow_live_provider and token:
        live_preflight = _live_preflight_for_stage(
            preflight,
            live_stage=live_stage,
            live_case_id=live_case_id,
        )
        canary = asyncio.run(
            _live_canary(
                context_live_provider_input_preflight=live_preflight,
                provider_profile_id=provider_profile_id,
                token=token,
                timeout_seconds=timeout_seconds,
            )
        )
    elif allow_live_provider:
        canary = build_missing_token_report(
            context_live_provider_input_preflight=preflight,
            provider_profile_id=provider_profile_id,
        )
    else:
        canary = _not_allowed_report(
            context_live_provider_input_preflight=preflight,
            provider_profile_id=provider_profile_id,
        )
    live_invoked = canary.get("live_invoked") is True
    stage_gate = (
        build_context_live_diagnostic_stage_gate_artifact(
            live_stage=live_stage,
            context_live_diagnostic_canary=canary,
            prior_single_case_stage_gate=prior_single_case_stage_gate,
        )
        if live_invoked
        else None
    )

    review_pack = build_context_live_diagnostic_review_pack_artifact(
        {
            "context_live_diagnostic_case_matrix": matrix,
            "context_live_diagnostic_anti_overfit_guard": anti_overfit,
            "context_live_diagnostic_holdout_plan": holdout_plan,
            "context_live_provider_input_preflight": preflight,
            "context_live_response_contract_dry_run": dry_run,
            "context_live_diagnostic_canary": canary,
        }
    )
    artifact_paths = _write_artifacts(
        artifact_dir=artifact_dir,
        matrix=matrix,
        anti_overfit=anti_overfit,
        holdout_plan=holdout_plan,
        preflight=preflight,
        dry_run=dry_run,
        canary=canary,
        review_pack=review_pack,
        stage_gate=stage_gate,
    )
    blockers = list(review_pack.get("blockers") or [])
    if stage_gate is not None and stage_gate.get("status") == "blocked":
        blockers.extend(f"context_live_diagnostic_stage_gate.{item}" for item in stage_gate.get("blockers") or [])
    if holdout_plan.get("status") != "pass":
        blockers.append("context_live_diagnostic_holdout_plan_status_not_pass")
        blockers.extend(f"context_live_diagnostic_holdout_plan.{item}" for item in holdout_plan.get("blockers") or [])
    if require_live_provider and not live_invoked:
        blockers.append("live_provider_required_but_not_invoked")
    if blockers:
        status = "blocked"
    elif review_pack.get("status") == "context_live_diagnostic_review_ready_with_live_canary":
        status = "context_live_diagnostic_gate_ready_with_live_canary"
    else:
        status = "context_live_diagnostic_gate_ready_without_live_canary"
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_diagnostic_gate",
            "status": status,
            "claim_scope": "current_shell_compatibility_context_live_diagnostic_stage_order_gate",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "blockers": blockers,
            "artifact_paths": artifact_paths,
            "review_pack_status": review_pack.get("status"),
            "canary_status": canary.get("status"),
            "provider_profile_id": provider_profile_id,
            "provider_profile_model": canary.get("provider_profile_model"),
            "live_stage": live_stage,
            "live_case_id": live_case_id if live_stage == "single-case" else None,
            "stage_gate_status": stage_gate.get("status") if stage_gate is not None else "not_applicable",
            "live_provider_allowed": allow_live_provider,
            "live_provider_required": require_live_provider,
            "live_llm_invoked": live_invoked,
            "live_provider_invoked": live_invoked,
            "single_case_live_probe_required": live_stage == "single-case",
            "full_matrix_live_probe_required": True,
            "full_matrix_live_probe_current_stage": live_stage == "full-matrix",
            "full_matrix_live_probe_requires_single_case": True,
            "ad_hoc_live_case_selection_allowed": False,
            "fixed_case_matrix_used": True,
            "anti_overfit_guard_required": True,
            "holdout_plan_required": True,
            "response_contract_dry_run_required": True,
            "diagnostic_only": True,
            "local_only": True,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "summary": {
                "fixed_case_count": review_pack.get("summary", {}).get("fixed_case_count"),
                "dry_run_validated_response_count": review_pack.get("summary", {}).get(
                    "dry_run_validated_response_count"
                ),
                "live_provider_output_count": review_pack.get("summary", {}).get(
                    "live_provider_output_count"
                ),
                "live_blocked_response_count": review_pack.get("summary", {}).get(
                    "live_blocked_response_count"
                ),
            },
        }
    )


def main(argv: list[str] | None = None) -> int:
    _load_local_env(ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Run the CurrentShell compatibility context live diagnostic gate without FoodDB/WebSearch truth."
    )
    parser.add_argument("--artifact-dir", default=str(DEFAULT_ARTIFACT_DIR))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--allow-live-provider", action="store_true")
    parser.add_argument("--require-live-provider", action="store_true")
    parser.add_argument("--provider-profile-id", default=DEFAULT_CONTEXT_LIVE_PROVIDER_PROFILE_ID)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--live-stage", choices=LIVE_STAGES, default="single-case")
    parser.add_argument("--live-case-id", default="context_live_001_general_chat_no_mutation")
    parser.add_argument("--prior-single-case-stage-gate-json")
    args = parser.parse_args(argv)

    artifact = build_context_live_diagnostic_gate_artifact(
        artifact_dir=Path(args.artifact_dir),
        allow_live_provider=bool(args.allow_live_provider),
        require_live_provider=bool(args.require_live_provider),
        provider_profile_id=str(args.provider_profile_id),
        timeout_seconds=int(args.timeout_seconds),
        live_stage=str(args.live_stage),
        live_case_id=str(args.live_case_id),
        prior_single_case_stage_gate=_read_json(
            Path(args.prior_single_case_stage_gate_json)
            if args.prior_single_case_stage_gate_json
            else None
        ),
    )
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "status": artifact["status"],
                "review_pack_status": artifact["review_pack_status"],
                "canary_status": artifact["canary_status"],
                "live_llm_invoked": artifact["live_llm_invoked"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if artifact["status"] != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
