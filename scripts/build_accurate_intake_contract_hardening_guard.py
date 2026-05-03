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


DEFAULT_CHANGE_MANIFEST = ROOT / "docs" / "quality" / "accurate_intake_contract_change_manifest_pr84.json"
DEFAULT_LEGAL_FLOW_MATRIX = ROOT / "docs" / "quality" / "accurate_intake_contract_legal_flow_matrix.json"
DEFAULT_SEMANTIC_DRIFT_AUDIT = ROOT / "docs" / "quality" / "accurate_intake_pr74_84_semantic_drift_audit.json"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts"


def build_accurate_intake_contract_hardening_guard(
    change_manifest_artifact: dict[str, Any],
    *,
    legal_flow_matrix_artifact: dict[str, Any] | None = None,
    semantic_drift_audit_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    input_blockers = _input_blockers(
        change_manifest_artifact,
        legal_flow_matrix_artifact=legal_flow_matrix_artifact,
        semantic_drift_audit_artifact=semantic_drift_audit_artifact,
    )
    change_id = str(change_manifest_artifact.get("change_id") or "")
    fixed_case_ids = _string_list(change_manifest_artifact.get("fixed_case_ids"))
    canonical_rule_exists = (
        change_manifest_artifact.get("canonical_rule_exists") is True
        and bool(_string_list(change_manifest_artifact.get("canonical_rule_refs")))
    )
    legal_flows_broken = _sorted_unique(
        [
            *_string_list(change_manifest_artifact.get("legal_flows_broken")),
            *_string_list(_dict(legal_flow_matrix_artifact).get("legal_flows_broken")),
        ]
    )
    legal_flow_matrix_updated = _legal_flow_matrix_updated(
        change_id,
        change_manifest_artifact=change_manifest_artifact,
        legal_flow_matrix_artifact=legal_flow_matrix_artifact,
    )
    holdout_tests_added = (
        change_manifest_artifact.get("holdout_tests_added") is True
        and bool(_string_list(change_manifest_artifact.get("holdout_test_refs")))
    )
    raw_text_routing_risk = change_manifest_artifact.get("raw_text_routing_risk") is True
    provider_overfit_risk = str(change_manifest_artifact.get("provider_overfit_risk") or "unknown")
    live_failure_only = change_manifest_artifact.get("live_failure_only") is True
    semantic_drift_audit_present = _dict(semantic_drift_audit_artifact).get(
        "artifact_type"
    ) == "accurate_intake_pr74_84_semantic_drift_audit"

    blockers: list[str] = []
    if live_failure_only:
        blockers.append("live_failure_only")
    if not canonical_rule_exists:
        blockers.append("canonical_rule_missing")
    if not legal_flow_matrix_updated:
        blockers.append("legal_flow_matrix_missing_or_stale")
    if not holdout_tests_added:
        blockers.append("holdout_tests_missing")
    if raw_text_routing_risk:
        blockers.append("raw_text_routing_risk")
    if provider_overfit_risk == "high":
        blockers.append("provider_overfit_risk_high")
    if legal_flows_broken:
        blockers.append("legal_flows_broken")
    if not semantic_drift_audit_present:
        blockers.append("semantic_drift_audit_missing")
    blockers.extend(input_blockers)
    blockers = _sorted_unique(blockers)
    merge_allowed = not blockers

    return _json_safe(
        {
            "artifact_type": "accurate_intake_contract_hardening_guard",
            "artifact_schema_version": "1.0",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "claim_scope": "diagnostic_governance",
            "readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_selected": False,
            "mutation_rollout_approved": False,
            "runtime_web_activation_approved": False,
            "change_id": change_id,
            "proposed_change_type": _optional_string(change_manifest_artifact.get("proposed_change_type")),
            "fixed_case_ids": fixed_case_ids,
            "canonical_rule_exists": canonical_rule_exists,
            "canonical_rule_refs": _string_list(change_manifest_artifact.get("canonical_rule_refs")),
            "legal_flow_matrix_updated": legal_flow_matrix_updated,
            "holdout_tests_added": holdout_tests_added,
            "holdout_test_refs": _string_list(change_manifest_artifact.get("holdout_test_refs")),
            "raw_text_routing_risk": raw_text_routing_risk,
            "provider_overfit_risk": provider_overfit_risk,
            "legal_flows_broken": legal_flows_broken,
            "live_failure_only": live_failure_only,
            "semantic_drift_audit_present": semantic_drift_audit_present,
            "merge_allowed": merge_allowed,
            "blockers": blockers,
            "contract_hardening_debt": {
                "present": not merge_allowed,
                "reasons": blockers,
            },
            "input_integrity": {
                "passed": not input_blockers,
                "blockers": input_blockers,
            },
            "decision_boundary": {
                "live_failure_unlocks_contract_hardening": False,
                "live_failure_unlocks_attribution_audit": True,
                "raw_text_routing_allowed": False,
                "fixture_shape_can_define_product_truth": False,
                "private_self_use_candidate_blocked_when_debt_present": True,
            },
        }
    )


def write_accurate_intake_contract_hardening_guard(
    *,
    change_manifest_path: Path = DEFAULT_CHANGE_MANIFEST,
    legal_flow_matrix_path: Path = DEFAULT_LEGAL_FLOW_MATRIX,
    semantic_drift_audit_path: Path = DEFAULT_SEMANTIC_DRIFT_AUDIT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    output_path: Path | None = None,
) -> Path:
    change_manifest = _load_json(change_manifest_path)
    legal_flow_matrix = _load_json(legal_flow_matrix_path)
    semantic_drift_audit = _load_json(semantic_drift_audit_path)
    artifact = build_accurate_intake_contract_hardening_guard(
        change_manifest,
        legal_flow_matrix_artifact=legal_flow_matrix,
        semantic_drift_audit_artifact=semantic_drift_audit,
    )
    path = output_path or output_dir / "accurate_intake_contract_hardening_guard.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _input_blockers(
    change_manifest_artifact: dict[str, Any],
    *,
    legal_flow_matrix_artifact: dict[str, Any] | None,
    semantic_drift_audit_artifact: dict[str, Any] | None,
) -> list[str]:
    blockers: list[str] = []
    if change_manifest_artifact.get("artifact_type") != "accurate_intake_contract_change_manifest":
        blockers.append("change_manifest_artifact_type_invalid")
    if _dict(legal_flow_matrix_artifact).get("artifact_type") != "accurate_intake_contract_legal_flow_matrix":
        blockers.append("legal_flow_matrix_artifact_type_invalid")
    if _dict(semantic_drift_audit_artifact).get(
        "artifact_type"
    ) != "accurate_intake_pr74_84_semantic_drift_audit":
        blockers.append("semantic_drift_audit_artifact_type_invalid")
    return _sorted_unique(blockers)


