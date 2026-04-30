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


DEFAULT_INPUT = ROOT / "artifacts" / "wave1_phase_b2_evidence_synthesis_smoke.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "wave1_phase_b2_local_p0_closure_audit.json"

TRUSTED_SOURCE_FORBIDDEN_SCOPE = "B-2 synthetic trusted database fixture"
TRUSTED_SOURCE_SCOPE = "B-2 local app-owned fixture/store evidence"
LOCAL_STORE_BACKING = "local_app_owned_test_aligned_store"
SEMANTIC_AUTHORITY_SOURCE = "synthetic_manager_structured_fixture"

REQUIRED_CASE_CHAIN_FIELDS = (
    "manager_semantic_decision",
    "retrieval_intent_source",
    "source_selection",
    "packet_consumption",
    "manager_pass_2",
)


def audit_phase_b2_local_p0_closure(report_data: dict[str, Any]) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    local_evidence_provenance = _check_local_evidence_provenance(report_data, blockers)
    owner_lineage = _check_runtime_owner_lineage(report_data, blockers)
    runtime_web_activation_approved = bool(report_data.get("runtime_web_activation_approved", False))
    if runtime_web_activation_approved:
        _add(
            blockers,
            "runtime_web_activation_forbidden",
            "B2 local P0 closure must not approve runtime web activation.",
        )

    return _json_safe(
        {
            "artifact_type": "wave1_phase_b2_local_p0_closure_audit",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "passed": not blockers,
            "blockers": blockers,
            "runtime_web_activation_approved": runtime_web_activation_approved,
            "official_runtime_backed_case_count": owner_lineage["runtime_backed_case_count"],
            "local_evidence_provenance": local_evidence_provenance,
            "owner_lineage": owner_lineage,
        }
    )


