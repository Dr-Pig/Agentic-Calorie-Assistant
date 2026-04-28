from __future__ import annotations

from scripts.repo_policy import (
    category_for_repo_path,
    effective_cap_for_repo_path,
    focus_modules,
    governance_tooling,
    load_active_code_policy,
    target_cap_for_repo_path,
)


def test_policy_classifies_rescue_proposal_and_builderspace_focus_modules() -> None:
    policy = load_active_code_policy()
    focus = focus_modules(policy)

    assert focus["app/rescue/application/proposal.py"]["classification"] == "later_wave_premature_active"
    assert focus["app/providers/builderspace_adapter.py"]["classification"] == "historical_workaround_residue"


def test_policy_assigns_expected_categories_and_caps() -> None:
    policy = load_active_code_policy()

    assert category_for_repo_path("app/providers/builderspace_adapter.py", policy) == "adapter_infrastructure"
    assert target_cap_for_repo_path("app/providers/builderspace_adapter.py", policy) == 350
    assert effective_cap_for_repo_path("app/providers/builderspace_adapter.py", policy) == 350

    assert category_for_repo_path("app/runtime/interface/base_routes.py", policy) == "boundary_surface"
    assert target_cap_for_repo_path("app/runtime/interface/base_routes.py", policy) == 200


def test_policy_tracks_autonomy_and_autorun_as_governance_tooling() -> None:
    policy = load_active_code_policy()
    tooling = governance_tooling(policy)

    assert "docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md" in tooling["docs"]
    assert "scripts/run_b1_cli_autorun.py" in tooling["scripts"]
    assert "scripts/run_codex_exec_with_prompt.py" in tooling["scripts"]
    assert "tests/test_b1_cli_autorun.py" in tooling["tests"]
    assert "tests/test_run_codex_exec_with_prompt.py" in tooling["tests"]
