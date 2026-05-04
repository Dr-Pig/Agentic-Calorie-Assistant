from __future__ import annotations

import json
from pathlib import Path

from scripts.merge_governance.build_merge_debt_matrix import (
    ALLOWED_VERDICTS,
    DEFAULT_CONFIG,
    build_matrix_from_prs,
    load_config,
    main,
    render_markdown,
)


def _check(name: str, conclusion: str = "SUCCESS", status: str = "COMPLETED") -> dict[str, str]:
    return {"name": name, "conclusion": conclusion, "status": status}


def _all_required_checks(conclusion: str = "SUCCESS") -> list[dict[str, str]]:
    return [_check(name, conclusion=conclusion) for name in DEFAULT_CONFIG["required_checks"]]


def _pr(
    *,
    number: int = 1,
    title: str = "Add BodyBudget slice",
    head: str = "codex/body-budget-slice",
    base: str = "main",
    body: str = "track: BodyBudgetCalibration\nruntime_truth_changed: false\nmanager_context_packet_changed: false\nmutation_changed: false\nproduct_readiness_claimed: false\n",
    additions: int = 10,
    deletions: int = 0,
    checks: list[dict[str, str]] | None = None,
    files: list[dict[str, object]] | None = None,
    head_contains_main: bool | None = True,
    contract_findings: list[str] | None = None,
) -> dict[str, object]:
    return {
        "number": number,
        "title": title,
        "headRefName": head,
        "baseRefName": base,
        "isDraft": True,
        "mergeStateStatus": "CLEAN",
        "statusCheckRollup": checks if checks is not None else _all_required_checks(),
        "additions": additions,
        "deletions": deletions,
        "changedFiles": len(files or []),
        "files": files or [{"path": "app/body/application/example.py", "additions": additions, "deletions": deletions}],
        "body": body,
        "updatedAt": "2026-05-04T00:00:00Z",
        "url": f"https://example.test/pull/{number}",
        "head_contains_main": head_contains_main,
        "contract_findings": contract_findings or [],
    }


def test_all_green_pr_with_stale_contract_requires_rebase() -> None:
    matrix = build_matrix_from_prs(
        [
            _pr(
                title="Add proactive no-send shadow evaluator",
                head="codex/proactive-no-send-shadow",
                body="track: ProactiveShadow\nruntime_truth_changed: false\nmanager_context_packet_changed: false\nmutation_changed: false\nproduct_readiness_claimed: false\n",
                additions=100,
                files=[{"path": "app/runtime/application/proactive_no_send_shadow_evaluator.py", "additions": 100}],
                contract_findings=["legacy_calibration_unmounted_route_gate"],
            )
        ],
        DEFAULT_CONFIG,
    )

    entry = matrix["entries"][0]
    assert entry["ci_status"] == "pass"
    assert entry["base_drift_status"] == "stale_contract_detected"
    assert entry["recommended_verdict"] == "rebase_required"


def test_future_shadow_large_inactive_implementation_can_be_dormant_candidate() -> None:
    matrix = build_matrix_from_prs(
        [
            _pr(
                title="Add long-term context shadow lab",
                head="codex/long-term-context-shadow-lab",
                body="track: LongTermContextLab\nruntime_truth_changed: false\nmanager_context_packet_changed: false\nmutation_changed: false\nproduct_readiness_claimed: false\n",
                additions=12042,
                files=[{"path": "app/memory/application/long_term_context_shadow_lab.py", "additions": 12042}],
            )
        ],
        DEFAULT_CONFIG,
    )

    entry = matrix["entries"][0]
    assert entry["mainline_status"] == "future_shadow"
    assert entry["fat_file_status"] == "warning"
    assert entry["runtime_activation_status"] == "inactive"
    assert entry["recommended_verdict"] == "dormant_shadow_candidate"


