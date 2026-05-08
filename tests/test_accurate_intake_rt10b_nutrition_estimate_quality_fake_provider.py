from __future__ import annotations

import asyncio
import json
from pathlib import Path


def test_rt10b_fake_provider_artifact_passes_fixture_wall() -> None:
    from scripts import run_accurate_intake_rt10b_nutrition_estimate_quality_fake_provider as module

    artifact = asyncio.run(module.build_rt10b_nutrition_estimate_quality_fake_provider_artifact())

    assert artifact["status"] == "pass"
    assert artifact["target_manager_runtime_gate"] == "rt10b_nutrition_estimate_quality_fake_provider"
    assert artifact["pass_type"] == "fixture"
    assert artifact["runtime_backed"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["summary"]["case_count"] == 5
    assert all(case["status"] == "pass" for case in artifact["cases"])


def test_rt10b_blocks_exactness_drift_from_fake_provider_payload() -> None:
    from scripts import run_accurate_intake_rt10b_nutrition_estimate_quality_fake_provider as module

    case = asyncio.run(
        module._provider_case(  # noqa: SLF001
            case_id="bad-exactness",
            family="generic_common_food",
            case_factory=lambda: module._anchor_case("\u6211\u5403\u4e86\u8336\u8449\u86cb"),  # noqa: SLF001
            provider_payload={
                "item_results": [
                    {
                        "interpreted_food_identity": "\u8336\u8449\u86cb",
                        "likely_kcal": 70,
                        "exactness_posture": "exact",
                        "suggested_followup_question": None,
                    }
                ]
            },
        )
    )

    assert case["status"] == "fail"
    assert "exactness_posture_drift" in case["blockers"]


def test_rt10b_blocks_forbidden_mutation_fields_in_provider_payload() -> None:
    from scripts import run_accurate_intake_rt10b_nutrition_estimate_quality_fake_provider as module

    case = asyncio.run(
        module._provider_case(  # noqa: SLF001
            case_id="bad-mutation",
            family="generic_common_food",
            case_factory=lambda: module._anchor_case("\u6211\u5403\u4e86\u8336\u8449\u86cb"),  # noqa: SLF001
            provider_payload={
                "item_results": [
                    {
                        "interpreted_food_identity": "\u8336\u8449\u86cb",
                        "likely_kcal": 70,
                        "exactness_posture": "estimated",
                        "suggested_followup_question": None,
                    }
                ],
                "mutation_result": {"should_not": "exist"},
            },
        )
    )

    assert case["status"] == "fail"
    assert "forbidden_mutation_fields_present" in case["blockers"]


def test_rt10b_cli_writes_artifact(tmp_path: Path) -> None:
    from scripts import run_accurate_intake_rt10b_nutrition_estimate_quality_fake_provider as module

    output_path = tmp_path / "accurate_intake_rt10b_nutrition_estimate_quality_fake_provider.json"
    exit_code = module.main(["--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
    assert artifact["artifact_name"] == "accurate_intake_rt10b_nutrition_estimate_quality_fake_provider.json"