def _legal_flow_matrix_updated(
    change_id: str,
    *,
    change_manifest_artifact: dict[str, Any],
    legal_flow_matrix_artifact: dict[str, Any] | None,
) -> bool:
    matrix = _dict(legal_flow_matrix_artifact)
    if change_manifest_artifact.get("legal_flow_matrix_updated") is not True:
        return False
    if matrix.get("status") != "pass":
        return False
    if change_id and change_id not in _string_list(matrix.get("updated_for_change_ids")):
        return False
    return bool(_list(matrix.get("flows")))


def _load_json(path: Path) -> dict[str, Any]:
    return _dict(json.loads(path.read_text(encoding="utf-8-sig")))


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in _list(value) if str(item)]


def _optional_string(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _sorted_unique(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Accurate Intake contract hardening anti-overfit guard.")
    parser.add_argument("--change-manifest", default=str(DEFAULT_CHANGE_MANIFEST))
    parser.add_argument("--legal-flow-matrix", default=str(DEFAULT_LEGAL_FLOW_MATRIX))
    parser.add_argument("--semantic-drift-audit", default=str(DEFAULT_SEMANTIC_DRIFT_AUDIT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output")
    args = parser.parse_args()
    path = write_accurate_intake_contract_hardening_guard(
        change_manifest_path=Path(args.change_manifest),
        legal_flow_matrix_path=Path(args.legal_flow_matrix),
        semantic_drift_audit_path=Path(args.semantic_drift_audit),
        output_dir=Path(args.output_dir),
        output_path=Path(args.output) if args.output else None,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
