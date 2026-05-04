from __future__ import annotations

import binascii
import struct
import zlib
from pathlib import Path

import pytest

from scripts import run_accurate_intake_product_pages_visual_qa as module


def _png_fixture_bytes(*, width: int = 1, height: int = 1) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(
            ">I", binascii.crc32(kind + payload) & 0xFFFFFFFF
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    raw_scanline = b"\x00" + (b"\x00\x00\x00\x00" * width)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw_scanline * height)) + chunk(
        b"IEND", b""
    )


def _passing_report(tmp_path: Path) -> dict[str, object]:
    screenshot_dir = tmp_path / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    for name in ("chat-desktop.png", "today-desktop.png", "body-desktop.png"):
        (screenshot_dir / name).write_bytes(_png_fixture_bytes(width=1440, height=1100))
    for name in ("chat-mobile.png", "today-mobile.png", "body-mobile.png"):
        (screenshot_dir / name).write_bytes(_png_fixture_bytes(width=390, height=844))
    return {
        "browser_executed": True,
        "desktop_screenshots_captured": True,
        "mobile_screenshots_captured": True,
        "chat_surface_verified": True,
        "today_surface_verified": True,
        "body_surface_verified": True,
        "three_distinct_pages_verified": True,
        "desktop_no_overflow": True,
        "mobile_no_overflow": True,
        "visible_trace_debug_terms_absent": True,
        "forbidden_storage_used": False,
        "frontend_semantic_owner": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "production_db_used": False,
        "web_readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "screenshots": {
            "desktop": {
                "chat": str(screenshot_dir / "chat-desktop.png"),
                "today": str(screenshot_dir / "today-desktop.png"),
                "body": str(screenshot_dir / "body-desktop.png"),
            },
            "mobile": {
                "chat": str(screenshot_dir / "chat-mobile.png"),
                "today": str(screenshot_dir / "today-mobile.png"),
                "body": str(screenshot_dir / "body-mobile.png"),
            },
        },
    }


def test_product_pages_visual_qa_missing_playwright_is_blocked_not_readiness(monkeypatch, tmp_path: Path) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_product_pages_visual_qa_report(
        db_path=tmp_path / "visual-qa.sqlite3",
        screenshot_dir=tmp_path / "screenshots",
    )

    assert report["artifact_type"] == "accurate_intake_product_pages_visual_qa"
    assert report["status"] == "blocked"
    assert report["browser_executed"] is False
    assert report["browser_execution_required"] is False
    assert report["blockers"] == ["playwright_not_installed"]
    assert report["web_readiness_claimed"] is False
    assert report["product_readiness_claimed"] is False
    assert report["private_self_use_approved"] is False
    assert report["live_llm_invoked"] is False
    assert report["web_tavily_used"] is False


def test_product_pages_visual_qa_can_require_browser_execution(monkeypatch, tmp_path: Path) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_product_pages_visual_qa_report(
        db_path=tmp_path / "visual-qa.sqlite3",
        screenshot_dir=tmp_path / "screenshots",
        require_browser_execution=True,
    )

    assert report["status"] == "fail"
    assert report["browser_execution_required"] is True
    assert report["browser_executed"] is False
    assert report["blockers"] == ["playwright_not_installed"]


def test_product_pages_visual_qa_validator_requires_visual_evidence(tmp_path: Path) -> None:
    status, blockers = module._validate(_passing_report(tmp_path))

    assert status == "pass"
    assert blockers == []


def test_product_pages_visual_qa_validator_rejects_missing_screenshot_files(tmp_path: Path) -> None:
    report = _passing_report(tmp_path)
    Path(str(report["screenshots"]["desktop"]["chat"])).unlink()

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "screenshot_file_missing:desktop:chat" in blockers


def test_product_pages_visual_qa_validator_rejects_empty_or_non_png_screenshots(tmp_path: Path) -> None:
    report = _passing_report(tmp_path)
    empty_path = Path(str(report["screenshots"]["desktop"]["today"]))
    empty_path.write_bytes(b"")
    jpg_path = empty_path.with_name("body-mobile.jpg")
    jpg_path.write_bytes(b"fixture")
    report["screenshots"]["mobile"]["body"] = str(jpg_path)

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "screenshot_file_empty:desktop:today" in blockers
    assert "screenshot_not_png:mobile:body" in blockers


