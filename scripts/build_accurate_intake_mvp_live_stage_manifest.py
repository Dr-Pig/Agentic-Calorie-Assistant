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

from scripts.run_accurate_intake_mvp_live_diagnostic import ORDERED_STAGE_IDS


DEFAULT_OUTPUT_DIR = ROOT / "artifacts"
DEFAULT_STAGE_ARTIFACTS = (
    ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic_provider_health.json",
    ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic_schema_probe.json",
    ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic_fake_runtime_gate.json",
    ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic_seeded_removal.json",
    ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic_single_case.json",
)
REQUIRED_STAGE_IDS = (
    "provider_health_smoke",
    "schema_contract_probe",
    "fake_provider_active_runtime_gate",
)
REQUIRED_SINGLE_CASE_IDS = (
    "explicit_item_removal_seeded",
    "chinese_chicken_rice_correction_removal_debug",
)

_FORBIDDEN_TRUE_FLAGS = (
    "readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_selected",
    "mutation_rollout_approved",
    "runtime_web_activation_approved",
    "live_provider_used_as_truth",
)


def build_accurate_intake_live_stage_manifest(stage_artifact_paths: list[Path]) -> dict[str, Any]:
    stages: list[dict[str, Any]] = []
    blockers: list[str] = []
    source_artifacts: list[dict[str, Any]] = []
    for index, path in enumerate(stage_artifact_paths):
        source = _load_json(path)
        source_artifacts.append(
            {
                "index": index,
                "path": str(path),
                "artifact_type": _optional_string(source.get("artifact_type")),
            }
        )
        if source.get("artifact_type") != "accurate_intake_mvp_live_diagnostic":
            blockers.append(f"source_{index}_artifact_type_invalid")
        for flag in _FORBIDDEN_TRUE_FLAGS:
            if source.get(flag) is True:
                blockers.append(f"source_{index}_{flag}")
        source_stages = [_dict(item) for item in _list(source.get("stages"))]
        if not source_stages:
            blockers.append(f"source_{index}_stages_missing")
        for stage in source_stages:
            stages.append(_manifest_stage(stage, source=source, source_path=path, source_index=index))

    input_integrity = {"passed": not blockers, "blockers": sorted(set(blockers))}
    return _json_safe(
        {
            "artifact_type": "accurate_intake_mvp_live_stage_manifest",
            "artifact_schema_version": "1.0",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "source_artifact_type": "accurate_intake_mvp_live_diagnostic",
            "claim_scope": "live_diagnostic_stage_manifest",
            "readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_selected": False,
            "mutation_rollout_approved": False,
            "runtime_web_activation_approved": False,
            "stage_ids_ordered": list(ORDERED_STAGE_IDS),
            "source_artifacts": source_artifacts,
            "stages": stages,
            "stage_summary": stage_summary_from_stages(stages),
            "input_integrity": input_integrity,
        }
    )