def test_future_shadow_without_track_report_is_fix_gate() -> None:
    entry = build_matrix_from_prs(
        [
            _pr(
                title="Add long-term context shadow lab",
                head="codex/long-term-context-shadow-lab",
                body="track: LongTermContextLab\nruntime_truth_changed: false\n",
                additions=100,
                files=[{"path": "app/memory/application/long_term_context_shadow_lab.py", "additions": 100}],
            )
        ],
        DEFAULT_CONFIG,
    )["entries"][0]

    assert entry["recommended_verdict"] == "fix_gate"
    assert "missing_track_report_key:manager_context_packet_changed" in entry["blocking_reasons"]


def test_future_shadow_guard_only_pr_is_extract_only() -> None:
    matrix = build_matrix_from_prs(
        [
            _pr(
                title="Add Recommendation Shadow manager-selection guard",
                head="codex/recommendation-shadow-manager-selection-boundary",
                body="track: RecommendationShadow\nruntime_truth_changed: false\nmanager_context_packet_changed: false\nmutation_changed: false\nproduct_readiness_claimed: false\n",
                additions=80,
                files=[
                    {"path": "tests/test_recommendation_shadow_artifact_gate.py", "additions": 60},
                    {"path": "app/recommendation/application/shadow_artifact_gate.py", "additions": 20},
                ],
            )
        ],
        DEFAULT_CONFIG,
    )

    assert matrix["entries"][0]["recommended_verdict"] == "extract_only"


def test_plce_track_alias_is_mvp_mainline() -> None:
    entry = build_matrix_from_prs([_pr(body=_pr()["body"].replace("BodyBudgetCalibration", "PL_CE"))], DEFAULT_CONFIG)[
        "entries"
    ][0]

    assert entry["track"] == "PLCE"
    assert entry["mainline_status"] == "mvp_mainline"
    assert entry["recommended_verdict"] == "merge_candidate"


def test_runtime_contract_failure_is_fix_gate() -> None:
    checks = _all_required_checks()
    checks.append(_check("runtime-contract-tests", conclusion="FAILURE"))
    matrix = build_matrix_from_prs([_pr(checks=checks)], DEFAULT_CONFIG)

    entry = matrix["entries"][0]
    assert entry["ci_status"] == "fail"
    assert entry["recommended_verdict"] == "fix_gate"


def test_required_checks_accept_success_skipped_neutral_and_reject_missing_pending_cancelled() -> None:
    assert DEFAULT_CONFIG["required_checks"] == [
        "repo-hygiene-and-architecture",
        "pre-edd-readiness",
        "runtime-contract-tests",
        "wave1-phase-a-contracts",
        "wave1-phase-b-contracts",
    ]
    assert DEFAULT_CONFIG["advisory_checks"] == ["phase-c-environment-gate", "accurate-intake-mvp-gate"]

    skipped_checks = _all_required_checks()
    skipped_checks[0] = _check(DEFAULT_CONFIG["required_checks"][0], conclusion="SKIPPED")
    skipped_checks[1] = _check(DEFAULT_CONFIG["required_checks"][1], conclusion="NEUTRAL")
    assert build_matrix_from_prs([_pr(checks=skipped_checks)], DEFAULT_CONFIG)["entries"][0]["ci_status"] == "pass"

    missing = _all_required_checks()
    missing = [check for check in missing if check["name"] != "wave1-phase-b-contracts"]
    missing_entry = build_matrix_from_prs([_pr(checks=missing)], DEFAULT_CONFIG)["entries"][0]
    assert missing_entry["ci_status"] == "incomplete"
    assert missing_entry["recommended_verdict"] == "fix_gate"

    pending = _all_required_checks()
    pending[0] = _check(DEFAULT_CONFIG["required_checks"][0], conclusion="", status="IN_PROGRESS")
    pending_entry = build_matrix_from_prs([_pr(checks=pending)], DEFAULT_CONFIG)["entries"][0]
    assert pending_entry["ci_status"] == "pending"
    assert pending_entry["recommended_verdict"] == "fix_gate"

    cancelled = _all_required_checks()
    cancelled[0] = _check(DEFAULT_CONFIG["required_checks"][0], conclusion="CANCELLED")
    cancelled_entry = build_matrix_from_prs([_pr(checks=cancelled)], DEFAULT_CONFIG)["entries"][0]
    assert cancelled_entry["ci_status"] == "fail"
    assert cancelled_entry["recommended_verdict"] == "fix_gate"


