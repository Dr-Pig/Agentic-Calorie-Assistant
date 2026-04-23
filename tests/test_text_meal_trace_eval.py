from __future__ import annotations

from app.runtime.infrastructure.trace.trace_eval import evaluate_trace_contract


def test_trace_eval_attributes_missing_required_checks_to_risk_validator() -> None:
    trace_contract = {
        'planner_used': True,
        'planner_output': {'intent': 'food_estimation'},
        'normalizer_mode': 'off',
        'normalizer_diff': {'changed': False, 'normalized_text': 'ramen'},
        'template_match': {'blocked': False},
        'rescue_applied': {'rescue_layer': None},
        'db_hit_type': 'none',
        'followup_decision': 'not_needed',
    }
    quality_signals = {
        'missing_required_checks': ['broth_consumption'],
    }

    verdict = evaluate_trace_contract(
        trace_contract,
        quality_signals,
        best_answer_source='initial',
        retry_triggered=False,
    )

    assert verdict['failed_layer'] == 'risk_validator'
    assert verdict['win_loss_neutral'] == 'loss'


def test_trace_eval_attributes_missing_followup_modeling_to_layer3() -> None:
    trace_contract = {
        'planner_used': True,
        'planner_output': {'intent': 'food_estimation'},
        'normalizer_mode': 'off',
        'normalizer_diff': {'changed': False, 'normalized_text': 'buffet plate'},
        'template_match': {'blocked': False},
        'rescue_applied': {'rescue_layer': None},
        'db_hit_type': 'none',
        'followup_decision': 'should_ask',
    }
    quality_signals = {
        'missing_required_checks': [],
        'missing_top_uncertainty_drivers': True,
        'missing_driver_followups': [],
        'missing_expected_drivers': [],
        'failure_family': None,
    }

    verdict = evaluate_trace_contract(
        trace_contract,
        quality_signals,
        best_answer_source='initial',
        retry_triggered=False,
    )

    assert verdict['failed_layer'] == 'layer3_primary_llm'
    assert verdict['win_loss_neutral'] == 'loss'


def test_trace_eval_attributes_clarify_before_estimate_violation_to_layer3() -> None:
    trace_contract = {
        'planner_used': False,
        'planner_output': {'intent': 'food_estimation'},
        'normalizer_mode': 'planner_off_fallback',
        'normalizer_diff': {'changed': False, 'normalized_text': 'shared meal'},
        'template_match': {'blocked': False},
        'rescue_applied': {'rescue_layer': None},
        'followup_policy_decision': 'clarify_before_estimate',
        'final_answer_summary': {'decision': 'DIRECT_ANSWER', 'estimated_kcal': 600},
        'db_hit_type': 'none',
        'followup_decision': 'must_ask',
    }
    quality_signals = {
        'missing_required_checks': [],
        'missing_top_uncertainty_drivers': False,
        'missing_driver_followups': [],
        'missing_expected_drivers': [],
        'failure_family': None,
    }

    verdict = evaluate_trace_contract(
        trace_contract,
        quality_signals,
        best_answer_source='initial',
        retry_triggered=False,
    )

    assert verdict['failed_layer'] == 'layer3_primary_llm'
    assert 'clarification before estimation' in verdict['why']


def test_trace_eval_marks_successful_clarify_before_estimate_as_win() -> None:
    trace_contract = {
        'planner_used': False,
        'planner_output': {'intent': 'food_estimation'},
        'normalizer_mode': 'planner_off_fallback',
        'normalizer_diff': {'changed': False, 'normalized_text': 'shared meal'},
        'template_match': {'blocked': False},
        'rescue_applied': {'rescue_layer': None},
        'followup_policy_decision': 'clarify_before_estimate',
        'final_answer_summary': {'decision': 'ASK_USER', 'estimated_kcal': 0},
        'db_hit_type': 'none',
        'followup_decision': 'must_ask',
    }
    quality_signals = {
        'missing_required_checks': [],
        'missing_top_uncertainty_drivers': False,
        'missing_driver_followups': [],
        'missing_expected_drivers': [],
        'failure_family': 'heuristic_macro_distortion',
    }

    verdict = evaluate_trace_contract(
        trace_contract,
        quality_signals,
        best_answer_source='initial',
        retry_triggered=False,
    )

    assert verdict['failed_layer'] is None
    assert verdict['win_loss_neutral'] == 'win'
    assert verdict['improved_dimension'] == 'followup_correctness'


def test_trace_eval_attributes_grounding_contradiction_to_grounding_layer() -> None:
    trace_contract = {
        'planner_used': False,
        'planner_output': {'intent': 'food_estimation'},
        'normalizer_mode': 'planner_off_fallback',
        'normalizer_diff': {'changed': False, 'normalized_text': 'brand drink'},
        'template_match': {'blocked': False},
        'rescue_applied': {'rescue_layer': None},
        'followup_policy_decision': 'estimate_with_targeted_followup',
        'final_answer_summary': {'decision': 'DIRECT_ANSWER', 'estimated_kcal': 420},
        'grounding_contradiction': True,
        'db_hit_type': 'none',
        'followup_decision': 'must_ask',
    }
    quality_signals = {
        'missing_required_checks': [],
        'missing_top_uncertainty_drivers': False,
        'missing_driver_followups': [],
        'missing_expected_drivers': [],
        'failure_family': None,
    }

    verdict = evaluate_trace_contract(
        trace_contract,
        quality_signals,
        best_answer_source='retry',
        retry_triggered=True,
    )

    assert verdict['failed_layer'] == 'grounding'
    assert verdict['win_loss_neutral'] == 'loss'


def test_trace_eval_marks_high_confidence_exact_truth_as_win_even_with_followup_gaps() -> None:
    trace_contract = {
        'planner_used': False,
        'planner_output': {'intent': 'food_estimation'},
        'normalizer_mode': 'planner_off_fallback',
        'normalizer_diff': {'changed': False, 'normalized_text': 'brand drink exact hit'},
        'template_match': {'blocked': False},
        'rescue_applied': {'rescue_layer': None},
        'followup_policy_decision': None,
        'final_answer_summary': {'decision': 'DIRECT_ANSWER', 'estimated_kcal': 395},
        'grounding_contradiction': False,
        'db_hit_type': 'exact_truth',
        'match_confidence': 'high',
        'match_path': 'brand_plus_alias_partial',
        'followup_decision': 'not_needed',
    }
    quality_signals = {
        'missing_required_checks': [],
        'missing_top_uncertainty_drivers': False,
        'missing_driver_followups': ['product_variant'],
        'missing_expected_drivers': ['add_on_customization'],
        'failure_family': None,
    }

    verdict = evaluate_trace_contract(
        trace_contract,
        quality_signals,
        best_answer_source='with_local_knowledge',
        retry_triggered=False,
    )

    assert verdict['failed_layer'] is None
    assert verdict['win_loss_neutral'] == 'win'
    assert verdict['improved_dimension'] == 'exact_truth_correctness'
