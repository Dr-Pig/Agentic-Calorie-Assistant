from pathlib import Path

import yaml

from app.benchmark_loader import load_benchmark_cases


def test_nutrition_output_contract_benchmark_loads_selected_cases() -> None:
    fixture = Path("tests/fixtures/nutrition_output_contract_benchmark.yaml")
    cases = load_benchmark_cases(fixture)

    assert len(cases) == 8
    assert {case["id"] for case in cases} == {
        "case_001_mos_pork_burger",
        "case_003_mos_breakfast_combo",
        "case_006_711_oyakodon",
        "case_011_shared_stirfry_partial_details",
        "case_013_poke_salmon_spicy_mayo",
        "case_014_zhajiangmian_generic",
        "case_015_zhajiangmian_taiwanese",
        "case_016_salmon_ikura_don",
    }


def test_nutrition_output_contract_benchmark_marks_macro_modes() -> None:
    fixture = Path("tests/fixtures/nutrition_output_contract_benchmark.yaml")
    raw = yaml.safe_load(fixture.read_text(encoding="utf-8"))
    items = {item["id"]: item for item in raw["items"]}
    loaded = {item["id"]: item for item in load_benchmark_cases(fixture)}

    assert items["case_001_mos_pork_burger"]["expected_contract"]["macro_mode"] == "unavailable"
    assert items["case_003_mos_breakfast_combo"]["expected_contract"]["macro_mode"] == "derived_from_components"
    assert items["case_011_shared_stirfry_partial_details"]["expected_contract"]["macro_mode"] == "derived_from_components"
    assert items["case_015_zhajiangmian_taiwanese"]["expected_contract"]["macro_mode"] == "derived_from_components"
    assert loaded["case_001_mos_pork_burger"]["expected_contract"]["macro_mode"] == "unavailable"
