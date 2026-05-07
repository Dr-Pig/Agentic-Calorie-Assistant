from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import scripts.merge_governance.build_merge_governance_advisory as merge_debt_matrix_module
from scripts.merge_governance.build_merge_governance_advisory import (
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
    title: str = "Add CurrentShell slice",
    head: str = "codex/current-shell-slice",
    base: str = "main",
    body: str = (
        "track: CurrentShell\n"
        "runtime_truth_changed: false\n"
        "manager_context_packet_changed: false\n"
        "mutation_changed: false\n"
        "product_readiness_claimed: false\n"
    ),
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
        "files": files or [{"path": "app/runtime/application/example.py", "additions": additions, "deletions": deletions}],
        "body": body,
        "updatedAt": "2026-05-07T00:00:00Z",
        "url": f"https://example.test/pull/{number}",
        "head_contains_main": head_contains_main,
        "contract_findings": contract_findings or [],
    }


def test_current_shell_aliases_normalize_to_canonical_track() -> None:
    for alias in (
        "PLCE",
        "PL+CE",
        "PL_CE",
        "PL/CE",
        "PL-CE",
        "ProductLoop",
        "ProductLifecycleContextEngineering",
    ):
        entry = build_matrix_from_prs(
            [_pr(body=_pr()["body"].replace("CurrentShell", alias))],
            DEFAULT_CONFIG,
        )["entries"][0]
        assert entry["track"] == "CurrentShell"


def test_current_shell_missing_owner_lane_is_advisory_not_blocker() -> None:
    entry = build_matrix_from_prs([_pr()], DEFAULT_CONFIG)["entries"][0]

    assert entry["current_shell_metadata_status"] == "advisory"
    assert "missing_owner_lane_advisory" in entry["advisories"]
    assert entry["merge_readiness_status"] == "ready_for_human_queue_review"


def test_current_shell_invalid_owner_lane_blocks_advisory_report() -> None:
    body = _pr()["body"] + "owner_lane: RandomThing\n"
    entry = build_matrix_from_prs([_pr(body=body)], DEFAULT_CONFIG)["entries"][0]

    assert entry["current_shell_metadata_status"] == "fail"
    assert "invalid_owner_lane:RandomThing" in entry["blocking_reasons"]
    assert entry["merge_readiness_status"] == "blocked"


def test_required_checks_accept_success_skipped_neutral_and_block_missing_pending_cancelled() -> None:
    assert DEFAULT_CONFIG["required_checks"] == [
        "repo-hygiene-and-architecture",
        "runtime-contract-tests",
        "product-pages-browser-e2e",
    ]
    assert DEFAULT_CONFIG["advisory_checks"] == []

    skipped_checks = _all_required_checks()
    skipped_checks[0] = _check(DEFAULT_CONFIG["required_checks"][0], conclusion="SKIPPED")
    skipped_checks[1] = _check(DEFAULT_CONFIG["required_checks"][1], conclusion="NEUTRAL")
    assert build_matrix_from_prs([_pr(checks=skipped_checks)], DEFAULT_CONFIG)["entries"][0]["ci_status"] == "pass"

    missing_checks = [check for check in _all_required_checks() if check["name"] != "product-pages-browser-e2e"]
    missing_entry = build_matrix_from_prs([_pr(checks=missing_checks)], DEFAULT_CONFIG)["entries"][0]
    assert missing_entry["ci_status"] == "incomplete"
    assert missing_entry["merge_readiness_status"] == "blocked"

    pending_checks = _all_required_checks()
    pending_checks[0] = _check(DEFAULT_CONFIG["required_checks"][0], conclusion="", status="IN_PROGRESS")
    pending_entry = build_matrix_from_prs([_pr(checks=pending_checks)], DEFAULT_CONFIG)["entries"][0]
    assert pending_entry["ci_status"] == "pending"
    assert pending_entry["merge_readiness_status"] == "blocked"

    cancelled_checks = _all_required_checks()
    cancelled_checks[0] = _check(DEFAULT_CONFIG["required_checks"][0], conclusion="CANCELLED")
    cancelled_entry = build_matrix_from_prs([_pr(checks=cancelled_checks)], DEFAULT_CONFIG)["entries"][0]
    assert cancelled_entry["ci_status"] == "fail"
    assert cancelled_entry["merge_readiness_status"] == "blocked"


def test_stale_base_marks_entry_stale() -> None:
    entry = build_matrix_from_prs([_pr(head_contains_main=False)], DEFAULT_CONFIG)["entries"][0]

    assert entry["base_drift_status"] == "stale_to_main"
    assert entry["merge_readiness_status"] == "stale"


def test_render_markdown_uses_advisory_shape_without_recommended_verdict() -> None:
    report = build_matrix_from_prs([_pr()], DEFAULT_CONFIG)
    markdown = render_markdown(report)

    assert "# Merge Governance Advisory" in markdown
    assert "ready_for_human_queue_review" in markdown
    assert "recommended_verdict" not in markdown


def test_main_writes_advisory_report_and_can_fail_on_blocking(tmp_path: Path) -> None:
    input_json = tmp_path / "prs.json"
    input_json.write_text(
        json.dumps([_pr(head_contains_main=False)]),
        encoding="utf-8",
    )
    json_out = tmp_path / "merge_governance_advisory.json"
    md_out = tmp_path / "merge_governance_advisory.md"

    assert main(["--input-json", str(input_json), "--json-out", str(json_out), "--md-out", str(md_out)]) == 0
    report = json.loads(json_out.read_text(encoding="utf-8"))
    assert report["artifact_type"] == "merge_governance_advisory"
    assert report["entries"][0]["merge_readiness_status"] == "stale"

    assert (
        main(
            [
                "--input-json",
                str(input_json),
                "--json-out",
                str(json_out),
                "--md-out",
                str(md_out),
                "--fail-on-blocking",
            ]
        )
        == 1
    )


def test_run_json_retries_transient_github_api_failure(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs):  # type: ignore[no-untyped-def]
        calls.append(command)
        if len(calls) == 1:
            return SimpleNamespace(
                returncode=1,
                stdout="",
                stderr="GraphQL: HTTP 504 timeout",
            )
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"ok": True}),
            stderr="",
        )

    monkeypatch.setattr(merge_debt_matrix_module.subprocess, "run", fake_run)
    monkeypatch.setattr(merge_debt_matrix_module.time, "sleep", lambda *_args, **_kwargs: None)

    result = merge_debt_matrix_module._run_json(["gh", "pr", "list"], retries=3)

    assert result == {"ok": True}
    assert len(calls) == 2


def test_load_config_uses_currentshell_required_defaults(tmp_path: Path) -> None:
    path = tmp_path / ".merge-governance.yml"
    path.write_text(
        "\n".join(
                [
                    "required_checks:",
                    "  - repo-hygiene-and-architecture",
                    "  - runtime-contract-tests",
                    "  - product-pages-browser-e2e",
                    "",
                    "advisory_checks:",
                    "",
                ]
            ),
        encoding="utf-8",
    )
    config = load_config(path)
    assert config["required_checks"] == DEFAULT_CONFIG["required_checks"]
    assert config["advisory_checks"] == []
