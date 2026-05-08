from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_accurate_intake_rt14g_response_language_prompt_polish as module  # noqa: E402


def test_rt14g_prompt_polish_contract_passes() -> None:
    artifact = module.build_rt14g_response_language_prompt_polish_artifact()

    assert artifact["artifact_type"] == "accurate_intake_rt14g_response_language_prompt_polish"
    assert artifact["target_manager_runtime_gate"] == "rt14g_response_language_prompt_polish"
    assert artifact["status"] == "pass"
    assert artifact["pass_type"] == "contract"
    assert artifact["runtime_backed"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["summary"] == {
        "case_count": 6,
        "passed_case_count": 6,
            "system_prompt_version": "v10",
        "prompt_cache_safe_static_policy": True,
    }


def test_rt14g_prompt_policy_is_user_visible_not_trace_visible() -> None:
    artifact = module.build_rt14g_response_language_prompt_polish_artifact()
    by_id = {case["case_id"]: case for case in artifact["cases"]}

    assert by_id["user_language_policy"]["status"] == "pass"
    assert by_id["debug_surface_suppression_policy"]["status"] == "pass"
    assert by_id["macro_visibility_policy"]["status"] == "pass"
    assert by_id["blocking_followup_policy"]["status"] == "pass"
    assert by_id["no_plan_budget_honesty_policy"]["status"] == "pass"


def test_rt14g_prompt_policy_preserves_prompt_cache_static_prefix_boundary() -> None:
    artifact = module.build_rt14g_response_language_prompt_polish_artifact()
    by_id = {case["case_id"]: case for case in artifact["cases"]}

    observed = by_id["prompt_cache_static_prefix_policy"]["observed"]
    assert observed["dynamic_request_markers_absent"] is True
    assert observed["stable_policy_in_system_prompt"] is True


def test_rt14g_cli_writes_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "rt14g.json"

    rc = module.main(["--output", str(output_path)])

    assert rc == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