def write_accurate_intake_live_stage_manifest(
    *,
    stage_artifact_paths: list[Path] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    paths = list(stage_artifact_paths or DEFAULT_STAGE_ARTIFACTS)
    manifest = build_accurate_intake_live_stage_manifest(paths)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "accurate_intake_mvp_live_stage_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def stage_summary_from_stages(stages: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {str(stage.get("stage_id") or ""): stage for stage in stages}
    provider_health = by_id.get("provider_health_smoke", {})
    schema_probe = by_id.get("schema_contract_probe", {})
    single_case = by_id.get("single_case_live_probe", {})
    full_suite = by_id.get("full_suite_live_diagnostic", {})
    provider_health_blocked = bool(provider_health) and provider_health.get("status") != "pass"
    schema_contract_blocked = bool(schema_probe) and schema_probe.get("status") != "pass"
    full_suite_without_single_case_probe = bool(full_suite) and single_case.get("status") != "pass"
    has_retry_dependent_stage = any(
        stage.get("retry_policy_applied") is True or str(stage.get("result_kind") or "") == "pass_after_retry"
        for stage in stages
    )
    present_stage_ids = {str(stage.get("stage_id") or "") for stage in stages}
    single_case_results = [
        {
            "case_ids": [str(item) for item in _list(stage.get("case_ids"))],
            "status": str(stage.get("status") or ""),
            "result_kind": _optional_string(stage.get("result_kind")),
        }
        for stage in stages
        if stage.get("stage_id") == "single_case_live_probe"
    ]
    present_single_case_ids = {
        case_id
        for result in single_case_results
        for case_id in [str(item) for item in _list(result.get("case_ids"))]
    }
    missing_required_stage_ids = [
        stage_id for stage_id in REQUIRED_STAGE_IDS if stage_id not in present_stage_ids
    ]
    missing_required_single_case_ids = [
        case_id for case_id in REQUIRED_SINGLE_CASE_IDS if case_id not in present_single_case_ids
    ]
    return {
        "present": bool(stages),
        "stage_ids": [str(stage.get("stage_id") or "") for stage in stages],
        "provider_health_status": _optional_string(provider_health.get("status")),
        "schema_contract_status": _optional_string(schema_probe.get("status")),
        "single_case_probe_status": _optional_string(single_case.get("status")),
        "full_suite_status": _optional_string(full_suite.get("status")),
        "provider_health_blocked": provider_health_blocked,
        "schema_contract_blocked": schema_contract_blocked,
        "full_suite_without_single_case_probe": full_suite_without_single_case_probe,
        "has_retry_dependent_stage": has_retry_dependent_stage,
        "has_missing_required_stage": bool(missing_required_stage_ids or missing_required_single_case_ids),
        "missing_required_stage_ids": missing_required_stage_ids,
        "missing_required_single_case_ids": missing_required_single_case_ids,
        "single_case_probe_results": single_case_results,
        "result_kind_counts": _counts(
            _optional_string(stage.get("result_kind")) for stage in stages if stage.get("result_kind")
        ),
        "failure_layer_counts": _counts(
            _optional_string(stage.get("failure_layer")) for stage in stages if stage.get("failure_layer")
        ),
        "failure_family_counts": _counts(
            _optional_string(stage.get("failure_family")) for stage in stages if stage.get("failure_family")
        ),
        "stage_failures": [
            {
                "stage_id": str(stage.get("stage_id") or ""),
                "status": str(stage.get("status") or ""),
                "failure_layer": _optional_string(stage.get("failure_layer")),
                "failure_family": _optional_string(stage.get("failure_family")),
            }
            for stage in stages
            if stage.get("status") != "pass"
        ],
    }


def _manifest_stage(
    stage: dict[str, Any],
    *,
    source: dict[str, Any],
    source_path: Path,
    source_index: int,
) -> dict[str, Any]:
    return _json_safe(
        {
            "stage_id": str(stage.get("stage_id") or ""),
            "artifact_path": str(source_path),
            "source_index": int(source_index),
            "status": str(stage.get("status") or ""),
            "provider_profile_id": _optional_string(
                stage.get("provider_profile_id") or source.get("provider_profile_id")
            ),
            "model": _optional_string(stage.get("model") or source.get("provider_profile_model")),
            "transport_mode": _optional_string(stage.get("transport_mode") or source.get("transport_mode")),
            "attempt_count": int(stage.get("attempt_count") or 0),
            "latency_ms": int(stage.get("latency_ms") or 0),
            "timeout_budget_ms": int(stage.get("timeout_budget_ms") or 0),
            "failure_layer": _optional_string(stage.get("failure_layer")),
            "failure_family": _optional_string(stage.get("failure_family")),
            "retry_policy_applied": bool(stage.get("retry_policy_applied")),
            "result_kind": _optional_string(stage.get("result_kind")),
            "retry_attempts": [_dict(item) for item in _list(stage.get("retry_attempts"))],
            "case_ids": [str(item) for item in _list(stage.get("case_ids"))],
            "summary": _dict(stage.get("summary")),
        }
    )


def _load_json(path: Path) -> dict[str, Any]:
    return _dict(json.loads(path.read_text(encoding="utf-8")))


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
    parser = argparse.ArgumentParser(description="Build Accurate Intake MVP live stage manifest.")
    parser.add_argument("--stage-artifact", action="append", dest="stage_artifacts")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    paths = [Path(item) for item in (args.stage_artifacts or [str(path) for path in DEFAULT_STAGE_ARTIFACTS])]
    output = write_accurate_intake_live_stage_manifest(
        stage_artifact_paths=paths,
        output_dir=Path(args.output_dir),
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
