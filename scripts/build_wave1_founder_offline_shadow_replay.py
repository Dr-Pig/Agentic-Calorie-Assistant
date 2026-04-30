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


DEFAULT_FOUNDER_LIVE_ARTIFACT = ROOT / "artifacts" / "wave1_founder_e2e_live_diagnostic.json"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts"
MINIMUM_STRICT_REPLAY_RUNS_FOR_SHADOW_CANDIDATE = 3

REPAIR_FAILURE_INVARIANT_BY_FAMILY = {
    "commit_without_evidence": "commit_requires_evidence",
    "correction_without_target": "correction_requires_valid_target",
    "mutation_without_final_mapping": "mutation_requires_final_mapping",
    "manager_output_contract_violation": "manager_contract_schema_adherence",
}


def build_founder_offline_shadow_replay(founder_live_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    runs = [_run_summary(index=index, artifact=artifact) for index, artifact in enumerate(founder_live_artifacts, 1)]
    input_integrity = _input_integrity(founder_live_artifacts, runs)
    summary = _summary(runs, input_integrity=input_integrity)
    return _json_safe(
        {
            "artifact_type": "wave1_founder_offline_shadow_replay",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "readiness_claimed": False,
            "readiness_claim": _readiness_claim(),
            "shadow_or_canary_approved": False,
            "production_rollout_approved": False,
            "mutation_rollout_approved": False,
            "runtime_web_activation_approved": False,
            "input_integrity": input_integrity,
            "summary": summary,
            "strictness_gate": {
                "repaired_pass_is_diagnostic_only": True,
                "repaired_pass_unlocks_shadow": False,
                "single_profile_stability_is_shadow_ready": False,
                "model_diversity_required_for_shadow_candidate": True,
                "timeout_excluded_from_strict_pass_claim": True,
                "prepare_shadow_candidate_requires_repeated_all_strict": True,
                "minimum_strict_replay_runs": MINIMUM_STRICT_REPLAY_RUNS_FOR_SHADOW_CANDIDATE,
                "human_approval_required_for_shadow_candidate": True,
            },
            "runs": runs,
        }
    )


def write_founder_offline_shadow_replay(
    *,
    founder_live_artifact_paths: list[Path] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    paths = founder_live_artifact_paths or [DEFAULT_FOUNDER_LIVE_ARTIFACT]
    artifacts = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    replay = build_founder_offline_shadow_replay(artifacts)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "wave1_founder_offline_shadow_replay.json"
    path.write_text(json.dumps(replay, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _run_summary(*, index: int, artifact: dict[str, Any]) -> dict[str, Any]:
    summary = _dict(artifact.get("summary"))
    cases = [_case_summary(case) for case in _list(artifact.get("cases"))]
    repaired_cases = [case for case in cases if case.get("case_contract_status") == "repaired_pass"]
    case_count = _case_count(summary, artifact)
    strict_pass_count = int(summary.get("strict_pass_count") or 0)
    repaired_pass_count = int(summary.get("repaired_pass_count") or 0)
    contract_fail_count = int(summary.get("contract_fail_count") or 0)
    product_decision_required_count = int(summary.get("product_decision_required_count") or 0)
    provider_timeout_count = int(summary.get("provider_timeout_count") or 0)
    deferred_count = int(summary.get("deferred_count") or 0)
    all_strict = (
        case_count > 0
        and strict_pass_count == case_count
        and repaired_pass_count == 0
        and contract_fail_count == 0
        and int(summary.get("fail_count") or 0) == 0
        and product_decision_required_count == 0
        and provider_timeout_count == 0
        and deferred_count == 0
    )
    return {
        "run_index": index,
        "source_artifact_type": artifact.get("artifact_type"),
        "live_invoked": artifact.get("live_invoked") is True,
        "provider_profile_id": str(artifact.get("provider_profile_id") or "unknown"),
        "provider_profile_model": str(artifact.get("provider_profile_model") or "unknown"),
        "case_count": case_count,
        "strict_pass_count": strict_pass_count,
        "repaired_pass_count": repaired_pass_count,
        "contract_fail_count": contract_fail_count,
        "product_decision_required_count": product_decision_required_count,
        "provider_timeout_count": provider_timeout_count,
        "deferred_count": deferred_count,
        "all_strict": all_strict,
        "repaired_case_ids": sorted({str(case.get("case_id")) for case in repaired_cases if case.get("case_id")}),
        "repaired_cases": [
            {
                "case_id": case.get("case_id"),
                "repair_failure_family": case.get("repair_failure_family"),
                "failed_invariant": case.get("failed_invariant"),
            }
            for case in repaired_cases
        ],
        "cases": cases,
    }


def _case_summary(case: Any) -> dict[str, Any]:
    item = _dict(case)
    status = str(item.get("case_contract_status") or "unknown")
    repair_failure_family = str(item.get("repair_failure_family") or "").strip()
    failed_invariant = str(item.get("failed_invariant") or "").strip()
    if status == "repaired_pass":
        if not repair_failure_family:
            repair_failure_family = _extract_repair_failure_family(item)
        if not failed_invariant and repair_failure_family:
            failed_invariant = REPAIR_FAILURE_INVARIANT_BY_FAMILY.get(repair_failure_family, "")
    return {
        "case_id": item.get("case_id"),
        "case_contract_status": status,
        "repair_failure_family": repair_failure_family or None,
        "failed_invariant": failed_invariant or None,
    }


def _extract_repair_failure_family(case: dict[str, Any]) -> str:
    traces = _case_manager_traces(case)
    for trace in traces:
        repair_contract = _find_nested_key(trace, "x-repair-contract")
        if isinstance(repair_contract, dict):
            repair_family = str(repair_contract.get("failure_family") or "")
            if repair_family:
                return repair_family
        request_family = str(trace.get("request_failure_family") or "")
        if request_family:
            return request_family
    for trace in traces:
        family = _find_nested_key(trace, "failure_family")
        if isinstance(family, str) and family in REPAIR_FAILURE_INVARIANT_BY_FAMILY:
            return family
    return ""


def _case_manager_traces(case: dict[str, Any]) -> list[dict[str, Any]]:
    traces: list[dict[str, Any]] = []
    actual = _dict(case.get("actual_behavior"))
    for round_item in actual.get("manager_rounds") or []:
        if isinstance(round_item, dict):
            traces.append(_dict(round_item.get("trace")))
    trace = _dict(actual.get("manager_trace"))
    if trace:
        traces.append(trace)
    return traces


def _find_nested_key(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for child in value.values():
            found = _find_nested_key(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_nested_key(child, key)
            if found is not None:
                return found
    return None


def _summary(runs: list[dict[str, Any]], *, input_integrity: dict[str, Any]) -> dict[str, Any]:
    sample_run_count = len(runs)
    repaired_case_ids = sorted(
        {
            str(case_id)
            for run in runs
            for case_id in _list(run.get("repaired_case_ids"))
            if str(case_id)
        }
    )
    strict_pass_count = sum(int(run.get("strict_pass_count") or 0) for run in runs)
    repaired_pass_count = sum(int(run.get("repaired_pass_count") or 0) for run in runs)
    contract_fail_count = sum(int(run.get("contract_fail_count") or 0) for run in runs)
    provider_timeout_count = sum(int(run.get("provider_timeout_count") or 0) for run in runs)
    deferred_count = sum(int(run.get("deferred_count") or 0) for run in runs)
    total_case_count = sum(int(run.get("case_count") or 0) for run in runs)
    all_runs_strict = sample_run_count > 0 and all(run.get("all_strict") is True for run in runs)
    all_sampled_runs_7_strict = all_runs_strict and all(int(run.get("case_count") or 0) == 7 for run in runs)
    strict_replay_ready = (
        input_integrity.get("passed") is True
        and all_sampled_runs_7_strict
        and sample_run_count >= MINIMUM_STRICT_REPLAY_RUNS_FOR_SHADOW_CANDIDATE
        and provider_timeout_count == 0
        and deferred_count == 0
    )
    provider_profile_ids = sorted(
        {str(run.get("provider_profile_id")) for run in runs if str(run.get("provider_profile_id"))}
    )
    provider_profile_models = sorted(
        {str(run.get("provider_profile_model")) for run in runs if str(run.get("provider_profile_model"))}
    )
    single_profile_stability = (
        strict_replay_ready
        and len(provider_profile_ids) == 1
        and len(provider_profile_models) == 1
    )
    if strict_replay_ready and single_profile_stability:
        model_diversity_status = "model_diversity_missing"
    elif strict_replay_ready:
        model_diversity_status = "provider_diversity_present"
    else:
        model_diversity_status = "insufficient_evidence"
    return {
        "sample_run_count": sample_run_count,
        "total_case_count": total_case_count,
        "strict_pass_count": strict_pass_count,
        "repaired_pass_count": repaired_pass_count,
        "contract_fail_count": contract_fail_count,
        "provider_timeout_count": provider_timeout_count,
        "deferred_count": deferred_count,
        "repaired_case_ids": repaired_case_ids,
        "repaired_pass_rate": (repaired_pass_count / total_case_count) if total_case_count else 0.0,
        "strict_pass_rate": (strict_pass_count / total_case_count) if total_case_count else 0.0,
        "all_runs_strict": all_runs_strict,
        "all_sampled_runs_7_strict": all_sampled_runs_7_strict,
        "strict_replay_ready": strict_replay_ready,
        "single_profile_stability": single_profile_stability,
        "model_diversity_status": model_diversity_status,
        "provider_profile_ids": provider_profile_ids,
        "provider_profile_models": provider_profile_models,
        "minimum_strict_replay_runs_for_shadow_candidate": MINIMUM_STRICT_REPLAY_RUNS_FOR_SHADOW_CANDIDATE,
        "eligible_for_shadow_candidate": False,
    }


def _input_integrity(founder_live_artifacts: list[dict[str, Any]], runs: list[dict[str, Any]]) -> dict[str, Any]:
    blockers: list[str] = []
    if not founder_live_artifacts:
        blockers.append("missing_founder_live_artifact")
    for artifact in founder_live_artifacts:
        if artifact.get("artifact_type") != "wave1_founder_e2e_live_diagnostic":
            blockers.append("input_artifact_type_invalid")
        if artifact.get("readiness_claimed") is True:
            blockers.append("input_readiness_claimed")
        if artifact.get("production_selected") is True:
            blockers.append("input_production_selected")
        if artifact.get("runtime_web_activation_approved") is True:
            blockers.append("input_runtime_web_activation_approved")
        if artifact.get("mutation_enabled") is True:
            blockers.append("input_mutation_enabled")
    for run in runs:
        for case in _list(run.get("cases")):
            item = _dict(case)
            if item.get("case_contract_status") != "repaired_pass":
                continue
            if not item.get("repair_failure_family"):
                blockers.append("repaired_case_missing_repair_failure_family")
            if not item.get("failed_invariant"):
                blockers.append("repaired_case_missing_failed_invariant")
    return {
        "passed": not blockers,
        "blockers": sorted(set(blockers)),
    }


def _case_count(summary: dict[str, Any], artifact: dict[str, Any]) -> int:
    counted = (
        int(summary.get("pass_count") or 0)
        + int(summary.get("fail_count") or 0)
        + int(summary.get("product_decision_required_count") or 0)
        + int(summary.get("deferred_count") or 0)
    )
    return counted or len(_list(artifact.get("cases")))


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
            "artifacts": ["artifacts/wave1_founder_e2e_live_diagnostic.json"],
            "producers": ["scripts/build_wave1_founder_offline_shadow_replay.py"],
            "legacy_oracle_used": False,
        },
        allowed_next_stage=None,
        forbidden_claims=[
            "product_ready",
            "user_facing_ready",
            "mutation_ready",
            "production_ready",
            "automatic_shadow_rollout",
        ],
        readiness_claimed=False,
    )


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Wave 1 Founder offline shadow replay artifact.")
    parser.add_argument(
        "--founder-live-artifact",
        action="append",
        default=[],
        help="Founder live diagnostic artifact path. May be supplied multiple times.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    paths = [Path(item) for item in args.founder_live_artifact] or [DEFAULT_FOUNDER_LIVE_ARTIFACT]
    path = write_founder_offline_shadow_replay(
        founder_live_artifact_paths=paths,
        output_dir=Path(args.output_dir),
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
