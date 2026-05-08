from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_OUTPUT_DIR = ROOT / "artifacts"
DEFAULT_ARTIFACTS = (
    ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic_provider_health.json",
    ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic_schema_probe.json",
    ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic_fake_runtime_gate.json",
    ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic_seeded_removal.json",
    ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic_single_case.json",
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
_COST_KEYS = (
    "estimated_cost_usd",
    "total_cost_usd",
    "cost_usd",
)


def build_accurate_intake_live_cost_summary(
    artifacts: list[dict[str, Any]],
    *,
    source_paths: list[Path] | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    source_artifacts: list[dict[str, Any]] = []
    usage_records: list[dict[str, Any]] = []
    cost_records: list[dict[str, Any]] = []
    stage_count = 0
    provider_invocation_count = 0

    for index, artifact in enumerate(artifacts):
        if artifact.get("artifact_type") != "accurate_intake_mvp_live_diagnostic":
            blockers.append(f"source_{index}_artifact_type_invalid")
        for flag in _FORBIDDEN_TRUE_FLAGS:
            if artifact.get(flag) is True:
                blockers.append(f"source_{index}_{flag}")
        stages = [_dict(item) for item in _list(artifact.get("stages"))]
        invocations = [_dict(item) for item in _list(artifact.get("provider_invocations"))]
        stage_count += len(stages)
        provider_invocation_count += len(invocations)
        path = source_paths[index] if source_paths and index < len(source_paths) else None
        source_artifacts.append(
            {
                "index": index,
                "path": str(path) if path is not None else None,
                "artifact_type": _optional_string(artifact.get("artifact_type")),
                "generated_at_utc": _optional_string(artifact.get("generated_at_utc")),
                "provider_profile_id": _optional_string(artifact.get("provider_profile_id")),
                "model": _optional_string(artifact.get("provider_profile_model")),
                "stage_ids": [str(stage.get("stage_id") or "") for stage in stages],
                "sha256": _source_hash(artifact, path=path),
                "sha256_kind": "source_file_bytes" if path is not None and path.exists() else "canonical_json_payload",
            }
        )
        usage_records.extend(_usage_records(artifact, source_index=index))
        cost_records.extend(_cost_records(artifact, source_index=index))

    prompt_tokens = sum(int(record.get("prompt_tokens") or 0) for record in usage_records)
    completion_tokens = sum(int(record.get("completion_tokens") or 0) for record in usage_records)
    total_tokens = sum(int(record.get("total_tokens") or 0) for record in usage_records)
    reported_cost_usd = sum(float(record["cost_usd"]) for record in cost_records) if cost_records else None
    cost_unavailable = bool(usage_records) and not cost_records
    return _json_safe(
        {
            "artifact_type": "accurate_intake_mvp_live_cost_summary",
            "artifact_schema_version": "1.0",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "claim_scope": "live_diagnostic_cost_summary",
            "generated_artifact_policy": {
                "commit_as_repo_truth": False,
                "local_diagnostic_evidence_only": True,
            },
            "input_integrity": {"passed": not blockers, "blockers": sorted(set(blockers))},
            "source_artifacts": source_artifacts,
            "usage_records": usage_records,
            "cost_records": cost_records,
            "summary": {
                "source_artifact_count": len(artifacts),
                "stage_count": stage_count,
                "provider_invocation_count": provider_invocation_count,
                "usage_record_count": len(usage_records),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "reported_cost_record_count": len(cost_records),
                "reported_cost_usd": reported_cost_usd,
                "cost_unavailable_without_pricing": cost_unavailable,
            },
            "cost_policy": {
                "billing_truth_source": "provider_reported_artifact_fields_only",
                "token_counts_are_not_billing_truth": True,
                "pricing_table_applied": False,
                "cost_unavailable_without_pricing": cost_unavailable,
            },
        }
    )


def write_accurate_intake_live_cost_summary(
    *,
    artifact_paths: list[Path] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    output_path: Path | None = None,
) -> Path:
    paths = list(artifact_paths or DEFAULT_ARTIFACTS)
    artifacts = [_dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    summary = build_accurate_intake_live_cost_summary(artifacts, source_paths=paths)
    path = output_path or output_dir / "accurate_intake_mvp_live_cost_summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _usage_records(value: Any, *, source_index: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path, usage in _walk_usage(value):
        prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or usage.get("total_token") or 0)
        if total_tokens <= 0:
            total_tokens = prompt_tokens + completion_tokens
        if prompt_tokens <= 0 and completion_tokens <= 0 and total_tokens <= 0:
            continue
        records.append(
            {
                "source_index": source_index,
                "json_path": path,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            }
        )
    return records


def _cost_records(value: Any, *, source_index: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path, payload in _walk_dicts(value):
        for key in _COST_KEYS:
            if key not in payload:
                continue
            try:
                cost = float(payload[key])
            except (TypeError, ValueError):
                continue
            records.append({"source_index": source_index, "json_path": f"{path}.{key}", "cost_usd": cost})
    return records


def _walk_usage(value: Any, path: str = "$") -> list[tuple[str, dict[str, Any]]]:
    records: list[tuple[str, dict[str, Any]]] = []
    if isinstance(value, dict):
        usage = value.get("usage")
        if isinstance(usage, dict):
            records.append((f"{path}.usage", dict(usage)))
        for key, item in value.items():
            if key == "usage":
                continue
            records.extend(_walk_usage(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            records.extend(_walk_usage(item, f"{path}[{index}]"))
    return records


def _walk_dicts(value: Any, path: str = "$") -> list[tuple[str, dict[str, Any]]]:
    records: list[tuple[str, dict[str, Any]]] = []
    if isinstance(value, dict):
        records.append((path, dict(value)))
        for key, item in value.items():
            records.extend(_walk_dicts(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            records.extend(_walk_dicts(item, f"{path}[{index}]"))
    return records


def _artifact_hash(artifact: dict[str, Any]) -> str:
    encoded = json.dumps(artifact, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_hash(artifact: dict[str, Any], *, path: Path | None) -> str:
    if path is not None and path.exists():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return _artifact_hash(artifact)


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _optional_string(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Accurate Intake MVP live diagnostic cost summary.")
    parser.add_argument("--artifact", action="append", dest="artifacts")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output")
    args = parser.parse_args()
    paths = [Path(item) for item in (args.artifacts or [str(path) for path in DEFAULT_ARTIFACTS])]
    output = write_accurate_intake_live_cost_summary(
        artifact_paths=paths,
        output_dir=Path(args.output_dir),
        output_path=Path(args.output) if args.output else None,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