def _check_local_evidence_provenance(report_data: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    manifest = report_data.get("trusted_source_manifest")
    entries = manifest.get("entries") if isinstance(manifest, dict) else None
    invalid_entries: list[dict[str, Any]] = []
    if not isinstance(entries, list) or not entries:
        _add(blockers, "trusted_source_manifest_missing", "B2 local P0 closure requires trusted_source_manifest entries.")
        entries = []

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            invalid_entries.append({"index": index, "reason": "entry_not_object"})
            continue
        scope = str(entry.get("scope") or "")
        if TRUSTED_SOURCE_FORBIDDEN_SCOPE in scope:
            _add(
                blockers,
                "trusted_source_manifest_synthetic_wording",
                "Local app-owned evidence stores must not be described as a synthetic trusted database fixture.",
                index=index,
            )
            invalid_entries.append({"index": index, "scope": scope})
        if entry.get("evidence_authority") != "local_app_owned_store":
            invalid_entries.append({"index": index, "reason": "missing_local_evidence_authority"})
        if entry.get("semantic_authority") != "none":
            invalid_entries.append({"index": index, "reason": "semantic_authority_must_be_none"})
        if entry.get("runtime_web_activation") is not False:
            invalid_entries.append({"index": index, "reason": "runtime_web_activation_must_be_false"})

    seed_manifest = report_data.get("minimal_db_seed_manifest")
    seed_manifest_ok = isinstance(seed_manifest, dict) and seed_manifest.get("store_backing") == LOCAL_STORE_BACKING
    if not seed_manifest_ok:
        _add(
            blockers,
            "minimal_db_seed_manifest_provenance_missing",
            "minimal_db_seed_manifest must declare local app-owned test-aligned store backing.",
        )

    passed = not invalid_entries and seed_manifest_ok
    return {
        "passed": passed,
        "trusted_source_scope": TRUSTED_SOURCE_SCOPE,
        "local_store_backing": seed_manifest.get("store_backing") if isinstance(seed_manifest, dict) else None,
        "invalid_entries": invalid_entries,
    }


def _check_runtime_owner_lineage(report_data: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    cases = report_data.get("cases")
    missing: list[dict[str, Any]] = []
    source_selection_violations: list[dict[str, Any]] = []
    final_mapping_violations: list[dict[str, Any]] = []
    runtime_backed_case_count = 0

    for case in cases if isinstance(cases, list) else []:
        if not isinstance(case, dict):
            continue
        case_id = case.get("case_id")
        trace = case.get("producer_trace")
        if not isinstance(trace, dict) or trace.get("backing_class") != "runtime_backed":
            continue
        runtime_backed_case_count += 1
        for field in REQUIRED_CASE_CHAIN_FIELDS:
            if field not in case:
                missing.append({"case_id": case_id, "field": field})

        manager_decision = case.get("manager_semantic_decision")
        if not isinstance(manager_decision, dict) or manager_decision.get("semantic_authority_source") != SEMANTIC_AUTHORITY_SOURCE:
            missing.append({"case_id": case_id, "field": "manager_semantic_decision.semantic_authority_source"})
        if case.get("retrieval_intent_source") != "manager_semantic_decision" or case.get("runner_inferred_semantics") is not False:
            missing.append({"case_id": case_id, "field": "retrieval_intent_source"})

        source_selection = case.get("source_selection")
        if not isinstance(source_selection, dict):
            missing.append({"case_id": case_id, "field": "source_selection"})
        else:
            if source_selection.get("decides_logged_or_draft") is not False:
                source_selection_violations.append({"case_id": case_id})
                _add(
                    blockers,
                    "source_selection_semantic_owner_forbidden",
                    "Source selection must not decide logged/draft semantics.",
                    case_id=case_id,
                )
            if source_selection.get("web_allowed") is not False:
                source_selection_violations.append({"case_id": case_id, "field": "web_allowed"})

        item_results = ((case.get("manager_pass_2") or {}).get("item_results") or [])
        if not item_results:
            missing.append({"case_id": case_id, "field": "manager_pass_2.item_results"})
        for item_index, item in enumerate(item_results):
            if not isinstance(item, dict):
                missing.append({"case_id": case_id, "field": f"manager_pass_2.item_results[{item_index}]"})
                continue
            final_mapping = item.get("final_mapping")
            if not isinstance(final_mapping, dict) or final_mapping.get("final_mapping_owner") != "nutrition_final_mapping":
                final_mapping_violations.append({"case_id": case_id, "item_index": item_index})

    if missing:
        _add(
            blockers,
            "runtime_owner_lineage_incomplete",
            "Runtime-backed B2 cases must expose first-class owner lineage fields.",
            missing=missing,
        )
    if final_mapping_violations:
        _add(
            blockers,
            "final_mapping_owner_missing",
            "B2 local P0 closure requires nutrition_final_mapping ownership on item results.",
            violations=final_mapping_violations,
        )
    if runtime_backed_case_count == 0:
        _add(blockers, "runtime_backed_cases_missing", "B2 local P0 closure requires runtime-backed official cases.")

    return {
        "passed": not missing and not source_selection_violations and not final_mapping_violations and runtime_backed_case_count > 0,
        "runtime_backed_case_count": runtime_backed_case_count,
        "missing": missing,
        "source_selection_semantic_owner_violations": source_selection_violations,
        "final_mapping_owner_violations": final_mapping_violations,
    }


def _add(blockers: list[dict[str, Any]], code: str, detail: str, **extra: Any) -> None:
    blockers.append({"code": code, "detail": detail, **extra})


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit B2 local P0 closure provenance and owner lineage.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="B2 evidence synthesis smoke artifact path.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Audit output path.")
    args = parser.parse_args()

    report = audit_phase_b2_local_p0_closure(_read_json(Path(args.input)))
    output = _write_json(Path(args.output), report)
    print(json.dumps({"report_path": str(output), "passed": report["passed"], "blocker_count": len(report["blockers"])}, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