def test_advisory_checks_are_recorded_but_not_required_for_ci_status() -> None:
    checks = _all_required_checks()
    checks.append(_check("phase-c-environment-gate", conclusion="FAILURE"))

    entry = build_matrix_from_prs([_pr(checks=checks)], DEFAULT_CONFIG)["entries"][0]

    assert entry["ci_status"] == "pass"
    assert entry["advisory_check_status"] == "fail"
    assert "failed_advisory_check:phase-c-environment-gate" in entry["blocking_reasons"]


def test_future_shadow_forbidden_runtime_flags_stop_merge_path() -> None:
    body = "\n".join(
        [
            "track: LongTermContextLab",
            "runtime_truth_changed: true",
            "manager_context_packet_changed: false",
            "mutation_changed: false",
            "product_readiness_claimed: false",
        ]
    )

    entry = build_matrix_from_prs(
        [
            _pr(
                title="Add long-term memory runtime hook",
                head="codex/long-term-context-shadow-lab",
                body=body,
                additions=40,
                files=[{"path": "app/memory/application/runtime_hook.py", "additions": 40}],
            )
        ],
        DEFAULT_CONFIG,
    )["entries"][0]

    assert entry["runtime_activation_status"] == "active"
    assert entry["recommended_verdict"] == "stop"
    assert "forbidden_future_runtime_effect:runtime_truth_changed" in entry["blocking_reasons"]


def test_head_branch_not_containing_current_main_requires_rebase() -> None:
    entry = build_matrix_from_prs([_pr(head_contains_main=False)], DEFAULT_CONFIG)["entries"][0]

    assert entry["base_drift_status"] == "stale_to_main"
    assert entry["recommended_verdict"] == "rebase_required"


def test_unknown_head_freshness_requires_rebase() -> None:
    entry = build_matrix_from_prs([_pr(head_contains_main=None)], DEFAULT_CONFIG)["entries"][0]

    assert entry["base_drift_status"] == "stale_to_main"
    assert entry["recommended_verdict"] == "rebase_required"
    assert "head_branch_freshness_unknown" in entry["blocking_reasons"]


def test_stacked_pr_roles_are_deterministic() -> None:
    root = _pr(number=1, head="codex/root", base="main")
    middle = _pr(number=2, head="codex/middle", base="codex/root")
    leaf = _pr(number=3, head="codex/leaf", base="codex/middle")

    entries = build_matrix_from_prs([leaf, root, middle], DEFAULT_CONFIG)["entries"]
    roles = {entry["head_branch"]: entry["stack_role"] for entry in entries}

    assert roles == {"codex/root": "root", "codex/middle": "middle", "codex/leaf": "leaf"}


def test_stack_depth_over_repo_policy_forces_fix_gate() -> None:
    root = _pr(number=1, head="codex/root", base="main")
    middle = _pr(number=2, head="codex/middle", base="codex/root")
    leaf = _pr(number=3, head="codex/leaf", base="codex/middle")

    leaf_entry = build_matrix_from_prs([root, middle, leaf], DEFAULT_CONFIG)["entries"][0]

    assert leaf_entry["head_branch"] == "codex/leaf"
    assert leaf_entry["stack_depth"] == 3
    assert leaf_entry["recommended_verdict"] == "fix_gate"
    assert "stack_depth_over_policy:3>2" in leaf_entry["blocking_reasons"]


def test_mvp_mainline_current_green_pr_is_merge_candidate() -> None:
    matrix = build_matrix_from_prs([_pr(additions=120)], DEFAULT_CONFIG)

    entry = matrix["entries"][0]
    assert entry["mainline_status"] == "mvp_mainline"
    assert entry["base_drift_status"] == "current"
    assert entry["recommended_verdict"] == "merge_candidate"


