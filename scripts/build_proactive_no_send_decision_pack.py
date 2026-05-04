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


DEFAULT_NO_SEND_ARTIFACT = ROOT / "artifacts" / "proactive_no_send_simulation.json"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts"
MINIMUM_CLEAN_SHADOW_RUNS = 3

_FORBIDDEN_TRUE_FLAGS = (
    "real_runtime_effect",
    "proactive_sent",
    "scheduler_enabled",
    "manager_context_injected",
    "durable_memory_written",
    "recommendation_served",
    "rescue_committed",
    "day_budget_mutated",
    "body_plan_mutated",
    "meal_thread_mutated",
    "product_readiness_claimed",
    "private_self_use_approved",
)


def build_proactive_no_send_decision_pack(no_send_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    input_integrity = _input_integrity(no_send_artifacts)
    summary = _summary(no_send_artifacts)
    promotion_blockers = _promotion_blockers(
        input_integrity=input_integrity,
        clean_run_count=summary["clean_run_count"],
    )
    return {
        "artifact_type": "proactive_no_send_decision_pack",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "claim_scope": "no_send_shadow_decision_pack",
        "shadow_mode": True,
        "live_delivery_allowed": False,
        "scheduler_activation_allowed": False,
        "promotion_allowed": False,
        "input_integrity": input_integrity,
        "summary": summary,
        "promotion_gate": {
            "minimum_clean_shadow_runs": MINIMUM_CLEAN_SHADOW_RUNS,
            "human_review_required": True,
            "repeated_clean_shadow_evidence": summary["clean_run_count"] >= MINIMUM_CLEAN_SHADOW_RUNS,
            "promotion_blockers": promotion_blockers,
        },
    }


def write_proactive_no_send_decision_pack(
    *,
    no_send_artifact_paths: list[Path] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    output_path: Path | None = None,
) -> Path:
    paths = no_send_artifact_paths or [DEFAULT_NO_SEND_ARTIFACT]
    artifacts = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    pack = build_proactive_no_send_decision_pack(artifacts)
    path = output_path or output_dir / "proactive_no_send_decision_pack.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _input_integrity(no_send_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    blockers: list[str] = []
    if not no_send_artifacts:
        blockers.append("missing_no_send_artifact")
    for index, artifact in enumerate(no_send_artifacts, 1):
        if artifact.get("artifact_type") != "proactive_no_send_simulation":
            blockers.append(f"run_{index}_artifact_type_invalid")
        if artifact.get("shadow_mode") is not True:
            blockers.append(f"run_{index}_shadow_mode_not_true")
        for flag in _FORBIDDEN_TRUE_FLAGS:
            if artifact.get(flag) is True:
                blockers.append(f"run_{index}_{flag}")
    return {"passed": not blockers, "blockers": sorted(set(blockers))}


def _summary(no_send_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    candidate_types = sorted(
        {
            str(trigger_type)
            for artifact in no_send_artifacts
            for trigger_type in _artifact_summary_list(
                artifact,
                "candidate_for_human_review_trigger_types",
            )
        }
    )
    suppressed_types = sorted(
        {
            str(trigger_type)
            for artifact in no_send_artifacts
            for trigger_type in _artifact_summary_mapping(artifact, "suppressed_trigger_types")
        }
    )
    deferred_types = sorted(
        {
            str(trigger_type)
            for artifact in no_send_artifacts
            for trigger_type in _artifact_summary_list(artifact, "deferred_later_only_trigger_types")
        }
    )
    clean_run_count = sum(1 for artifact in no_send_artifacts if _artifact_clean(artifact))
    return {
        "run_count": len(no_send_artifacts),
        "clean_run_count": clean_run_count,
        "candidate_for_human_review_trigger_types": candidate_types,
        "suppressed_trigger_types": suppressed_types,
        "deferred_later_only_trigger_types": deferred_types,
    }


def _promotion_blockers(*, input_integrity: dict[str, Any], clean_run_count: int) -> list[str]:
    blockers = [
        "human_review_required_before_live_delivery",
        "live_scheduler_not_enabled",
        "no_send_shadow_only",
    ]
    if clean_run_count < MINIMUM_CLEAN_SHADOW_RUNS:
        blockers.append("minimum_clean_shadow_runs_not_met")
    if input_integrity.get("passed") is not True:
        blockers.append("input_integrity_failed")
    return sorted(blockers)


def _artifact_clean(artifact: dict[str, Any]) -> bool:
    if artifact.get("artifact_type") != "proactive_no_send_simulation":
        return False
    if artifact.get("shadow_mode") is not True:
        return False
    return not any(artifact.get(flag) is True for flag in _FORBIDDEN_TRUE_FLAGS)


def _artifact_summary_list(artifact: dict[str, Any], key: str) -> list[str]:
    summary = artifact.get("summary")
    if not isinstance(summary, dict):
        return []
    value = summary.get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _artifact_summary_mapping(artifact: dict[str, Any], key: str) -> dict[str, Any]:
    summary = artifact.get("summary")
    if not isinstance(summary, dict):
        return {}
    value = summary.get(key)
    if not isinstance(value, dict):
        return {}
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Build proactive no-send shadow decision pack.")
    parser.add_argument("--input", action="append", dest="inputs")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output")
    args = parser.parse_args()
    paths = [Path(path) for path in args.inputs] if args.inputs else None
    path = write_proactive_no_send_decision_pack(
        no_send_artifact_paths=paths,
        output_dir=Path(args.output_dir),
        output_path=Path(args.output) if args.output else None,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
