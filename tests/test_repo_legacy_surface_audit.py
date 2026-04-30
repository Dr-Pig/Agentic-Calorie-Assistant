from __future__ import annotations

from pathlib import Path

from scripts.audit_repo_legacy_surfaces import build_report


def test_repo_legacy_surface_audit_detects_tracked_archive_path(tmp_path: Path) -> None:
    report = build_report(
        root=tmp_path,
        tracked_paths=[("docs/" + "archive/old.md")],
    )

    assert report["fails_build"] is True
    assert report["tracked_path_finding_count"] == 1


def test_repo_legacy_surface_audit_detects_active_package_filename(tmp_path: Path) -> None:
    report = build_report(
        root=tmp_path,
        tracked_paths=[("app/body/application/v2_" + "bundle" + "3_service.py")],
    )

    assert report["fails_build"] is True
    assert report["tracked_path_finding_count"] == 1


def test_repo_legacy_surface_audit_detects_active_tool_batch_test_filename(tmp_path: Path) -> None:
    report = build_report(
        root=tmp_path,
        tracked_paths=[("tests/test_" + "bundle" + "2_tool_batch_semantic_rewrite_guard.py")],
    )

    assert report["fails_build"] is True
    assert report["tracked_path_finding_count"] == 1


def test_repo_legacy_surface_audit_detects_stale_text_marker(tmp_path: Path) -> None:
    target = tmp_path / "app" / "runtime" / "example.py"
    target.parent.mkdir(parents=True)
    legacy_action = "run_" + "nutrition" + "_resolution"
    target.write_text(f"token = '{legacy_action}'\n", encoding="utf-8")

    report = build_report(root=tmp_path, tracked_paths=[])

    assert report["fails_build"] is True
    assert report["text_finding_count"] >= 1


def test_repo_legacy_surface_audit_detects_legacy_bundle_runner_marker(tmp_path: Path) -> None:
    target = tmp_path / "scripts" / "example.py"
    target.parent.mkdir(parents=True)
    legacy_runner = "run_v2_" + "bundle" + "2_live_eval"
    target.write_text(f"token = '{legacy_runner}'\n", encoding="utf-8")

    report = build_report(root=tmp_path, tracked_paths=[])

    assert report["fails_build"] is True
    assert report["text_finding_count"] >= 1


def test_repo_legacy_surface_audit_detects_active_bundle_import_marker(tmp_path: Path) -> None:
    target = tmp_path / "app" / "composition" / "example.py"
    target.parent.mkdir(parents=True)
    marker = "app.composition." + "bundle" + "2_response"
    target.write_text(f"from {marker} import build_response\n", encoding="utf-8")

    report = build_report(root=tmp_path, tracked_paths=[])

    assert report["fails_build"] is True
    assert report["legacy_naming_finding_count"] >= 1


def test_repo_legacy_surface_audit_detects_active_body_calibration_package_marker(tmp_path: Path) -> None:
    target = tmp_path / "app" / "body" / "application" / "example.py"
    target.parent.mkdir(parents=True)
    marker = "process_" + "bundle" + "3_body_and_calibration"
    target.write_text(f"async def {marker}():\n    pass\n", encoding="utf-8")

    report = build_report(root=tmp_path, tracked_paths=[])

    assert report["fails_build"] is True
    assert report["legacy_naming_finding_count"] >= 1


def test_repo_legacy_surface_audit_detects_stale_nutrition_policy_path(tmp_path: Path) -> None:
    target = tmp_path / "config" / "active_code_policy.jsonc"
    target.parent.mkdir(parents=True)
    marker = "app/nutrition/application/" + "b2_" + "local_synthesis.py"
    target.write_text(f'{{"path": "{marker}"}}\n', encoding="utf-8")

    report = build_report(root=tmp_path, tracked_paths=[])

    assert report["fails_build"] is True
    assert report["legacy_naming_finding_count"] >= 1


def test_repo_legacy_surface_audit_detects_stale_body_calibration_plan_reference(tmp_path: Path) -> None:
    target = tmp_path / "docs" / "specs" / "APP_V2_IMPLEMENTATION_PLAN.md"
    target.parent.mkdir(parents=True)
    marker = "v2_" + "bundle" + "3_service.py"
    target.write_text(f"- {marker}\n", encoding="utf-8")

    report = build_report(root=tmp_path, tracked_paths=[])

    assert report["fails_build"] is True
    assert report["legacy_naming_finding_count"] >= 1


def test_repo_legacy_surface_audit_allows_trace_fallback_path(tmp_path: Path) -> None:
    target = tmp_path / "app" / "budget" / "interface" / "today_trace_debug.py"
    target.parent.mkdir(parents=True)
    old_turn_trace = "v2_" + "bundle1"
    old_execution_trace = "v2_" + "bundle2"
    target.write_text(f"bundles = ('{old_turn_trace}', '{old_execution_trace}')\n", encoding="utf-8")

    report = build_report(root=tmp_path, tracked_paths=[])

    assert report["fails_build"] is False
    assert report["legacy_naming_finding_count"] == 0


def test_repo_legacy_surface_audit_detects_legacy_bundle_readiness_language(tmp_path: Path) -> None:
    target = tmp_path / "docs" / "quality" / "example.md"
    target.parent.mkdir(parents=True)
    marker = "Bundle " + "readiness"
    target.write_text(f"## {marker}\n", encoding="utf-8")

    report = build_report(root=tmp_path, tracked_paths=[])

    assert report["fails_build"] is True
    assert report["text_finding_count"] >= 1


def test_repo_legacy_surface_audit_passes_clean_temp_repo(tmp_path: Path) -> None:
    target = tmp_path / "app" / "runtime" / "example.py"
    target.parent.mkdir(parents=True)
    target.write_text("token = 'manager_runtime'\n", encoding="utf-8")

    report = build_report(root=tmp_path, tracked_paths=["app/runtime/example.py"])

    assert report["fails_build"] is False
    assert report["finding_count"] == 0
