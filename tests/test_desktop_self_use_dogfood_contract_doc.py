from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "docs" / "quality" / "CURRENT_SHELL_DESKTOP_SELF_USE_DOGFOOD_CONTRACT.md"
DOC_INDEX_PATH = ROOT / "docs" / "DOC_INDEX.md"


def test_desktop_self_use_dogfood_contract_is_indexed() -> None:
    doc_index = DOC_INDEX_PATH.read_text(encoding="utf-8-sig")

    assert "CURRENT_SHELL_DESKTOP_SELF_USE_DOGFOOD_CONTRACT.md" in doc_index
    assert "desktop local self-use dogfood" in doc_index


def test_desktop_self_use_dogfood_contract_locks_scope_and_non_claims() -> None:
    text = SPEC_PATH.read_text(encoding="utf-8-sig")

    required_fragments = [
        "desktop local self-use dogfood",
        "Chat / Today / Body / Feedback / Review Queue",
        "feedback is triage input, not product truth",
        "canonical product truth",
        "manager trace",
        "UI/session event",
        "feedback triage record",
        "golden-set candidate",
        "FoodDB macro expansion boundary",
        "broad FoodDB expansion is out of scope",
        "macro fields may be null",
        "return-to-mainline gate",
        "current_shell_fixture_e2e",
        "current_shell_compatibility_local_mvp_candidate_bundle",
    ]
    for fragment in required_fragments:
        assert fragment in text

    forbidden_fragments = [
        "private_self_use_approved: true",
        "product_readiness_claimed: true",
        "production_ready: true",
        "fooddb_truth_promoted: true",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in text
