from __future__ import annotations

import json
from pathlib import Path

from scripts.run_accurate_intake_desktop_dogfood_launcher import (
    build_launch_descriptor,
    main,
)


def test_desktop_dogfood_launch_descriptor_uses_persistent_local_sqlite_and_launchpad_url() -> None:
    descriptor = build_launch_descriptor(
        host="127.0.0.1",
        port=8765,
        user_id="dogfood-user",
        db_path=Path("workspace_data/local_dogfood/accurate_intake.sqlite3"),
        local_debug_token="test-token",
    )

    assert descriptor["artifact_type"] == "accurate_intake_desktop_dogfood_launcher_descriptor"
    assert descriptor["status"] == "launch_descriptor_ready"
    assert descriptor["entry_surface"] == "desktop_dogfood_hub"
    assert descriptor["host"] == "127.0.0.1"
    assert descriptor["port"] == 8765
    assert descriptor["db_path"] == "workspace_data/local_dogfood/accurate_intake.sqlite3"
    assert descriptor["persistent_local_sqlite"] is True
    assert descriptor["reset_db_default"] is False
    assert descriptor["launch_url"] == (
        "http://127.0.0.1:8765/static/accurate-intake-desktop.html?user_id=dogfood-user"
    )
    assert descriptor["entry_pages"] == [
        "desktop",
        "chat",
        "today",
        "body",
        "feedback",
        "review",
        "data",
    ]
    assert descriptor["local_debug_token"] == "test-token"
    assert descriptor["local_debug_header"] == "X-Local-Debug-Token"
    assert descriptor["local_debug_token_in_url"] is False


def test_desktop_dogfood_launch_descriptor_preserves_non_claims_and_boundaries() -> None:
    descriptor = build_launch_descriptor(
        host="127.0.0.1",
        port=8765,
        user_id="dogfood-user",
        db_path=Path("workspace_data/local_dogfood/accurate_intake.sqlite3"),
        local_debug_token="test-token",
    )

    assert descriptor["runtime_truth_changed"] is False
    assert descriptor["mutation_legality_changed"] is False
    assert descriptor["fooddb_truth_updated"] is False
    assert descriptor["frontend_semantic_owner"] is False
    assert descriptor["live_llm_invoked"] is False
    assert descriptor["production_db_used"] is False
    assert descriptor["product_readiness_claimed"] is False
    assert descriptor["private_self_use_approved"] is False
    assert descriptor["not_claiming"] == [
        "product_ready",
        "private_self_use_approved",
        "production_ready",
        "live_llm_ready",
        "fooddb_expansion_ready",
    ]


def test_desktop_dogfood_launcher_cli_prints_descriptor_without_starting_server(
    tmp_path: Path,
    capsys,
) -> None:
    output_path = tmp_path / "launcher.json"
    db_path = tmp_path / "accurate_intake.sqlite3"

    exit_code = main(
        [
            "--describe-only",
            "--host",
            "127.0.0.1",
            "--port",
            "8765",
            "--user-id",
            "dogfood-user",
            "--db-path",
            str(db_path),
            "--local-debug-token",
            "test-token",
            "--output",
            str(output_path),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "launch_descriptor_ready"
    assert artifact["server_started"] is False
    assert artifact["browser_open_requested"] is False
    assert artifact["db_path"].endswith(
        ".pytest_tmp_local/test_desktop_dogfood_launcher_0/accurate_intake.sqlite3"
    )


def test_self_use_runbook_documents_desktop_launcher_without_readiness_claim() -> None:
    runbook = Path("docs/quality/ACCURATE_INTAKE_MVP_SELF_USE_RUNBOOK.md").read_text(encoding="utf-8-sig")

    assert "run_accurate_intake_desktop_dogfood_launcher.py" in runbook
    assert "workspace_data/local_dogfood/accurate_intake.sqlite3" in runbook
    assert "/static/accurate-intake-desktop.html" in runbook
    assert "X-Local-Debug-Token" in runbook
    assert "does not approve private self-use" in runbook
