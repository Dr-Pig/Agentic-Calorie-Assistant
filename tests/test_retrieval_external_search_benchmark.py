from pathlib import Path

from app.benchmark_loader import load_benchmark_cases


def test_retrieval_external_search_benchmark_loads_selected_cases() -> None:
    fixture = Path("tests/fixtures/retrieval_external_search_benchmark.yaml")
    cases = load_benchmark_cases(fixture)

    assert len(cases) == 8
    assert {case["id"] for case in cases} == {
        "case_001_mos_pork_burger",
        "case_003_mos_breakfast_combo",
        "case_006_711_oyakodon",
        "case_007_yoshinoya_large_beef_bowl",
        "case_010_shared_stirfry_generic",
        "case_013_poke_salmon_spicy_mayo",
        "case_017_luwei_generic",
        "case_018_luwei_detailed",
    }


def test_retrieval_external_search_benchmark_contains_mixed_paths() -> None:
    fixture = Path("tests/fixtures/retrieval_external_search_benchmark.yaml")
    cases = {case["id"]: case for case in load_benchmark_cases(fixture)}

    assert cases["case_001_mos_pork_burger"]["expected_retrieval"]["path_family"] == "local_exact_only"
    assert cases["case_007_yoshinoya_large_beef_bowl"]["expected_retrieval"]["path_family"] == "external_official_escalation"
    assert cases["case_013_poke_salmon_spicy_mayo"]["expected_retrieval"]["path_family"] == "local_anchor_only"
    assert cases["case_017_luwei_generic"]["expected_retrieval"]["path_family"] == "template_only"
