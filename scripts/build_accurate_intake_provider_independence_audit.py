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


PROVIDER_MARKERS = ("grok", "grokfast", "kimi", "builderspace", "deepseek", "gemini", "gpt-5")

PRODUCT_SEMANTIC_PATHS = (
    Path("docs/specs/WAVE_1_PHASE_B2_SEMANTIC_DECISION_REGISTER.md"),
    Path("docs/quality/accurate_intake_mvp_ux_semantic_cases.json"),
    Path("docs/quality/accurate_intake_one_day_self_use_cases.json"),
    Path("docs/quality/accurate_intake_contract_legal_flow_matrix.json"),
    Path("docs/quality/accurate_intake_basket_holdout_cases.json"),
)
MANAGER_CONTRACT_PATHS = (
    ROOT / "app" / "runtime" / "agent" / "founder_live_manager_contract.py",
    ROOT / "docs" / "specs" / "APP_ENGINEERING_OPERATING_ENTRY.md",
)
FOOD_KB_PATHS = (
    ROOT / "app" / "knowledge" / "small_anchor_store_tw.json",
    ROOT / "app" / "knowledge" / "exact_item_cards_tw.json",
)
DECISION_PACK_PATH = ROOT / "scripts" / "build_accurate_intake_mvp_live_decision_pack.py"
LIVE_DIAGNOSTIC_PATH = ROOT / "scripts" / "run_accurate_intake_mvp_live_diagnostic.py"


def build_provider_independence_audit(
    *,
    decision_pack_artifact: dict[str, Any] | None = None,
    live_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    product_offenders = _provider_reference_offenders(_read_existing(PRODUCT_SEMANTIC_PATHS))
    manager_contract_offenders = _marker_offenders(
        _read_existing(MANAGER_CONTRACT_PATHS),
        markers=("grok", "grokfast", "kimi", "builderspace-kimi", "builderspace-grok"),
    )
    food_kb_offenders = _marker_offenders(
        _read_existing(FOOD_KB_PATHS),
        markers=("provider_profile", "builderspace", "grok", "kimi", "deepseek", "gemini"),
    )
    decision_pack_shape = _decision_pack_preserves_provider_boundary(decision_pack_artifact)
    live_artifact_shape = _live_artifact_carries_provider_identity(live_artifact)
    checks = {
        "no_product_semantic_enum_references_provider_names": not product_offenders,
        "no_manager_contract_text_hardcodes_grokfast_behavior": not manager_contract_offenders,
        "no_food_kb_source_references_provider_profile": not food_kb_offenders,
        "decision_pack_separates_provider_diagnostic_evidence_from_product_truth": decision_pack_shape,
        "live_artifacts_always_carry_provider_profile_identity": live_artifact_shape,
    }
    blockers: list[str] = []
    if product_offenders:
        blockers.append("product_semantic_provider_reference")
    if manager_contract_offenders:
        blockers.append("manager_contract_provider_hardcode")
    if food_kb_offenders:
        blockers.append("food_kb_provider_reference")
    for check_id, passed in checks.items():
        if passed is not True:
            if check_id == "decision_pack_separates_provider_diagnostic_evidence_from_product_truth":
                blockers.append("decision_pack_provider_evidence_truth_boundary_invalid")
            elif check_id == "live_artifacts_always_carry_provider_profile_identity":
                blockers.append("live_artifact_provider_identity_or_non_claim_invalid")
            else:
                blockers.append(check_id)
    return {
        "artifact_type": "accurate_intake_provider_independence_audit",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "claim_scope": "provider_independence_audit",
        "passed": not blockers,
        "provider_independence_audit": checks,
        "blockers": sorted(set(blockers)),
        "offenders": {
            "product_semantic_provider_references": product_offenders,
            "manager_contract_provider_references": manager_contract_offenders,
            "food_kb_provider_references": food_kb_offenders,
        },
        "readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "production_selected": False,
    }


def _read_existing(paths: tuple[Path, ...]) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for path in paths:
        actual = path if path.is_absolute() else ROOT / path
        if not actual.exists():
            continue
        resolved[actual.relative_to(ROOT).as_posix()] = _read_text(actual)
    return resolved


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig") if path.exists() else ""


def _provider_reference_offenders(contents_by_path: dict[str, str]) -> list[dict[str, str]]:
    return _marker_offenders(contents_by_path, markers=PROVIDER_MARKERS)


def _marker_offenders(contents_by_path: dict[str, str], *, markers: tuple[str, ...]) -> list[dict[str, str]]:
    offenders: list[dict[str, str]] = []
    for path, content in contents_by_path.items():
        lowered = content.casefold()
        for marker in markers:
            if marker.casefold() in lowered:
                offenders.append({"path": path, "provider_marker": marker})
                break
    return offenders


def _decision_pack_preserves_provider_boundary(artifact: dict[str, Any] | None) -> bool:
    if artifact is None:
        source = _read_text(DECISION_PACK_PATH)
        return (
            "provider_robustness_summary" in source
            and '"production_selected"' in source
            and '"live_provider_used_as_truth"' in source
            and "if live_artifact.get(key) is True" in source
        )
    if artifact.get("artifact_type") != "accurate_intake_mvp_live_decision_pack":
        return False
    if artifact.get("production_selected") is not False:
        return False
    if artifact.get("product_readiness_claimed") is not False:
        return False
    if artifact.get("private_self_use_approved") is not False:
        return False
    if artifact.get("live_provider_used_as_truth") is True:
        return False
    if not isinstance(artifact.get("provider_robustness_summary"), dict):
        return False
    decision_boundary = artifact.get("decision_boundary")
    if not isinstance(decision_boundary, dict):
        return False
    return decision_boundary.get("production_manager_selected") is False


def _live_artifact_carries_provider_identity(artifact: dict[str, Any] | None) -> bool:
    if artifact is None:
        source = _read_text(LIVE_DIAGNOSTIC_PATH)
        return "provider_profile_id" in source and "provider_profile_model" in source and '"production_selected": False' in source
    if artifact.get("artifact_type") != "accurate_intake_mvp_live_diagnostic":
        return False
    if not artifact.get("provider_profile_id") or not artifact.get("provider_profile_model"):
        return False
    if artifact.get("production_selected") is not False:
        return False
    if artifact.get("product_readiness_claimed") is not False:
        return False
    if artifact.get("private_self_use_approved") is not False:
        return False
    return artifact.get("live_provider_used_as_truth") is not True


def write_provider_independence_audit(*, output_path: Path) -> Path:
    audit = build_provider_independence_audit()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Accurate Intake provider-independence audit.")
    parser.add_argument("--output", default=str(ROOT / "artifacts" / "accurate_intake_provider_independence_audit.json"))
    args = parser.parse_args()
    path = write_provider_independence_audit(output_path=Path(args.output))
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
