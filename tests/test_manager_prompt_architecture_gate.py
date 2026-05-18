from __future__ import annotations

from scripts.check_manager_prompt_architecture_gate import build_manager_prompt_architecture_gate_report


def test_manager_prompt_architecture_gate_passes() -> None:
    report = build_manager_prompt_architecture_gate_report()

    assert report["status"] == "pass"
    assert report["claim_scope"] == "prompt_architecture_contract_not_line_count_gate"
    assert report["summary"]["gate_model"] == "section_owner_hash_cache_boundary_not_line_count"
    assert "app/runtime/agent/manager_user_facing_reply_prompt.py" in report["summary"]["prompt_source_files"]
    assert report["best_practice_alignment"]["section_source_of_truth_required"] is True


def test_manager_prompt_architecture_gate_blocks_case_style_prompt_patches() -> None:
    report = build_manager_prompt_architecture_gate_report()
    cases = {case["case_id"]: case for case in report["cases"]}

    assert cases["stable_prompt_has_no_golden_set_literal_utterance"]["status"] == "pass"
    assert cases["stable_prompt_has_no_if_user_says_routing"]["status"] == "pass"
    assert cases["stable_prompt_has_no_dynamic_runtime_values"]["status"] == "pass"


def test_manager_prompt_architecture_gate_uses_sections_not_line_count() -> None:
    report = build_manager_prompt_architecture_gate_report()
    cases = {case["case_id"]: case for case in report["cases"]}
    section_case = cases["section_manifest_has_owner_source_hash_and_cache_role"]
    prompt_cache_case = cases["prompt_cache_gate_uses_sections_not_line_count"]

    assert section_case["status"] == "pass"
    assert "source_of_truth_refs" in section_case["observed"]["required_fields"]
    assert "allowed_change_type" in section_case["observed"]["required_fields"]
    assert prompt_cache_case["status"] == "pass"
    assert prompt_cache_case["observed"]["line_count_is_not_quality_gate"] is True
    assert prompt_cache_case["observed"]["section_hashes_are_quality_gate"] is True
    assert prompt_cache_case["observed"]["cache_truth_source"] == "provider_reported_usage_only"
