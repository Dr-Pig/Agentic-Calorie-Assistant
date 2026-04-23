from __future__ import annotations

from app.text_integrity import (
    corruption_summary,
    find_text_corruption,
    is_corrupted_text,
    sanitize_text_structure,
    sanitize_text_value,
)


def test_text_integrity_detects_question_mark_corruption() -> None:
    mojibake = "?" + chr(0xF699) + "?憟嗉" + chr(0xF5CB)
    findings = find_text_corruption(
        {
            "raw_user_input": "????",
            "nested": {"meal_title": mojibake},
            "items": ["ok", "\ufffdbroken"],
        }
    )
    summary = corruption_summary(findings)
    assert len(summary) == 3
    assert {item["path"] for item in summary} == {"$.raw_user_input", "$.nested.meal_title", "$.items[1]"}


def test_text_integrity_sanitizes_corrupted_fields() -> None:
    payload = {
        "meal_title": "????",
        "pending_question": "I can't estimate this safely yet.",
        "missing_slots": ["????", "cup_size"],
        "nested": {"active_meal_title": "\ufffdbad", "goal": "lose_weight"},
    }
    cleaned = sanitize_text_structure(payload)
    assert cleaned["pending_question"] == "I can't estimate this safely yet."
    assert cleaned["missing_slots"] == ["cup_size"]
    assert cleaned["nested"] == {"goal": "lose_weight"}
    assert "meal_title" not in cleaned


def test_text_integrity_text_helpers() -> None:
    mojibake = "?" + chr(0xF699) + "?憟嗉" + chr(0xF5CB)
    assert is_corrupted_text("????") is True
    assert is_corrupted_text(mojibake) is True
    assert sanitize_text_value("????") is None
    assert sanitize_text_value(f" {mojibake} ") is None
    assert sanitize_text_value(" 珍珠奶茶 ") == "珍珠奶茶"