def test_rescue_fixture_under_active_app_forces_fix_gate() -> None:
    matrix = build_matrix_from_prs(
        [
            _pr(
                title="Add rescue shadow scenario fixtures",
                head="codex/rescue-rs6-scenario-fixtures",
                body="track: RescueShadow\nruntime_truth_changed: false\nmanager_context_packet_changed: false\nmutation_changed: false\nproduct_readiness_claimed: false\n",
                additions=524,
                files=[{"path": "app/rescue/fixtures/shadow_scenarios.py", "additions": 263}],
            )
        ],
        DEFAULT_CONFIG,
    )

    entry = matrix["entries"][0]
    assert entry["boundary_status"] == "fail"
    assert entry["recommended_verdict"] == "fix_gate"


def test_windows_style_paths_are_normalized_before_active_surface_checks() -> None:
    entry = build_matrix_from_prs(
        [
            _pr(
                title="Add proactive runtime route",
                head="codex/proactive-no-send-shadow",
                body="track: ProactiveShadow\nruntime_truth_changed: false\nmanager_context_packet_changed: false\nmutation_changed: false\nproduct_readiness_claimed: false\n",
                additions=20,
                files=[{"path": "app\\routes.py", "additions": 20}],
            )
        ],
        DEFAULT_CONFIG,
    )["entries"][0]

    assert entry["boundary_status"] == "fail"
    assert entry["runtime_activation_status"] == "active"
    assert entry["recommended_verdict"] == "stop"


def test_missing_track_report_stops_unknown_product_pr() -> None:
    matrix = build_matrix_from_prs(
        [
            _pr(
                title="Add broad product behavior",
                head="codex/new-agent-feature",
                body="summary only",
                files=[{"path": "app/runtime/agent/new_feature.py", "additions": 50}],
            )
        ],
        DEFAULT_CONFIG,
    )

    entry = matrix["entries"][0]
    assert entry["boundary_status"] == "needs_review"
    assert entry["recommended_verdict"] == "stop"


def test_proactive_title_wins_over_memory_words_in_body() -> None:
    entry = build_matrix_from_prs(
        [
            _pr(
                title="Add proactive no-send shadow evaluator",
                head="codex/proactive-no-send-shadow",
                body="Uses memory context only as fixture text.",
                additions=1886,
                files=[{"path": "app/runtime/application/proactive_no_send_shadow_evaluator.py", "additions": 1886}],
            )
        ],
        DEFAULT_CONFIG,
    )["entries"][0]

    assert entry["track"] == "ProactiveShadow"


def test_dependency_bumps_do_not_need_product_track_report() -> None:
    entry = build_matrix_from_prs(
        [
            _pr(
                title="Bump actions/upload-artifact from 4 to 7",
                head="dependabot/github_actions/actions/upload-artifact-7",
                body="",
                files=[{"path": ".github/workflows/ci.yml", "additions": 4, "deletions": 4}],
            )
        ],
        DEFAULT_CONFIG,
    )["entries"][0]

    assert entry["mainline_status"] == "dependency_bump"
    assert entry["boundary_status"] == "pass"
    assert not any(reason.startswith("missing_track_report_key") for reason in entry["blocking_reasons"])


def test_recommendation_top_pick_mentions_are_allowed_when_manager_selection_is_required() -> None:
    entry = build_matrix_from_prs(
        [
            _pr(
                title="Fix Recommendation Shadow manager selection boundary",
                head="codex/recommendation-shadow-manager-selection-boundary",
                body="Removes top_pick and records manager selection required.",
                additions=100,
                files=[{"path": "app/recommendation/application/shadow_artifact_gate.py", "additions": 100}],
            )
        ],
        DEFAULT_CONFIG,
    )["entries"][0]

    assert entry["deterministic_boundary_status"] == "pass"


