from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.current_shell_golden_set_trace_adapter import grade_golden_case_trace  # noqa: E402


DEFAULT_MANIFEST_PATH = ROOT / "docs" / "quality" / "current_shell_self_use_golden_set_manifest.yaml"
DEFAULT_TRACE_ARTIFACT_PATH = ROOT / "artifacts" / "current_shell_self_use_golden_set_trace_artifact.json"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "current_shell_self_use_golden_set_replay.json"

_FORBIDDEN_SOURCE_TRUE_FLAGS = (
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
    "whole_product_mvp_claimed",
    "pre_manager_websearch_routing_used",
    "websearch_candidate_promoted_to_truth",
    "websearch_candidate_committed",
    "wrong_brand_exact_promotion",
    "websearch_call_when_fooddb_anchor_available",
    "visible_macro_from_candidate_only",
)


def build_golden_set_replay(
    *,
    manifest: dict[str, Any],
    trace_artifact: dict[str, Any],
) -> dict[str, Any]:
    core_cases = _core_cases(manifest)
    websearch_extension_cases = _websearch_extension_cases(manifest)
    manifest_cases = [*core_cases, *websearch_extension_cases]
    source_cases = _source_cases_by_id(trace_artifact)
    case_grades = [
        _grade_case(manifest_case, source_cases.get(str(manifest_case.get("case_id") or "")), manifest)
        for manifest_case in manifest_cases
    ]
    input_blockers = _input_blockers(
        manifest=manifest,
        trace_artifact=trace_artifact,
        case_grades=case_grades,
    )
    failed_cases = [case for case in case_grades if case.get("status") != "pass"]
    missing_cases = [case for case in case_grades if "case_missing" in _list(case.get("blockers"))]

    return _json_safe(
        {
            "artifact_type": "current_shell_self_use_golden_set_replay",
            "artifact_schema_version": "1.0",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "claim_scope": "offline_runtime_trace_replay",
            "source_artifact_type": trace_artifact.get("artifact_type"),
            "live_invoked_by_replay": False,
            "readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "whole_product_mvp_claimed": False,
            "runner_inferred_semantics": False,
            "semantic_keyword_oracle_used": False,
            "summary": {
                "core_case_count": len(core_cases),
                "websearch_extension_case_count": len(websearch_extension_cases),
                "total_closeout_case_count": len(manifest_cases),
                "manifest_case_count": len(manifest_cases),
                "source_case_count": len(source_cases),
                "graded_case_count": len(case_grades),
                "failed_case_count": len(failed_cases),
                "missing_case_count": len(missing_cases),
                "strict_golden_set_replay_passed": not input_blockers and not failed_cases,
            },
            "input_integrity": {"passed": not input_blockers, "blockers": input_blockers},
            "cases": case_grades,
        }
    )


def write_golden_set_replay(
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    trace_artifact_path: Path = DEFAULT_TRACE_ARTIFACT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    manifest = _read_yaml(manifest_path)
    trace_artifact = _read_json(trace_artifact_path)
    replay = build_golden_set_replay(manifest=manifest, trace_artifact=trace_artifact)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(replay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def _grade_case(
    manifest_case: dict[str, Any],
    source_case: dict[str, Any] | None,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    case_id = str(manifest_case.get("case_id") or "")
    if source_case is None:
        return {
            "case_id": case_id,
            "status": "blocked",
            "blockers": ["case_missing"],
            "warnings": [],
            "deterministic_grader_owns_semantics": False,
        }
    return grade_golden_case_trace(case_id, source_case, manifest=manifest)


def _source_cases_by_id(trace_artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for raw_case in _list(trace_artifact.get("cases")):
        case = _dict(raw_case)
        for key in ("manifest_case_id", "case_id"):
            case_id = str(case.get(key) or "")
            if case_id:
                indexed.setdefault(case_id, case)
    return indexed


def _input_blockers(
    *,
    manifest: dict[str, Any],
    trace_artifact: dict[str, Any],
    case_grades: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if manifest.get("artifact_type") != "current_shell_self_use_golden_set_manifest":
        blockers.append("manifest.artifact_type_invalid")
    if int(manifest.get("case_count") or 0) != len(_list(manifest.get("cases"))):
        blockers.append("manifest.case_count_mismatch")
    websearch_extension = _dict(manifest.get("websearch_extension"))
    if websearch_extension and int(websearch_extension.get("case_count") or 0) != len(
        _list(websearch_extension.get("cases"))
    ):
        blockers.append("manifest.websearch_extension.case_count_mismatch")
    if not _list(trace_artifact.get("cases")):
        blockers.append("source.cases_missing")
    for flag in _FORBIDDEN_SOURCE_TRUE_FLAGS:
        if trace_artifact.get(flag) is True:
            blockers.append(f"source.{flag}_not_allowed")
    if any(case.get("deterministic_grader_owns_semantics") is True for case in case_grades):
        blockers.append("case_grader_semantic_ownership_violation")
    return sorted(set(blockers))


def _manifest_cases(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [*_core_cases(manifest), *_websearch_extension_cases(manifest)]


def _core_cases(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [_dict(item) for item in _list(manifest.get("cases"))]


def _websearch_extension_cases(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    websearch_extension = _dict(manifest.get("websearch_extension"))
    return [_dict(item) for item in _list(websearch_extension.get("cases"))]


def _read_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    return _dict(loaded)


def _read_json(path: Path) -> dict[str, Any]:
    return _dict(json.loads(path.read_text(encoding="utf-8")))


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Current Shell self-use Golden Set replay artifact.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--trace-artifact", default=str(DEFAULT_TRACE_ARTIFACT_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args()
    output = write_golden_set_replay(
        manifest_path=Path(args.manifest),
        trace_artifact_path=Path(args.trace_artifact),
        output_path=Path(args.output),
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
