from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACK_SPECS = (
    {
        "path": ROOT / "docs" / "quality" / "benchmarks" / "intake" / "intake_executable_action_pack_v1.json",
        "source_pack_path": ROOT / "docs" / "quality" / "benchmarks" / "intake" / "intake_official_canonical_pack_v1.json",
        "workflow_family": "intake",
    },
    {
        "path": ROOT / "docs" / "quality" / "benchmarks" / "rescue" / "rescue_executable_action_pack_v1.json",
        "source_pack_path": ROOT / "docs" / "quality" / "benchmarks" / "rescue" / "rescue_official_canonical_pack_v1.json",
        "workflow_family": "rescue",
    },
)

REQUIRED_OUTCOME_FIELDS = (
    "expected_target_object_type",
    "expected_target_workflow_family",
    "expected_disposition",
    "expected_workflow_effect",
)
ALLOWED_DERIVATION_STATUSES = {
    "contract_ready",
    "blocked_pending_runtime_action_choice",
}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing executable action artifact: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"artifact must be a JSON object: {path}")
    return payload


def _source_case_map(source_payload: dict[str, Any], *, source_path: Path) -> dict[str, dict[str, Any]]:
    cases = source_payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{source_path} must contain a non-empty cases list")
    mapping: dict[str, dict[str, Any]] = {}
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError(f"{source_path} contains a non-object case entry")
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"{source_path} contains a case missing case_id")
        mapping[case_id] = case
    return mapping


def _validate_pack(pack_payload: dict[str, Any], *, pack_path: Path, source_cases: dict[str, dict[str, Any]], workflow_family: str) -> None:
    if pack_payload.get("pack_mode") != "executable_action":
        raise ValueError(f"{pack_path} must use pack_mode=executable_action")
    if pack_payload.get("authority_level") != "derived_from_official_canonical":
        raise ValueError(f"{pack_path} must use authority_level=derived_from_official_canonical")
    runner_input_contract = pack_payload.get("runner_input_contract")
    if not isinstance(runner_input_contract, dict):
        raise ValueError(f"{pack_path} missing runner_input_contract object")
    if runner_input_contract.get("workflow_family") != workflow_family:
        raise ValueError(f"{pack_path} runner_input_contract.workflow_family must be {workflow_family}")

    cases = pack_payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{pack_path} must contain a non-empty cases list")

    seen_case_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError(f"{pack_path} contains a non-object case entry")
        case_id = case.get("executable_case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"{pack_path} contains a case missing executable_case_id")
        if case_id in seen_case_ids:
            raise ValueError(f"{pack_path} contains duplicate executable_case_id: {case_id}")
        seen_case_ids.add(case_id)

        source_case_id = case.get("source_official_case_id")
        if not isinstance(source_case_id, str) or source_case_id not in source_cases:
            raise ValueError(f"{pack_path} case {case_id} points to unknown source_official_case_id")
        source_case = source_cases[source_case_id]

        derivation_status = case.get("derivation_status")
        if derivation_status not in ALLOWED_DERIVATION_STATUSES:
            raise ValueError(f"{pack_path} case {case_id} has unsupported derivation_status: {derivation_status}")
        if derivation_status == "blocked_pending_runtime_action_choice":
            block_reason = case.get("block_reason")
            if not isinstance(block_reason, str) or not block_reason:
                raise ValueError(f"{pack_path} case {case_id} blocked without block_reason")

        if not isinstance(case.get("suite_id"), str) or not case.get("suite_id"):
            raise ValueError(f"{pack_path} case {case_id} missing suite_id")
        if case["suite_id"] != source_case.get("suite_id"):
            raise ValueError(f"{pack_path} case {case_id} suite_id must match source official case")

        input_text_source = case.get("input_text_source")
        if input_text_source is not None:
            if not isinstance(input_text_source, dict):
                raise ValueError(f"{pack_path} case {case_id} input_text_source must be an object")
            if input_text_source.get("source_official_case_id") != source_case_id:
                raise ValueError(f"{pack_path} case {case_id} input_text_source must point back to source official case")
            if input_text_source.get("source_field") != "utterance":
                raise ValueError(f"{pack_path} case {case_id} input_text_source.source_field must be utterance")

        if not isinstance(case.get("state_seed", case.get("proposal_seed")), dict):
            raise ValueError(f"{pack_path} case {case_id} must include state_seed or proposal_seed")
        if not isinstance(case.get("execution_mode"), str) or not case.get("execution_mode"):
            raise ValueError(f"{pack_path} case {case_id} missing execution_mode")

        outcome = case.get("expected_runtime_outcome")
        if not isinstance(outcome, dict):
            raise ValueError(f"{pack_path} case {case_id} missing expected_runtime_outcome")
        for field in REQUIRED_OUTCOME_FIELDS:
            if outcome.get(field) != source_case.get(field):
                raise ValueError(
                    f"{pack_path} case {case_id} outcome field {field} must match source official case "
                    f"({outcome.get(field)!r} vs {source_case.get(field)!r})"
                )


def main() -> int:
    try:
        for spec in PACK_SPECS:
            pack_payload = _load_json(spec["path"])
            source_payload = _load_json(spec["source_pack_path"])
            source_cases = _source_case_map(source_payload, source_path=spec["source_pack_path"])
            _validate_pack(
                pack_payload,
                pack_path=spec["path"],
                source_cases=source_cases,
                workflow_family=str(spec["workflow_family"]),
            )
    except ValueError as exc:
        print(f"[FAIL] executable action pack contract check failed: {exc}", file=sys.stderr)
        return 1

    print("[OK] executable action pack contract check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
