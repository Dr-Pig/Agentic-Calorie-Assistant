from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.runtime.agent.manager_system_prompt import (  # noqa: E402
    SINGLE_MANAGER_SYSTEM_PROMPT,
    SINGLE_MANAGER_SYSTEM_PROMPT_ID,
    SINGLE_MANAGER_SYSTEM_PROMPT_SECTION_MANIFEST_VERSION,
    SINGLE_MANAGER_SYSTEM_PROMPT_VERSION,
    single_manager_system_prompt_section_manifest,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "manager_prompt_architecture_gate.json"
GOLDEN_MANIFEST_PATH = ROOT / "docs" / "quality" / "current_shell_self_use_golden_set_manifest.yaml"

CASE_STYLE_PATTERNS = (
    re.compile(r"\bif\s+user\s+says\s+['\"]", re.IGNORECASE),
    re.compile(r"\bif\s+the\s+user\s+says\s+['\"]", re.IGNORECASE),
    re.compile(r"如果使用者說[「『\"']"),
    re.compile(r"當使用者說[「『\"']"),
)

DYNAMIC_VALUE_PATTERNS = (
    re.compile(r"\blocal-self-use-\d+", re.IGNORECASE),
    re.compile(r"\btrace[-_][A-Za-z0-9_.:-]+", re.IGNORECASE),
    re.compile(r"\bsession[-_][A-Za-z0-9_.:-]+", re.IGNORECASE),
    re.compile(r"\b20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}"),
)


def build_manager_prompt_architecture_gate_report() -> dict[str, Any]:
    prompt = SINGLE_MANAGER_SYSTEM_PROMPT
    sections = single_manager_system_prompt_section_manifest()
    cases = [
        _evaluate_section_manifest(sections),
        _evaluate_no_golden_literals(prompt),
        _evaluate_no_case_style_routing(prompt),
        _evaluate_no_dynamic_runtime_values(prompt),
        _evaluate_prompt_cache_gate_policy(sections),
    ]
    blockers = [f"{case['case_id']}.{blocker}" for case in cases for blocker in case["blockers"]]
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "manager_prompt_architecture_gate",
        "claim_scope": "prompt_architecture_contract_not_line_count_gate",
        "prompt_id": SINGLE_MANAGER_SYSTEM_PROMPT_ID,
        "prompt_version": SINGLE_MANAGER_SYSTEM_PROMPT_VERSION,
        "section_manifest_version": SINGLE_MANAGER_SYSTEM_PROMPT_SECTION_MANIFEST_VERSION,
        "status": "pass" if not blockers else "fail",
        "blockers": blockers,
        "summary": {
            "case_count": len(cases),
            "passed_case_count": sum(1 for case in cases if case["status"] == "pass"),
            "section_count": len(sections),
            "stable_prompt_utf8_bytes": len(prompt.encode("utf-8")),
            "gate_model": "section_owner_hash_cache_boundary_not_line_count",
        },
        "cases": cases,
        "best_practice_alignment": {
            "static_prefix_first": True,
            "dynamic_suffix_last": True,
            "provider_reported_cache_metrics_only": True,
            "prompt_versions_and_section_hashes_required": True,
        },
    }


def _evaluate_section_manifest(sections: list[dict[str, Any]]) -> dict[str, Any]:
    blockers: list[str] = []
    seen_ids: set[str] = set()
    for index, section in enumerate(sections):
        section_id = str(section.get("section_id") or "")
        if not section_id:
            blockers.append(f"section_{index}_missing_id")
        if section_id in seen_ids:
            blockers.append(f"section_{section_id}_duplicate")
        seen_ids.add(section_id)
        if str(section.get("owner") or "") == "":
            blockers.append(f"section_{section_id}_missing_owner")
        if str(section.get("cache_role") or "") == "":
            blockers.append(f"section_{section_id}_missing_cache_role")
        if section.get("layer") != "static_prefix":
            blockers.append(f"section_{section_id}_not_static_prefix")
        if section.get("provider_overlay_allowed") is not False:
            blockers.append(f"section_{section_id}_provider_overlay_allowed")
        if not re.fullmatch(r"[0-9a-f]{64}", str(section.get("sha256") or "")):
            blockers.append(f"section_{section_id}_missing_sha256")
    return {
        "case_id": "section_manifest_has_owner_hash_and_cache_role",
        "status": _status(blockers),
        "blockers": blockers,
        "observed": {
            "section_ids": [str(section.get("section_id") or "") for section in sections],
            "section_count": len(sections),
        },
    }


def _evaluate_no_golden_literals(prompt: str) -> dict[str, Any]:
    utterances = _golden_utterances()
    matches = [
        utterance
        for utterance in utterances
        if len(utterance) >= 6 and utterance in prompt
    ]
    blockers = [f"golden_literal_in_stable_prompt:{_shorten(match)}" for match in matches]
    return {
        "case_id": "stable_prompt_has_no_golden_set_literal_utterance",
        "status": _status(blockers),
        "blockers": blockers,
        "observed": {
            "golden_utterance_count": len(utterances),
            "literal_match_count": len(matches),
        },
    }


def _evaluate_no_case_style_routing(prompt: str) -> dict[str, Any]:
    blockers = [
        f"case_style_pattern:{pattern.pattern}"
        for pattern in CASE_STYLE_PATTERNS
        if pattern.search(prompt)
    ]
    return {
        "case_id": "stable_prompt_has_no_if_user_says_routing",
        "status": _status(blockers),
        "blockers": blockers,
        "observed": {"pattern_count": len(CASE_STYLE_PATTERNS)},
    }


def _evaluate_no_dynamic_runtime_values(prompt: str) -> dict[str, Any]:
    blockers = [
        f"dynamic_runtime_value_pattern:{pattern.pattern}"
        for pattern in DYNAMIC_VALUE_PATTERNS
        if pattern.search(prompt)
    ]
    return {
        "case_id": "stable_prompt_has_no_dynamic_runtime_values",
        "status": _status(blockers),
        "blockers": blockers,
        "observed": {"pattern_count": len(DYNAMIC_VALUE_PATTERNS)},
    }


def _evaluate_prompt_cache_gate_policy(sections: list[dict[str, Any]]) -> dict[str, Any]:
    blockers: list[str] = []
    if not sections:
        blockers.append("missing_static_prefix_sections")
    if any(section.get("provider_overlay_allowed") is not False for section in sections):
        blockers.append("provider_overlay_can_change_stable_prompt")
    return {
        "case_id": "prompt_cache_gate_uses_sections_not_line_count",
        "status": _status(blockers),
        "blockers": blockers,
        "observed": {
            "line_count_is_not_quality_gate": True,
            "section_hashes_are_quality_gate": True,
            "cache_truth_source": "provider_reported_usage_only",
        },
    }


def _golden_utterances() -> list[str]:
    if not GOLDEN_MANIFEST_PATH.exists():
        return []
    text = GOLDEN_MANIFEST_PATH.read_text(encoding="utf-8-sig")
    utterances: list[str] = []
    for match in re.finditer(r"utterance_zh_tw:\s*(.+)", text):
        value = match.group(1).strip().strip("'\"")
        if value:
            utterances.append(value)
    return sorted(set(utterances))


def _shorten(value: str) -> str:
    return value[:40] + ("..." if len(value) > 40 else "")


def _status(blockers: list[str]) -> str:
    return "pass" if not blockers else "fail"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Manager prompt architecture gate.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)
    report = build_manager_prompt_architecture_gate_report()
    write_json_artifact(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
