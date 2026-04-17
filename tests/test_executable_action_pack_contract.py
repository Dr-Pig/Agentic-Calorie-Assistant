from __future__ import annotations

import json
from pathlib import Path

from scripts import check_executable_action_pack_contract


ROOT = Path(__file__).resolve().parents[1]
INTAKE_EXECUTABLE_PACK_PATH = (
    ROOT
    / "docs"
    / "quality"
    / "benchmarks"
    / "intake"
    / "intake_executable_action_pack_v1.json"
)
RESCUE_EXECUTABLE_PACK_PATH = (
    ROOT
    / "docs"
    / "quality"
    / "benchmarks"
    / "rescue"
    / "rescue_executable_action_pack_v1.json"
)


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def test_executable_action_packs_have_expected_top_level_shape() -> None:
    for path, pack_id in (
        (INTAKE_EXECUTABLE_PACK_PATH, "intake_executable_action_pack_v1"),
        (RESCUE_EXECUTABLE_PACK_PATH, "rescue_executable_action_pack_v1"),
    ):
        payload = _load_json(path)
        assert payload["pack_id"] == pack_id
        assert payload["pack_mode"] == "executable_action"
        assert payload["authority_level"] == "derived_from_official_canonical"
        assert payload["derived_from_pack_id"].endswith("_official_canonical_pack_v1")
        assert "must not be treated as a separate source of product truth" in payload["non_authority_note"]
        assert payload["cases"]


def test_executable_action_pack_contract_check_passes() -> None:
    assert check_executable_action_pack_contract.main() == 0


def test_rescue_adjust_executable_case_uses_adjust_direction() -> None:
    payload = _load_json(RESCUE_EXECUTABLE_PACK_PATH)
    adjust_case = next(case for case in payload["cases"] if case["suite_id"] == "rescue_adjust_action_golden_v1")
    assert adjust_case["expected_runtime_outcome"]["expected_disposition"] == "adjust"
    assert adjust_case["expected_runtime_outcome"]["expected_adjust_direction"] == "longer"
    assert adjust_case["runtime_action"]["action"] == "extend_rescue_plan"
