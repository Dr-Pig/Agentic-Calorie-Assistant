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


DEFAULT_MANIFEST_PATH = ROOT / "docs" / "quality" / "accurate_intake_mvp_live_diagnostic_case_manifest.json"
DEFAULT_TRACE_ARTIFACT_PATH = ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic_full_suite.json"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_mvp_live_case_replay.json"

_FORBIDDEN_TRUE_FLAGS = (
    "runner_inferred_semantics",
    "semantic_keyword_oracle_used",
    "raw_text_routing_used",
    "deterministic_semantic_override_used",
    "fixture_oracle_rewrote_manager_decision",
    "app_shell_semantic_owner",
    "websearch_snippet_as_truth",
    "macro_invented",
    "readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
)


def build_live_case_replay(
    *,
    manifest: dict[str, Any],
    trace_artifact: dict[str, Any],
) -> dict[str, Any]:
    manifest_cases = [_dict(item) for item in _list(manifest.get("cases"))]
    source_cases_by_id = _source_cases_by_manifest_or_runtime_id(trace_artifact)
    trace_layers = [str(item.get("layer_id")) for item in _list(manifest.get("trace_layers"))]
    case_grades = [
        _grade_case(manifest_case, source_cases_by_id.get(str(manifest_case.get("case_id") or "")), trace_layers)
        for manifest_case in manifest_cases
    ]
    blockers = _input_blockers(manifest=manifest, trace_artifact=trace_artifact, case_grades=case_grades)
    failed_cases = [case for case in case_grades if case["status"] != "pass"]
    return _json_safe(
        {
            "artifact_type": "accurate_intake_mvp_live_case_replay",
            "artifact_schema_version": "1.0",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "claim_scope": "offline_manifest_trace_replay",
            "manifest_id": manifest.get("manifest_id"),
            "source_artifact_type": trace_artifact.get("artifact_type"),
            "live_invoked_by_replay": False,
            "readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "fooddb_expansion_approved": False,
            "whole_product_mvp_claimed": False,
            "semantic_keyword_oracle_used": False,
            "runner_inferred_semantics": False,
            "summary": {
                "manifest_case_count": len(manifest_cases),
                "source_case_count": len(source_cases_by_id),
                "graded_case_count": len(case_grades),
                "failed_case_count": len(failed_cases),
                "missing_case_count": sum(1 for case in case_grades if "case_missing" in case["blockers"]),
                "trace_layer_failure_count": sum(
                    1 for case in case_grades if any(str(item).startswith("missing_layer:") for item in case["blockers"])
                ),
                "semantic_oracle_failure_count": sum(
                    1
                    for case in case_grades
                    if any(str(item).startswith("forbidden_true_flag:") for item in case["blockers"])
                ),
                "strict_trace_replay_passed": not blockers and not failed_cases,
            },
            "input_integrity": {"passed": not blockers, "blockers": blockers},
            "cases": case_grades,
        }
    )


def write_live_case_replay(
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    trace_artifact_path: Path = DEFAULT_TRACE_ARTIFACT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    manifest = _read_json(manifest_path)
    trace_artifact = _read_json(trace_artifact_path)
    replay = build_live_case_replay(manifest=manifest, trace_artifact=trace_artifact)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(replay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def _grade_case(
    manifest_case: dict[str, Any],
    source_case: dict[str, Any] | None,
    required_trace_layers: list[str],
) -> dict[str, Any]:
    case_id = str(manifest_case.get("case_id") or "")
    blockers: list[str] = []
    if source_case is None:
        blockers.append("case_missing")
        source_case = {}
    present_layers = _present_layers(source_case, required_trace_layers)
    missing_layers = [layer for layer in required_trace_layers if layer not in present_layers]
    focus_layers = [str(item) for item in _list(manifest_case.get("expected_trace_focus"))]
    missing_focus_layers = [layer for layer in focus_layers if layer not in present_layers]
    blockers.extend(f"missing_layer:{layer}" for layer in missing_layers)
    blockers.extend(f"missing_focus_layer:{layer}" for layer in missing_focus_layers if layer not in missing_layers)
    for flag in _FORBIDDEN_TRUE_FLAGS:
        if source_case.get(flag) is True:
            blockers.append(f"forbidden_true_flag:{flag}")
    if source_case.get("expected_response_text") or source_case.get("golden_final_answer"):
        blockers.append("exact_response_template_present")
    return {
        "case_id": case_id,
        "status": "pass" if not blockers else "fail",
        "required_layers": required_trace_layers,
        "expected_focus_layers": focus_layers,
        "present_layers": present_layers,
        "missing_layers": missing_layers,
        "missing_focus_layers": missing_focus_layers,
        "blockers": blockers,
    }


def _source_cases_by_manifest_or_runtime_id(trace_artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for raw_case in _list(trace_artifact.get("cases")):
        case = _dict(raw_case)
        for key in ("manifest_case_id", "case_id"):
            case_id = str(case.get(key) or "")
            if case_id:
                indexed.setdefault(case_id, case)
    return indexed


def _present_layers(source_case: dict[str, Any], required_trace_layers: list[str]) -> list[str]:
    declared = {str(item) for item in _list(source_case.get("trace_layers_present")) if str(item)}
    if declared:
        return sorted(declared)
    return sorted(layer for layer in required_trace_layers if source_case.get(layer) is not None)


def _input_blockers(
    *,
    manifest: dict[str, Any],
    trace_artifact: dict[str, Any],
    case_grades: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if manifest.get("artifact_type") != "accurate_intake_mvp_live_diagnostic_case_manifest":
        blockers.append("manifest_artifact_type_invalid")
    if int(manifest.get("case_count") or 0) != len(_list(manifest.get("cases"))):
        blockers.append("manifest_case_count_mismatch")
    if not _list(trace_artifact.get("cases")):
        blockers.append("trace_artifact_cases_missing")
    for flag in _FORBIDDEN_TRUE_FLAGS:
        if trace_artifact.get(flag) is True:
            blockers.append(f"source_forbidden_true_flag:{flag}")
    if any(case["status"] != "pass" for case in case_grades):
        blockers.append("case_trace_grade_failed")
    return sorted(set(blockers))


def _read_json(path: Path) -> dict[str, Any]:
    return _dict(json.loads(path.read_text(encoding="utf-8")))


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Accurate Intake MVP manifest-driven case replay.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--trace-artifact", default=str(DEFAULT_TRACE_ARTIFACT_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args()
    output = write_live_case_replay(
        manifest_path=Path(args.manifest),
        trace_artifact_path=Path(args.trace_artifact),
        output_path=Path(args.output),
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
