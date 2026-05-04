from __future__ import annotations


def _fixture_payload() -> dict:

    return {
        "fixture_input_used": True,
        "real_dogfood_export_used": False,
        "user_id": "fixture-user",
        "meal_logs": [
            {
                "trace_id": "meal-1",
                "meal_id": "m1",
                "logged_at": "2026-04-01T08:15:00+08:00",
                "item_names": ["oatmeal", "latte"],
                "item_kinds": ["staple", "drink"],
                "staple_types": ["oats"],
                "drink_names": ["latte"],
                "store_name": "Morning Bar",
            },
            {
                "trace_id": "meal-2",
                "meal_id": "m2",
                "logged_at": "2026-04-02T08:05:00+08:00",
                "item_names": ["oatmeal", "latte"],
                "item_kinds": ["staple", "drink"],
                "staple_types": ["oats"],
                "drink_names": ["latte"],
                "store_name": "Morning Bar",
            },
            {
                "trace_id": "meal-3",
                "meal_id": "m3",
                "logged_at": "2026-04-03T08:22:00+08:00",
                "item_names": ["oatmeal", "latte"],
                "item_kinds": ["staple", "drink"],
                "staple_types": ["oats"],
                "drink_names": ["latte"],
                "store_name": "Morning Bar",
            },
            {
                "trace_id": "meal-4",
                "meal_id": "m4",
                "logged_at": "2026-04-04T21:20:00+08:00",
                "item_names": ["fried chicken"],
                "item_kinds": ["main"],
                "staple_types": [],
                "drink_names": [],
                "store_name": "Night Market",
            },
        ],
        "body_observations": [
            {
                "trace_id": "body-1",
                "observed_at": "2026-04-01T07:30:00+08:00",
                "weight_kg": 82.1,
            },
            {
                "trace_id": "body-2",
                "observed_at": "2026-04-08T07:35:00+08:00",
                "weight_kg": 81.8,
            },
        ],
        "budget_summaries": [
            {
                "trace_id": "budget-1",
                "date": "2026-04-01",
                "target_kcal": 2100,
                "actual_kcal": 2300,
                "overshoot_kcal": 200,
            },
            {
                "trace_id": "budget-2",
                "date": "2026-04-02",
                "target_kcal": 2100,
                "actual_kcal": 2000,
                "overshoot_kcal": 0,
            },
        ],
        "calibration_diagnostics": [
            {
                "trace_id": "cal-1",
                "window_start": "2026-03-25",
                "window_end": "2026-04-08",
                "expected_weight_delta_kg": -0.4,
                "observed_weight_delta_kg": -0.1,
            }
        ],
        "language_observations": [
            {
                "trace_id": "lang-1",
                "observed_at": "2026-04-02T12:20:00+08:00",
                "user_phrase": "正常便當",
                "observed_meaning": "usually rice, one main, and two to three sides",
                "phrase_kind": "portion_phrase",
                "portion_semantics": {
                    "portion_label": "normal_meal",
                    "expected_components": ["rice", "main", "two_to_three_sides"],
                },
                "confidence": 0.62,
            }
        ],
        "intake_estimation_events": [
            {
                "trace_id": "bias-1",
                "observed_at": "2026-04-03T22:15:00+08:00",
                "bias_direction": "likely_underestimate",
                "event_kind": "missed_item_pattern",
                "reason": "missed_drink_or_sauce",
                "missed_item_kind": "drink_or_sauce",
                "correction_tendency": "adds_kcal_after_clarification",
                "correction_delta_kcal": 180,
            }
        ],
        "app_usage_events": [
            {
                "trace_id": "usage-1",
                "observed_at": "2026-04-04T23:10:00+08:00",
                "usage_signal": "late_night_backfill",
                "surface": "chat",
            },
            {
                "trace_id": "usage-2",
                "observed_at": "2026-04-05T09:10:00+08:00",
                "usage_signal": "accepted_quick_action",
                "surface": "chat",
            },
        ],
        "interaction_events": [
            {
                "trace_id": "interaction-1",
                "observed_at": "2026-04-05T09:11:00+08:00",
                "preference_signal": "prefers_direct_calorie_numbers",
                "action": "accepted",
            }
        ],
        "negative_preference_observations": [
            {
                "trace_id": "neg-1",
                "observed_at": "2026-04-05T12:15:00+08:00",
                "preference_scope": "ingredient",
                "value": "cilantro",
                "source_signal": "explicit_rejection",
                "confidence": 0.9,
            }
        ],
        "temporary_preference_observations": [
            {
                "trace_id": "temp-1",
                "observed_at": "2026-04-06T18:30:00+08:00",
                "preference_type": "temporary_constraint",
                "value": "lower_oil_dinner",
                "context_scope": "dinner",
                "valid_from": "2026-04-06",
                "valid_until": "2026-04-10",
                "confidence": 0.8,
            }
        ],
        "conversation_history_summaries": [
            {
                "trace_id": "conv-1",
                "conversation_id": "chat-2026-04-01",
                "observed_at": "2026-04-01T23:40:00+08:00",
                "summary": "User discussed late-night snack logging and wanted fewer repeated questions.",
                "topic_tags": ["late_logging", "followup_preference"],
            }
        ],
        "review_actions": [
            {
                "action_id": "review-accept-language",
                "target_candidate_ids": ["user-language-正常便當"],
                "action_type": "accept_candidate",
                "actor": "fixture_human_reviewer",
                "rationale": "Useful phrase for future intake clarification.",
            },
            {
                "action_id": "review-reject-usage",
                "target_candidate_ids": ["app-usage-style-pattern"],
                "action_type": "reject_candidate",
                "actor": "fixture_human_reviewer",
                "rationale": "Insufficient evidence for app usage style.",
            },
        ],
        "trace_metadata": [
            {"trace_id": "meal-1", "source_object_ref": "MealThread:m1"},
            {"trace_id": "budget-1", "source_object_ref": "DayBudgetLedger:2026-04-01"},
        ],
        "candidate_pool": [
            {
                "candidate_id": "food-1",
                "name": "oatmeal with latte",
                "source": "fixture",
                "estimated_kcal": 520,
                "tags": ["breakfast", "oats"],
            }
        ],
        "menu_scan_context": {
            "scan_source": "text_description",
            "restaurant_name": "Morning Bar",
            "parsed_items": [
                {
                    "item_name": "oatmeal with latte",
                    "estimated_kcal_range": [480, 560],
                    "confidence": 0.82,
                },
                {
                    "item_name": "cilantro chicken bowl",
                    "estimated_kcal_range": [620, 760],
                    "confidence": 0.71,
                },
            ],
            "parse_confidence": 0.78,
            "unparsed_items": [],
        },
    }
