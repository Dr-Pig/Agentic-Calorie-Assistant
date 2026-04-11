# Runtime Experiment Checklist

## 1. Purpose

Use this checklist when tuning:

- pass count
- pass split
- `decision_mode`
- LLM vs deterministic boundaries
- collapse vs expanded runtime shape

This document operationalizes the posture defined in:

- [L6E LLM Pass Design Policy Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md)
- [L5A Eval Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5A_EVAL_SPEC.md)

The default posture is:

- `LLM-first with deterministic carve-outs`

This means:

- ambiguous interpretation should usually be allowed to stay LLM-backed first
- explicit formula, threshold, boolean gate, legality, and guardrail truth should be carved out as deterministic

## 2. Before You Run Any Experiment

Confirm all of the following:

- the target domain is named explicitly
- the current canonical graph is written down
- the candidate variant is written down
- the `decision_mode` of each changed step is written down
- the expected reason for improvement is written down
- the affected success metrics are written down

Do not run "vibe-based" graph changes.

Every experiment should start from:

- current graph
- one collapsed or expanded variant
- one explicit hypothesis

## 3. Experiment Definition Template

Record these fields before implementation or eval:

- `domain`
- `current_graph`
- `candidate_graph`
- `changed_steps`
- `decision_mode_changes`
- `why_not_deterministic`
- `candidate_for_future_determinization`
- `candidate_for_future_collapse`
- `expected_quality_gain`
- `expected_cost_or_latency_change`

Recommended hypothesis format:

- `If we change <current_graph/step> to <candidate_graph/step>, then <metric> should improve because <reason>.`

## 4. Variant Types To Compare

For each major domain, compare only a small number of meaningful variants.

### 4.1 Intake

Recommended comparisons:

- canonical 4-stage graph
- boundary-first collapsed variant
- lighter response variant

Do not compare variants that merge boundary resolution into nutrition truth.

### 4.2 Recommendation

Recommended comparisons:

- canonical 3-node graph
- 2-node collapsed graph when candidate pool is already retrieved
- expanded 4-pass graph when candidate generation truly needs separate LLM synthesis

### 4.3 Calibration Proposal

Recommended comparisons:

- canonical `2-3 node` graph
- `deterministic gate -> proposal response`
- expanded 4-pass decomposition only when option shaping and ranking genuinely separate

### 4.4 Rescue

Recommended comparisons:

- canonical `2-3 node` graph
- 2-node deterministic-first rescue
- expanded 4-pass decomposition only when option shaping needs separate reasoning

## 5. What Must Stay Deterministic

Do not delegate these to LLM truth decisions:

- formulas
- numeric thresholds
- boolean gates
- legality checks
- safety floor resolution
- guardrail math
- rescue viability math
- proposal eligibility truth

If any candidate variant moves one of these into an LLM step, the variant should fail review unless the spec itself changes first.

## 6. What Is Allowed To Stay LLM-Backed

These are valid LLM-backed candidates:

- semantic interpretation
- boundary disambiguation
- incomplete-evidence estimation
- soft tradeoff ranking between already-legal options
- user-facing explanation
- proposal framing
- response phrasing

If a step is still gray-zone, keep it LLM-backed first and mark:

- `candidate_for_future_determinization: true`

## 7. Minimum Metrics For Comparison

Every runtime experiment should compare:

- correctness
- consistency / variance
- usefulness
- user friction
- latency
- token cost
- safety outcome

Domain-specific additions:

- intake: meal linking accuracy, correction handling, kcal usefulness
- recommendation: candidate relevance, budget fit, preference fit
- calibration: gate correctness, proposal appropriateness
- rescue: rescue appropriateness, horizon quality, escalation timing

## 8. Trace Requirements

Each evaluated run should emit enough trace to reconstruct:

- chosen graph
- chosen steps
- `decision_mode` per changed step
- deterministic inputs used
- fallback usage
- refusal / abstain conditions
- final outcome

At minimum, experiments should log:

- `current_graph`
- `candidate_graph`
- `step_name`
- `decision_mode`
- `decision_reason`
- `fallback_used`
- `quality_outcome`
- `latency_ms`
- `token_cost_estimate`

## 9. Decision Rules

Prefer collapse when:

- quality is flat or better
- latency or cost improves meaningfully
- observability remains sufficient

Prefer expanded mode when:

- it clearly improves correctness or stability
- the additional node has a distinct responsibility
- the gain is repeatable across cases, not only one anecdote

Prefer deterministic carve-out when:

- the step has one correct answer
- the LLM introduces variance on a truth decision
- the rule can be expressed clearly as formula, threshold, or legality gate

Keep LLM-backed when:

- the step depends on ambiguity, context, or incomplete evidence
- deterministic formalization reduces generic understanding
- the deterministic version only wins on toy cases

## 10. Stop / Adopt Criteria

Adopt a new graph or split only if:

- it beats or matches the current graph on correctness
- it does not regress safety
- its cost / latency tradeoff is acceptable
- the win reproduces across a representative case set

Do not adopt a variant when:

- it only improves one anecdotal founder case
- it wins on style preference but loses on measured usefulness
- it shifts deterministic truth into hidden LLM reasoning
- it overfits by reducing generic interpretation ability

## 11. Run Sheet

For each experiment, complete this checklist:

- write the current graph
- write the candidate graph
- write the changed step boundaries
- label each changed step with `decision_mode`
- mark deterministic carve-outs explicitly
- define the expected win
- run the comparison on a representative case set
- review correctness, variance, latency, token cost, and safety
- record whether the candidate should be:
  - adopted
  - rejected
  - kept as optional expanded mode
  - kept as future determinization candidate

## 12. Output Summary Template

At the end of an experiment, produce a short conclusion in this shape:

- `domain:`
- `current_graph:`
- `candidate_graph:`
- `result: adopt | reject | keep-optional`
- `quality_delta:`
- `latency_delta:`
- `token_delta:`
- `safety_delta:`
- `decision:`
- `follow_up:`
