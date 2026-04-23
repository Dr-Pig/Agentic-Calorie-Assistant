from __future__ import annotations

from scripts.check_markdown_encoding import UTF8_BOM, policy_markdown_paths, verify_markdown_encoding


def test_byte_level_verifier_accepts_valid_utf8_chinese(tmp_path) -> None:
    path = tmp_path / "spec.md"
    path.write_bytes(UTF8_BOM + "# 標題\n\n本文件定義 single manager。\n".encode("utf-8"))

    assert verify_markdown_encoding(path, require_bom=True) == []


def test_byte_level_verifier_does_not_confuse_terminal_rendering_with_corruption(tmp_path) -> None:
    path = tmp_path / "spec.md"
    text = "# L3.1\n\n本文件定義 V2 intake 主流程。\n"
    path.write_bytes(text.encode("utf-8"))

    assert verify_markdown_encoding(path) == []


def test_byte_level_verifier_rejects_replacement_and_private_use_characters(tmp_path) -> None:
    path = tmp_path / "spec.md"
    path.write_text("bad \ufffd text \ue000\n", encoding="utf-8")

    reasons = {issue.reason for issue in verify_markdown_encoding(path)}

    assert "replacement_character" in reasons
    assert "private_use_character" in reasons


def test_byte_level_verifier_can_require_bom(tmp_path) -> None:
    path = tmp_path / "spec.md"
    path.write_text("# title\n", encoding="utf-8")

    reasons = {issue.reason for issue in verify_markdown_encoding(path, require_bom=True)}

    assert "missing_utf8_bom" in reasons


def test_policy_markdown_paths_exclude_archive(tmp_path) -> None:
    root = tmp_path
    (root / "AGENTS.md").write_text("# Agent\n", encoding="utf-8")
    (root / "docs" / "specs").mkdir(parents=True)
    (root / "docs" / "archive").mkdir(parents=True)
    active = root / "docs" / "specs" / "active.md"
    archived = root / "docs" / "archive" / "old.md"
    active.write_text("# active\n", encoding="utf-8")
    archived.write_text("# old\n", encoding="utf-8")

    paths = policy_markdown_paths(root)

    assert active in paths
    assert root / "AGENTS.md" in paths
    assert archived not in paths
