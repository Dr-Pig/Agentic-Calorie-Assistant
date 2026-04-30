from __future__ import annotations

import argparse
from collections import defaultdict
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


def build_founder_provider_robustness_matrix(founder_live_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    input_integrity = _input_integrity(founder_live_artifacts)
    provider_rows = _provider_rows(founder_live_artifacts)
    matrix_summary = _matrix_summary(provider_rows)
    return _json_safe(
        {
            "artifact_type": "wave1_founder_provider_robustness_matrix",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "readiness_claimed": False,
            "readiness_claim": _readiness_claim(),
            "production_manager_selected": False,
            "shadow_or_canary_approved": False,
            "input_integrity": input_integrity,
            "matrix_summary": matrix_summary,
            "provider_rows": provider_rows,
            "matrix_policy": {
                "tracks_repaired_rate": True,
                "tracks_timeout_rate": True,
                "pass_fail_only_forbidden": True,
                "single_model_success_is_not_model_inversion": True,
                "grokfast_diagnostic_only": True,
                "deepseek_comparison_only": True,
                "production_selection_allowed": False,
            },
        }
    )


def write_founder_provider_robustness_matrix(
    *,
    founder_live_artifact_paths: list[Path] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    paths = founder_live_artifact_paths or [DEFAULT_FOUNDER_LIVE_ARTIFACT]
    artifacts = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    matrix = build_founder_provider_robustness_matrix(artifacts)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "wave1_founder_provider_robustness_matrix.json"
    path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _provider_rows(founder_live_artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for artifact in founder_live_artifacts:
        profile_id = str(artifact.get("provider_profile_id") or "unknown")
        model = str(artifact.get("provider_profile_model") or "unknown")
        grouped[(profile_id, model)].append(artifact)
    rows: list[dict[str, Any]] = []
    for (profile_id, model), artifacts in sorted(grouped.items()):
        summaries = [_dict(artifact.get("summary")) for artifact in artifacts]
        strict_pass_count = sum(int(summary.get("strict_pass_count") or 0) for summary in summaries)
        repaired_pass_count = sum(int(summary.get("repaired_pass_count") or 0) for summary in summaries)
        contract_fail_count = sum(int(summary.get("contract_fail_count") or 0) for summary in summaries)
        provider_timeout_count = sum(int(summary.get("provider_timeout_count") or 0) for summary in summaries)
        deferred_count = sum(int(summary.get("deferred_count") or 0) for summary in summaries)
        pass_count = sum(int(summary.get("pass_count") or 0) for summary in summaries)
        fail_count = sum(int(summary.get("fail_count") or 0) for summary in summaries)
        base_case_count = max(
            pass_count + fail_count + deferred_count,
            strict_pass_count + repaired_pass_count + contract_fail_count + deferred_count,
        )
        timeout_not_already_counted = max(0, provider_timeout_count - max(fail_count, contract_fail_count))
        total_case_count = base_case_count + timeout_not_already_counted
        rate_denominator = (
            strict_pass_count
            + repaired_pass_count
            + contract_fail_count
            + provider_timeout_count
            + deferred_count
        )
        if total_case_count == 0:
            total_case_count = rate_denominator
        repaired_case_ids = sorted(
            {
                str(case_id)
                for summary in summaries
                for case_id in _list(summary.get("repaired_case_ids"))
                if str(case_id)
            }
        )
        all_runs_strict = bool(artifacts) and all(
            int(summary.get("repaired_pass_count") or 0) == 0
            and int(summary.get("contract_fail_count") or 0) == 0
            and int(summary.get("provider_timeout_count") or 0) == 0
            and int(summary.get("deferred_count") or 0) == 0
            and int(summary.get("fail_count") or 0) == 0
            and int(summary.get("strict_pass_count") or 0) > 0
            for summary in summaries
        )
        rows.append(
            {
                "provider_profile_id": profile_id,
                "provider_profile_model": model,
                "matrix_role": _matrix_role(profile_id),
                "sample_run_count": len(artifacts),
                "total_case_count": total_case_count,
                "pass_count": pass_count,
                "fail_count": fail_count,
                "strict_pass_count": strict_pass_count,
                "repaired_pass_count": repaired_pass_count,
                "contract_fail_count": contract_fail_count,
                "provider_timeout_count": provider_timeout_count,
                "deferred_count": deferred_count,
                "strict_pass_rate": (strict_pass_count / total_case_count) if total_case_count else 0.0,
                "repaired_pass_rate": (repaired_pass_count / total_case_count) if total_case_count else 0.0,
                "contract_fail_rate": (contract_fail_count / total_case_count) if total_case_count else 0.0,
                "timeout_rate": (provider_timeout_count / total_case_count) if total_case_count else 0.0,
                "deferred_rate": (deferred_count / total_case_count) if total_case_count else 0.0,
                "all_runs_strict": all_runs_strict,
                "single_profile_all_strict": all_runs_strict,
                "repaired_case_ids": repaired_case_ids,
                "readiness_owner": False,
                "production_selected": False,
            }
        )
    return rows


def _matrix_role(profile_id: str) -> str:
    lowered = profile_id.lower()
    if "deepseek" in lowered:
        return "comparison_only"
    if "grok" in lowered:
        return "diagnostic_candidate"
    return "alternate_diagnostic_candidate"


def _matrix_summary(provider_rows: list[dict[str, Any]]) -> dict[str, Any]:
    diagnostic_rows = [
        row
        for row in provider_rows
        if row.get("matrix_role") in {"diagnostic_candidate", "alternate_diagnostic_candidate"}
    ]
    primary_rows = [row for row in diagnostic_rows if row.get("matrix_role") == "diagnostic_candidate"]
    alternate_rows = [row for row in diagnostic_rows if row.get("matrix_role") == "alternate_diagnostic_candidate"]
    strict_pass_count = sum(int(row.get("strict_pass_count") or 0) for row in diagnostic_rows)
    repaired_pass_count = sum(int(row.get("repaired_pass_count") or 0) for row in diagnostic_rows)
    contract_fail_count = sum(int(row.get("contract_fail_count") or 0) for row in diagnostic_rows)
    provider_timeout_count = sum(int(row.get("provider_timeout_count") or 0) for row in diagnostic_rows)
    deferred_count = sum(int(row.get("deferred_count") or 0) for row in diagnostic_rows)
    total_case_count = sum(int(row.get("total_case_count") or 0) for row in diagnostic_rows)
    primary_all_strict = bool(primary_rows) and all(row.get("single_profile_all_strict") is True for row in primary_rows)
    alternate_all_strict = bool(alternate_rows) and all(row.get("single_profile_all_strict") is True for row in alternate_rows)
    if primary_all_strict and alternate_all_strict:
        provider_diversity_status = "provider_diversity_present"
        model_inversion_evidence_passed = True
        contract_overfit_risk = False
    elif primary_all_strict and alternate_rows:
        provider_diversity_status = "contract_overfit_risk"
        model_inversion_evidence_passed = False
        contract_overfit_risk = True
    else:
        provider_diversity_status = "model_diversity_missing"
        model_inversion_evidence_passed = False
        contract_overfit_risk = False
    return {
        "provider_diversity_status": provider_diversity_status,
        "model_inversion_evidence_passed": model_inversion_evidence_passed,
        "contract_overfit_risk": contract_overfit_risk,
        "diagnostic_profile_count": len(diagnostic_rows),
        "alternate_profile_count": len(alternate_rows),
        "strict_pass_count": strict_pass_count,
        "repaired_pass_count": repaired_pass_count,
        "contract_fail_count": contract_fail_count,
        "provider_timeout_count": provider_timeout_count,
        "deferred_count": deferred_count,
        "strict_pass_rate": (strict_pass_count / total_case_count) if total_case_count else 0.0,
        "repaired_pass_rate": (repaired_pass_count / total_case_count) if total_case_count else 0.0,
        "timeout_rate": (provider_timeout_count / total_case_count) if total_case_count else 0.0,
        "deferred_rate": (deferred_count / total_case_count) if total_case_count else 0.0,
    }


def _input_integrity(founder_live_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
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
    return {
        "passed": not blockers,
        "blockers": sorted(set(blockers)),
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
            "artifacts": ["artifacts/wave1_founder_e2e_live_diagnostic.json"],
            "producers": ["scripts/build_wave1_founder_provider_robustness_matrix.py"],
            "legacy_oracle_used": False,
        },
        allowed_next_stage=None,
        forbidden_claims=[
            "product_ready",
            "user_facing_ready",
            "mutation_ready",
            "production_ready",
            "production_manager",
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
    parser = argparse.ArgumentParser(description="Build Wave 1 Founder provider robustness matrix.")
    parser.add_argument(
        "--founder-live-artifact",
        action="append",
        default=[],
        help="Founder live diagnostic artifact path. May be supplied multiple times.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    paths = [Path(item) for item in args.founder_live_artifact] or [DEFAULT_FOUNDER_LIVE_ARTIFACT]
    path = write_founder_provider_robustness_matrix(
        founder_live_artifact_paths=paths,
        output_dir=Path(args.output_dir),
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
