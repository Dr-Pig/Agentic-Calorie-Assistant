from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.contracts.readiness_claim import build_readiness_claim
from scripts.build_accurate_intake_mvp_live_stage_manifest import (
    DEFAULT_OUTPUT_DIR,
    REQUIRED_SINGLE_CASE_IDS,
    REQUIRED_STAGE_IDS,
)


DEFAULT_STAGE_MANIFEST_ARTIFACT = ROOT / "artifacts" / "accurate_intake_mvp_live_stage_manifest.json"
MINIMUM_STRICT_REPLAY_RUNS_FOR_PRIVATE_SELF_USE_CANDIDATE = 3

_FORBIDDEN_TRUE_FLAGS = (
    "readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_selected",
    "mutation_rollout_approved",
    "runtime_web_activation_approved",
)


def build_accurate_intake_offline_shadow_replay(stage_manifest_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    runs = [
        _run_summary(index=index, artifact=artifact)
        for index, artifact in enumerate(stage_manifest_artifacts, 1)
    ]
    input_integrity = _input_integrity(stage_manifest_artifacts, runs)
    summary = _summary(runs, input_integrity=input_integrity)
    return _json_safe(
        {
            "artifact_type": "accurate_intake_mvp_offline_shadow_replay",
            "artifact_schema_version": "1.0",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "claim_scope": "offline_shadow_replay",
            "readiness_claimed": False,
            "readiness_claim": _readiness_claim(),
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_selected": False,
            "mutation_rollout_approved": False,
            "runtime_web_activation_approved": False,
            "input_integrity": input_integrity,
            "summary": summary,
            "strictness_gate": {
                "minimum_strict_replay_runs": MINIMUM_STRICT_REPLAY_RUNS_FOR_PRIVATE_SELF_USE_CANDIDATE,
                "single_live_run_unlocks_private_self_use": False,
                "pass_after_retry_counts_as_strict": False,
                "timeout_excluded_from_strict_pass_claim": True,
                "single_profile_stability_is_private_self_use_ready": False,
                "model_diversity_required_for_private_self_use_candidate": True,
                "human_approval_required_for_private_self_use_candidate": True,
            },
            "runs": runs,
        }
    )


def write_accurate_intake_offline_shadow_replay(
    *,
    stage_manifest_paths: list[Path] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    paths = list(stage_manifest_paths or [DEFAULT_STAGE_MANIFEST_ARTIFACT])
    artifacts = [_dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    replay = build_accurate_intake_offline_shadow_replay(artifacts)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "accurate_intake_mvp_offline_shadow_replay.json"
    path.write_text(json.dumps(replay, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _run_summary(*, index: int, artifact: dict[str, Any]) -> dict[str, Any]:
    stages = [_dict(stage) for stage in _list(artifact.get("stages"))]
    result_kind_counts = _counts(_optional_string(stage.get("result_kind")) for stage in stages)
    failure_family_counts = _counts(_optional_string(stage.get("failure_family")) for stage in stages)
    failure_layer_counts = _counts(_optional_string(stage.get("failure_layer")) for stage in stages)
    profile_ids = sorted(
        {
            profile_id
            for stage in stages
            for profile_id in [_optional_string(stage.get("provider_profile_id"))]
            if profile_id
        }
    )
    models = sorted(
        {
            model
            for stage in stages
            for model in [_optional_string(stage.get("model"))]
            if model
        }
    )
    present_stage_ids = {str(stage.get("stage_id") or "") for stage in stages}
    present_single_case_ids = {
        str(case_id)
        for stage in stages
        if stage.get("stage_id") == "single_case_live_probe"
        for case_id in _list(stage.get("case_ids"))
        if str(case_id)
    }
    missing_required_stage_ids = [
        stage_id for stage_id in REQUIRED_STAGE_IDS if stage_id not in present_stage_ids
    ]
    missing_required_single_case_ids = [
        case_id for case_id in REQUIRED_SINGLE_CASE_IDS if case_id not in present_single_case_ids
    ]
    retry_dependent_count = sum(
        1
        for stage in stages
        if stage.get("retry_policy_applied") is True
        or str(stage.get("result_kind") or "") == "pass_after_retry"
    )
    timeout_count = sum(
        1
        for stage in stages
        if str(stage.get("status") or "") == "timeout"
        or str(stage.get("result_kind") or "").startswith("timeout")
    )
    failed_stage_count = sum(
        1 for stage in stages if str(stage.get("status") or "") in {"fail", "blocked"}
    )
    strict_pass_first_attempt_count = result_kind_counts.get("strict_pass_first_attempt", 0)
    all_strict_first_attempt = (
        bool(stages)
        and strict_pass_first_attempt_count == len(stages)
        and retry_dependent_count == 0
        and timeout_count == 0
        and failed_stage_count == 0
        and not missing_required_stage_ids
        and not missing_required_single_case_ids
    )
    return {
        "run_index": index,
        "source_artifact_type": artifact.get("artifact_type"),
        "claim_scope": artifact.get("claim_scope"),
        "stage_count": len(stages),
        "profile_ids": profile_ids,
        "models": models,
        "result_kind_counts": result_kind_counts,
        "failure_layer_counts": failure_layer_counts,
        "failure_family_counts": failure_family_counts,
        "strict_pass_first_attempt_count": strict_pass_first_attempt_count,
        "pass_after_retry_count": result_kind_counts.get("pass_after_retry", 0),
        "timeout_count": timeout_count,
        "retry_dependent_count": retry_dependent_count,
        "failed_stage_count": failed_stage_count,
        "missing_required_stage_ids": missing_required_stage_ids,
        "missing_required_single_case_ids": missing_required_single_case_ids,
        "all_strict_first_attempt": all_strict_first_attempt,
    }


def _input_integrity(stage_manifest_artifacts: list[dict[str, Any]], runs: list[dict[str, Any]]) -> dict[str, Any]:
    blockers: list[str] = []
    if not stage_manifest_artifacts:
        blockers.append("missing_stage_manifest_artifact")
    for index, artifact in enumerate(stage_manifest_artifacts, 1):
        if artifact.get("artifact_type") != "accurate_intake_mvp_live_stage_manifest":
            blockers.append(f"run_{index}_artifact_type_invalid")
        for flag in _FORBIDDEN_TRUE_FLAGS:
            if artifact.get(flag) is True:
                blockers.append(f"run_{index}_{flag}")
        manifest_integrity = _dict(artifact.get("input_integrity"))
        if manifest_integrity.get("passed") is not True:
            blockers.append(f"run_{index}_stage_manifest_integrity_failed")
            for blocker in _string_list(manifest_integrity.get("blockers")):
                blockers.append(f"run_{index}_{blocker}")
    for run in runs:
        run_index = int(run.get("run_index") or 0)
        if run.get("missing_required_stage_ids"):
            blockers.append(f"run_{run_index}_missing_required_stage")
        if run.get("missing_required_single_case_ids"):
            blockers.append(f"run_{run_index}_missing_required_single_case")
    return {"passed": not blockers, "blockers": sorted(set(blockers))}


def _summary(runs: list[dict[str, Any]], *, input_integrity: dict[str, Any]) -> dict[str, Any]:
    sample_run_count = len(runs)
    strict_pass_first_attempt_count = sum(
        int(run.get("strict_pass_first_attempt_count") or 0) for run in runs
    )
    pass_after_retry_count = sum(int(run.get("pass_after_retry_count") or 0) for run in runs)
    timeout_count = sum(int(run.get("timeout_count") or 0) for run in runs)
    retry_dependent_count = sum(int(run.get("retry_dependent_count") or 0) for run in runs)
    failed_stage_count = sum(int(run.get("failed_stage_count") or 0) for run in runs)
    stage_count = sum(int(run.get("stage_count") or 0) for run in runs)
    profile_ids = sorted(
        {str(profile_id) for run in runs for profile_id in _list(run.get("profile_ids")) if str(profile_id)}
    )
    models = sorted({str(model) for run in runs for model in _list(run.get("models")) if str(model)})
    failure_family_counts = _merge_counts(_dict(run.get("failure_family_counts")) for run in runs)
    all_runs_strict_first_attempt = sample_run_count > 0 and all(
        run.get("all_strict_first_attempt") is True for run in runs
    )
    strict_replay_ready = (
        input_integrity.get("passed") is True
        and sample_run_count >= MINIMUM_STRICT_REPLAY_RUNS_FOR_PRIVATE_SELF_USE_CANDIDATE
        and all_runs_strict_first_attempt
        and pass_after_retry_count == 0
        and timeout_count == 0
        and retry_dependent_count == 0
        and failed_stage_count == 0
    )
    single_profile_stability = (
        strict_replay_ready and len(profile_ids) <= 1 and len(models) <= 1
    )
    model_diversity_missing = len(profile_ids) <= 1 and len(models) <= 1
    if model_diversity_missing:
        model_diversity_status = "model_diversity_missing"
    else:
        model_diversity_status = "provider_diversity_present"
    max_model_claim = (
        "single_profile_live_diagnostic_observed"
        if model_diversity_missing
        else "multi_profile_live_diagnostic_observed"
    )
    return {
        "sample_run_count": sample_run_count,
        "run_count": sample_run_count,
        "stage_count": stage_count,
        "strict_pass_first_attempt_count": strict_pass_first_attempt_count,
        "pass_after_retry_count": pass_after_retry_count,
        "repaired_pass_count": 0,
        "timeout_count": timeout_count,
        "retry_dependent_count": retry_dependent_count,
        "failed_stage_count": failed_stage_count,
        "failure_family_counts": failure_family_counts,
        "profile_ids": profile_ids,
        "models": models,
        "model_diversity_missing": model_diversity_missing,
        "model_diversity_status": model_diversity_status,
        "max_model_claim": max_model_claim,
        "all_runs_strict_first_attempt": all_runs_strict_first_attempt,
        "strict_replay_ready": strict_replay_ready,
        "single_profile_stability": single_profile_stability,
        "minimum_strict_replay_runs_for_private_self_use_candidate": (
            MINIMUM_STRICT_REPLAY_RUNS_FOR_PRIVATE_SELF_USE_CANDIDATE
        ),
        "eligible_for_private_self_use_candidate": False,
    }


def _readiness_claim() -> dict[str, Any]:
    return build_readiness_claim(
        claim_scope="live_diagnostic",
        activation_stage="live_diagnostic",
        semantic_authority_source="deterministic_validator",
        producer_honesty={
            "runner_inferred_semantics": False,
            "fake_provider_simulated_manager": False,
            "final_mapping_fabricated": False,
            "mutation_fabricated": False,
        },
        evidence_lineage={
            "artifacts": ["artifacts/accurate_intake_mvp_live_stage_manifest.json"],
            "producers": ["scripts/build_accurate_intake_mvp_offline_shadow_replay.py"],
            "legacy_oracle_used": False,
        },
        allowed_next_stage=None,
        forbidden_claims=[
            "product_ready",
            "private_self_use_ready",
            "user_facing_ready",
            "mutation_ready",
            "production_ready",
            "runtime_web_activation_ready",
            "model_portable",
        ],
        readiness_claimed=False,
    )


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in _list(value) if str(item)]


def _optional_string(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _counts(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        if not value:
            continue
        counts[str(value)] = counts.get(str(value), 0) + 1
    return counts


def _merge_counts(items: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        for key, value in item.items():
            counts[str(key)] = counts.get(str(key), 0) + int(value or 0)
    return counts


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Accurate Intake MVP offline shadow replay.")
    parser.add_argument("--stage-manifest", action="append", dest="stage_manifests")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    paths = [
        Path(item)
        for item in (args.stage_manifests or [str(DEFAULT_STAGE_MANIFEST_ARTIFACT)])
    ]
    output = write_accurate_intake_offline_shadow_replay(
        stage_manifest_paths=paths,
        output_dir=Path(args.output_dir),
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
