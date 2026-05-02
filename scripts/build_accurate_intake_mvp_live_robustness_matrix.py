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

from scripts.build_accurate_intake_mvp_live_stage_manifest import DEFAULT_STAGE_ARTIFACTS


DEFAULT_OUTPUT_DIR = ROOT / "artifacts"
_FORBIDDEN_TRUE_FLAGS = (
    "readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_selected",
    "mutation_rollout_approved",
    "runtime_web_activation_approved",
    "live_provider_used_as_truth",
)


def build_accurate_intake_live_robustness_matrix(
    artifacts: list[dict[str, Any]],
    *,
    source_paths: list[Path] | None = None,
) -> dict[str, Any]:
    stages: list[dict[str, Any]] = []
    blockers: list[str] = []
    profile_ids: set[str] = set()
    model_ids: set[str] = set()

    for index, artifact in enumerate(artifacts):
        if artifact.get("artifact_type") != "accurate_intake_mvp_live_diagnostic":
            blockers.append(f"source_{index}_artifact_type_invalid")
        for flag in _FORBIDDEN_TRUE_FLAGS:
            if artifact.get(flag) is True:
                blockers.append(f"source_{index}_{flag}")
        profile_id = _optional_string(artifact.get("provider_profile_id"))
        model_id = _optional_string(artifact.get("provider_profile_model"))
        if profile_id:
            profile_ids.add(profile_id)
        if model_id:
            model_ids.add(model_id)
        for stage in _list(artifact.get("stages")):
            stage_dict = _dict(stage)
            stage_profile_id = _optional_string(stage_dict.get("provider_profile_id") or profile_id)
            stage_model_id = _optional_string(stage_dict.get("model") or model_id)
            if stage_profile_id:
                profile_ids.add(stage_profile_id)
            if stage_model_id:
                model_ids.add(stage_model_id)
            stages.append(
                {
                    "stage_id": str(stage_dict.get("stage_id") or ""),
                    "source_path": str(source_paths[index]) if source_paths and index < len(source_paths) else None,
                    "status": str(stage_dict.get("status") or ""),
                    "result_kind": _optional_string(stage_dict.get("result_kind")),
                    "retry_policy_applied": stage_dict.get("retry_policy_applied") is True,
                    "failure_layer": _optional_string(stage_dict.get("failure_layer")),
                    "failure_family": _optional_string(stage_dict.get("failure_family")),
                    "provider_profile_id": stage_profile_id,
                    "model": stage_model_id,
                    "latency_ms": int(stage_dict.get("latency_ms") or 0),
                    "timeout_budget_ms": int(stage_dict.get("timeout_budget_ms") or 0),
                    "attempt_count": int(stage_dict.get("attempt_count") or 0),
                }
            )

    result_kind_counts = _counts(stage.get("result_kind") for stage in stages)
    failure_layer_counts = _counts(stage.get("failure_layer") for stage in stages)
    failure_family_counts = _counts(stage.get("failure_family") for stage in stages)
    has_retry_dependent_evidence = any(
        stage.get("retry_policy_applied") is True or stage.get("result_kind") == "pass_after_retry"
        for stage in stages
    )
    has_timeout_evidence = any(
        stage.get("status") == "timeout" or str(stage.get("result_kind") or "").startswith("timeout")
        for stage in stages
    )
    has_error_evidence = any(stage.get("status") in {"fail", "blocked"} for stage in stages)
    single_profile_only = len(profile_ids) <= 1 and len(model_ids) <= 1
    return _json_safe(
        {
            "artifact_type": "accurate_intake_mvp_live_robustness_matrix",
            "artifact_schema_version": "1.0",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "claim_scope": "live_diagnostic_robustness_matrix",
            "readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_selected": False,
            "mutation_rollout_approved": False,
            "runtime_web_activation_approved": False,
            "model_portability_claimed": False,
            "max_model_claim": (
                "single_profile_live_diagnostic_observed"
                if single_profile_only
                else "multi_profile_live_diagnostic_observed"
            ),
            "input_integrity": {"passed": not blockers, "blockers": sorted(set(blockers))},
            "provider_profile_ids": sorted(profile_ids),
            "models": sorted(model_ids),
            "single_profile_only": single_profile_only,
            "stage_count": len(stages),
            "stages": stages,
            "result_kind_counts": result_kind_counts,
            "failure_layer_counts": failure_layer_counts,
            "failure_family_counts": failure_family_counts,
            "has_retry_dependent_evidence": has_retry_dependent_evidence,
            "has_timeout_evidence": has_timeout_evidence,
            "has_error_evidence": has_error_evidence,
            "private_self_use_candidate_blocked": (
                bool(blockers) or has_retry_dependent_evidence or has_timeout_evidence or has_error_evidence
            ),
        }
    )


def write_accurate_intake_live_robustness_matrix(
    *,
    stage_artifact_paths: list[Path] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    paths = list(stage_artifact_paths or DEFAULT_STAGE_ARTIFACTS)
    artifacts = [_dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    matrix = build_accurate_intake_live_robustness_matrix(artifacts, source_paths=paths)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "accurate_intake_mvp_live_robustness_matrix.json"
    path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


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


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Accurate Intake MVP live robustness matrix.")
    parser.add_argument("--stage-artifact", action="append", dest="stage_artifacts")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    paths = [Path(item) for item in (args.stage_artifacts or [str(path) for path in DEFAULT_STAGE_ARTIFACTS])]
    output = write_accurate_intake_live_robustness_matrix(
        stage_artifact_paths=paths,
        output_dir=Path(args.output_dir),
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