def test_matrix_cli_writes_deterministic_json_and_markdown(tmp_path: Path) -> None:
    input_path = tmp_path / "prs.json"
    json_out = tmp_path / "merge_debt_matrix.json"
    md_out = tmp_path / "merge_debt_matrix.md"
    input_path.write_text(json.dumps([_pr(number=7)], ensure_ascii=False), encoding="utf-8")

    assert main(["--input-json", str(input_path), "--json-out", str(json_out), "--md-out", str(md_out)]) == 0

    report = json.loads(json_out.read_text(encoding="utf-8"))
    assert report["entries"][0]["pr_number"] == 7
    assert report["entries"][0]["recommended_verdict"] == "merge_candidate"
    assert set(report["entries"][0]) >= {
        "pr_number",
        "track",
        "base_branch",
        "head_branch",
        "stack_role",
        "mainline_status",
        "ci_status",
        "base_drift_status",
        "boundary_status",
        "deterministic_boundary_status",
        "advisory_check_status",
        "runtime_activation_status",
        "fat_file_status",
        "recommended_verdict",
        "blocking_reasons",
        "safe_next_action",
    }
    rendered = md_out.read_text(encoding="utf-8")
    assert "| # | Track | Status | Verdict | Blocking reasons |" in rendered
    assert render_markdown(report) == rendered


def test_matrix_cli_reports_missing_input_json_without_traceback(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"

    assert main(["--input-json", str(missing)]) == 2


def test_matrix_entries_are_sorted_and_verdicts_are_schema_guarded() -> None:
    matrix = build_matrix_from_prs([_pr(number=1), _pr(number=3), _pr(number=2)], DEFAULT_CONFIG)

    assert [entry["pr_number"] for entry in matrix["entries"]] == [3, 2, 1]
    assert {entry["recommended_verdict"] for entry in matrix["entries"]} <= ALLOWED_VERDICTS
    assert ALLOWED_VERDICTS == {
        "merge_candidate",
        "dormant_shadow_candidate",
        "extract_only",
        "rebase_required",
        "fix_gate",
        "hold_as_shadow",
        "stop",
    }


def test_input_json_path_does_not_consult_local_git_state(tmp_path: Path, monkeypatch) -> None:
    def fail_if_called(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("local git state must not be consulted for fixture input")

    input_path = tmp_path / "prs.json"
    json_out = tmp_path / "matrix.json"
    md_out = tmp_path / "matrix.md"
    input_path.write_text(json.dumps([_pr(number=11)], ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr("scripts.merge_governance.build_merge_debt_matrix.subprocess.run", fail_if_called)

    assert main(["--input-json", str(input_path), "--json-out", str(json_out), "--md-out", str(md_out)]) == 0
    assert json.loads(json_out.read_text(encoding="utf-8"))["entries"][0]["pr_number"] == 11


def test_config_loader_parses_repo_yaml_subset(tmp_path: Path) -> None:
    config_path = tmp_path / ".merge-governance.yml"
    config_path.write_text(
        "\n".join(
            [
                "main_branch: main",
                "mvp_mainline_tracks:",
                "  - AccurateIntake",
                "future_shadow_tracks:",
                "  - ProactiveShadow",
                "required_checks:",
                "  - runtime-contract-tests",
                "advisory_checks:",
                "  - phase-c-environment-gate",
                "forbidden_future_runtime_effects:",
                "  - proactive_sent: true",
                "size_budget:",
                "  mvp_mainline_max_additions: 10",
                "  future_shadow_merge_max_additions: 5",
                "  max_stack_depth: 1",
                "  max_branch_age_days_without_realign: 2",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config["main_branch"] == "main"
    assert config["future_shadow_tracks"] == ["ProactiveShadow"]
    assert config["advisory_checks"] == ["phase-c-environment-gate"]
    assert config["forbidden_future_runtime_effects"] == [{"proactive_sent": True}]
    assert config["size_budget"]["future_shadow_merge_max_additions"] == 5
