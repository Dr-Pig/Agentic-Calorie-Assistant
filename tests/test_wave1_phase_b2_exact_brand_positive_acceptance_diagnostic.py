from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from scripts.diagnose_wave1_phase_b2_exact_brand_positive_acceptance import (
    classify_primary_root_cause,
    diagnose_positive_case,
    check_requested_size_present,
    check_requested_item_present,
)

@pytest.mark.parametrize(
    "raw_content, expected",
    [
        ("星巴克大杯那堤熱量 150大卡", True),
        ("中杯摩卡", False),
        ("星巴克grande那堤", True),
        ("那堤 473ml", True),
        ("那堤特大杯", False),
    ]
)
def test_check_requested_size_present(raw_content: str, expected: bool):
    assert check_requested_size_present(raw_content) is expected


@pytest.mark.parametrize(
    "raw_content, expected",
    [
        ("星巴克大杯那堤熱量 150大卡", True),
        ("Latte熱量", True),
        ("星巴克美式咖啡", False),
    ]
)
def test_check_requested_item_present(raw_content: str, expected: bool):
    assert check_requested_item_present(raw_content) is expected


def test_classify_no_raw_content():
    # 1. no raw_content -> official_source_missing_nutrition
    cause = classify_primary_root_cause(
        reason_if_missing=None,
        hard_recheck_rejected=False,
        hard_recheck_too_strict=False,
        packet_consumption_rejected=False,
        raw_content_present=False,
        requested_item_present=False,
        requested_size_present=False,
        kcal_candidates_found=False,
    )
    assert cause == "official_source_missing_nutrition"

def test_classify_raw_content_item_but_no_size():
    # 2. raw content has item but no size -> extract_missing_requested_size
    cause = classify_primary_root_cause(
        reason_if_missing=None,
        hard_recheck_rejected=False,
        hard_recheck_too_strict=False,
        packet_consumption_rejected=False,
        raw_content_present=True,
        requested_item_present=True,
        requested_size_present=False,
        kcal_candidates_found=True,
    )
    assert cause == "extract_missing_requested_size"

def test_classify_raw_content_item_and_size_no_kcal():
    # raw_content has item and size but no parseable kcal -> extract_missing_parseable_kcal
    cause = classify_primary_root_cause(
        reason_if_missing=None,
        hard_recheck_rejected=False,
        hard_recheck_too_strict=False,
        packet_consumption_rejected=False,
        raw_content_present=True,
        requested_item_present=True,
        requested_size_present=True,
        kcal_candidates_found=False,
    )
    assert cause == "extract_missing_parseable_kcal"

def test_classify_raw_content_no_size_no_kcal():
    # raw_content has item but no size -> extract_missing_requested_size (unchanged)
    cause = classify_primary_root_cause(
        reason_if_missing=None,
        hard_recheck_rejected=False,
        hard_recheck_too_strict=False,
        packet_consumption_rejected=False,
        raw_content_present=True,
        requested_item_present=True,
        requested_size_present=False,
        kcal_candidates_found=False,
    )
    assert cause == "extract_missing_requested_size"

def test_classify_raw_content_size_kcal_no_packet():
    # 3. raw content has size/kcal but no packet -> extract_packetization_gap
    cause = classify_primary_root_cause(
        reason_if_missing="packetizer_discarded_due_to_missing_kcal",
        hard_recheck_rejected=False,
        hard_recheck_too_strict=False,
        packet_consumption_rejected=False,
        raw_content_present=True,
        requested_item_present=True,
        requested_size_present=True,
        kcal_candidates_found=True,
    )
    assert cause == "extract_packetization_gap"

def test_classify_packet_exists_hard_recheck_rejects():
    # 4. packet exists but hard recheck rejects -> hard_recheck_correct_reject
    cause = classify_primary_root_cause(
        reason_if_missing=None,
        hard_recheck_rejected=True,
        hard_recheck_too_strict=False,
        packet_consumption_rejected=False,
        raw_content_present=True,
        requested_item_present=True,
        requested_size_present=True,
        kcal_candidates_found=True,
    )
    assert cause == "hard_recheck_correct_reject"

def test_classify_packet_accepted_but_consumption_gap():
    # 5. packet accepted by recheck but not consumption -> packet_consumption_gap
    cause = classify_primary_root_cause(
        reason_if_missing=None,
        hard_recheck_rejected=False,
        hard_recheck_too_strict=False,
        packet_consumption_rejected=True,
        raw_content_present=True,
        requested_item_present=True,
        requested_size_present=True,
        kcal_candidates_found=True,
    )
    assert cause == "packet_consumption_gap"


@pytest.fixture
def dummy_canary_json():
    return {
        "cases": [
            {
                "case_id": "starbucks_latte_positive",
                "raw_user_input": "我喝了星巴克大杯那堤",
                "web_query": "星巴克大杯那堤",
                "trace": {
                    "selected_search_packet_id": "pkt_123",
                    "candidate_traces": [
                        {
                            "packet_id": "pkt_123",
                            "source_url": "https://example.com/starbucks",
                            "source_title": "Starbucks Latte",
                            "candidate_identity": "Starbucks Latte",
                        }
                    ]
                }
            }
        ]
    }


@pytest.mark.asyncio
async def test_diagnose_positive_case_no_raw_content(dummy_canary_json):
    mock_port = AsyncMock()
    mock_port.extract_rows.return_value = [{"url": "https://example.com/starbucks", "raw_content": ""}]
    
    result = await diagnose_positive_case(
        canary_json=dummy_canary_json,
        case_id="starbucks_latte_positive",
        extract_port=mock_port,
    )
    
    assert result["primary_root_cause"] == "official_source_missing_nutrition"
    assert result["extract"]["raw_content_present"] is False
    assert result["recommended_next_step"] == "defer_to_manual_product_decision"


@pytest.mark.asyncio
async def test_diagnose_positive_case_missing_size(dummy_canary_json):
    mock_port = AsyncMock()
    # Content has item (那堤) but no size string, and has some kcals
    mock_port.extract_rows.return_value = [{"url": "https://example.com/starbucks", "raw_content": "那堤 熱量 150大卡", "title": "熱濃縮咖啡飲料-那堤", "serving_basis": "100g"}]
    
    result = await diagnose_positive_case(
        canary_json=dummy_canary_json,
        case_id="starbucks_latte_positive",
        extract_port=mock_port,
    )
    
    assert result["primary_root_cause"] == "extract_missing_requested_size"
    assert result["extract"]["raw_content_present"] is True
    assert result["extract"]["requested_size_present"] is False


@pytest.mark.asyncio
async def test_diagnose_positive_case_has_item_size_but_no_kcal(dummy_canary_json):
    mock_port = AsyncMock()
    # Content has item + size but no parseable kcal (the real Starbucks scenario)
    mock_port.extract_rows.return_value = [{"url": "https://example.com/starbucks", "raw_content": "那堤 大杯 很香很好喝，沒有寫熱量", "title": "熱濃縮咖啡飲料-那堤", "serving_basis": "1杯"}]
    
    result = await diagnose_positive_case(
        canary_json=dummy_canary_json,
        case_id="starbucks_latte_positive",
        extract_port=mock_port,
    )
    
    assert result["primary_root_cause"] == "extract_missing_parseable_kcal"
    assert result["extract"]["requested_item_present"] is True
    assert result["extract"]["requested_size_present"] is True
    assert result["extract"]["kcal_candidates_found"] is False
    assert result["extract_packet"]["created"] is False
    assert result["recommended_next_step"] == "defer_exact_brand_positive_acceptance"
