from __future__ import annotations

from scripts.repo_policy import (
    category_for_repo_path,
    effective_cap_for_repo_path,
    focus_modules,
    governance_tooling,
    iter_active_python_files,
    load_active_code_policy,
    target_cap_for_repo_path,
)


def test_policy_classifies_active_focus_modules_without_archive_surfaces() -> None:
    policy = load_active_code_policy()
    focus = focus_modules(policy)

    assert focus["app/providers/builderspace_adapter.py"]["classification"] == "historical_workaround_residue"
    archived_prefix = "app/" + "archive/"
    assert not any(path.startswith(archived_prefix) for path in focus)


def test_policy_assigns_expected_categories_and_caps() -> None:
    policy = load_active_code_policy()

    assert category_for_repo_path("app/providers/builderspace_adapter.py", policy) == "adapter_infrastructure"
    assert target_cap_for_repo_path("app/providers/builderspace_adapter.py", policy) == 350
    assert effective_cap_for_repo_path("app/providers/builderspace_adapter.py", policy) == 350

    assert category_for_repo_path("app/runtime/interface/base_routes.py", policy) == "boundary_surface"
    assert target_cap_for_repo_path("app/runtime/interface/base_routes.py", policy) == 200


def test_policy_tracks_current_governance_tooling_without_autonomy_loop() -> None:
    policy = load_active_code_policy()
    tooling = governance_tooling(policy)

    assert "docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md" in tooling["docs"]
    assert "scripts/verify_wave1_phase_b_tool_loop_readiness.py" in tooling["scripts"]
    assert "tests/test_wave1_phase_b_tool_loop_readiness.py" in tooling["tests"]
    assert not any("autonomy-" in path for paths in tooling.values() for path in paths)


def test_policy_excludes_archive_app_family_from_active_inventory() -> None:
    policy = load_active_code_policy()
    active_paths = {path.as_posix().replace("\\", "/") for path in iter_active_python_files(policy)}

    archived_prefix = "app/" + "archive/"
    assert not any(path.startswith(archived_prefix) for path in active_paths)