def test_product_pages_visual_qa_validator_rejects_corrupt_png_bytes(tmp_path: Path) -> None:
    report = _passing_report(tmp_path)
    corrupt_path = Path(str(report["screenshots"]["mobile"]["chat"]))
    corrupt_path.write_bytes(b"\x89PNG\r\n\x1a\ncorrupt")

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "screenshot_invalid_png:mobile:chat" in blockers


def test_product_pages_visual_qa_validator_rejects_header_only_png_stub(tmp_path: Path) -> None:
    report = _passing_report(tmp_path)
    stub_path = Path(str(report["screenshots"]["desktop"]["body"]))
    stub_path.write_bytes(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 1, 1))

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "screenshot_invalid_png:desktop:body" in blockers


def test_product_pages_visual_qa_validator_rejects_tiny_png_screenshot_evidence(tmp_path: Path) -> None:
    report = _passing_report(tmp_path)
    tiny_path = Path(str(report["screenshots"]["desktop"]["chat"]))
    tiny_path.write_bytes(_png_fixture_bytes(width=1, height=1))

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "screenshot_too_small:desktop:chat:1x1" in blockers


def test_product_pages_visual_qa_validator_rejects_missing_surfaces_and_claims(tmp_path: Path) -> None:
    report = _passing_report(tmp_path)
    report["desktop_screenshots_captured"] = False
    report["mobile_screenshots_captured"] = False
    report["chat_surface_verified"] = False
    report["today_surface_verified"] = False
    report["body_surface_verified"] = False
    report["visible_trace_debug_terms_absent"] = False
    report["frontend_semantic_owner"] = True
    report["web_readiness_claimed"] = True

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "desktop_screenshots_not_captured" in blockers
    assert "mobile_screenshots_not_captured" in blockers
    assert "chat_surface_not_verified" in blockers
    assert "today_surface_not_verified" in blockers
    assert "body_surface_not_verified" in blockers
    assert "visible_trace_debug_terms_present" in blockers
    assert "frontend_semantic_owner" in blockers
    assert "web_readiness_claimed" in blockers


def test_product_pages_visual_qa_runs_real_browser_when_playwright_available(tmp_path: Path) -> None:
    try:
        module._load_sync_playwright()
    except module.BrowserSmokeDependencyMissing:
        pytest.skip("Playwright is not installed in this environment.")

    report = module.build_product_pages_visual_qa_report(
        db_path=tmp_path / "visual-qa.sqlite3",
        screenshot_dir=tmp_path / "screenshots",
        require_browser_execution=True,
        timeout_ms=25000,
    )

    assert report["status"] == "pass"
    assert report["browser_executed"] is True
    assert report["desktop_screenshots_captured"] is True
    assert report["mobile_screenshots_captured"] is True
    assert report["chat_surface_verified"] is True
    assert report["today_surface_verified"] is True
    assert report["body_surface_verified"] is True
    for viewport_screenshots in report["screenshots"].values():
        for screenshot_path in viewport_screenshots.values():
            path = Path(str(screenshot_path))
            assert path.exists()
            assert path.suffix == ".png"
            assert path.stat().st_size > 0


def test_ci_runs_product_pages_visual_qa_and_uploads_screenshots() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "test_accurate_intake_product_pages_visual_qa.py" in workflow
    assert "run_accurate_intake_product_pages_visual_qa.py --require-browser-execution" in workflow
    assert "accurate_intake_product_pages_visual_qa_ci.json" in workflow
    assert "artifacts/product_pages_visual_qa_ci" in workflow


def test_product_pages_visual_qa_stays_out_of_fooddb_websearch_and_live_boundaries() -> None:
    source = Path("scripts/run_accurate_intake_product_pages_visual_qa.py").read_text(encoding="utf-8")

    forbidden = [
        "app.providers",
        "tavily_adapter",
        "Tavily",
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "fooddb_evidence_used = True",
        "live_llm_invoked = True",
        "web_tavily_used = True",
    ]
    for fragment in forbidden:
        assert fragment not in source
