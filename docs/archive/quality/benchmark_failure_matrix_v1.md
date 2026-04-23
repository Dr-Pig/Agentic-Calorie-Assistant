# Benchmark Failure Matrix V1

Source run:
- `.logs/benchmark_v1_builderspace_20260407_050656.json`

Current summary:
- total: 18
- passed: 10
- failed: 8
- answer_passed: 16
- route_passed: 10

Principle:
- This matrix groups failures by generalized behavior gap, not by case-specific patch target.
- Allowed fix categories remain:
  - LLM prompt / handoff improvement
  - evidence representation / attestation improvement
  - search loop / extractor / observer loop improvement
- Disallowed:
  - case-id branching
  - brand hardcoding for single cases
  - deterministic final posture override

## Family A: Exact Evidence Present, But Model Downgrades To Heuristic

Symptoms:
- `db_hit_type=exact_truth`
- decision already allows nutrition resolution
- nutrition still returns `heuristic_fallback` instead of exact or anchored
- usually adds a follow-up about flavor / brand / variant

Cases:
- `case_001` `星巴克冰那堤大杯`
- `case_002` `星巴克冰那堤`
- `case_004` `麥香雞`

Observed pattern:
- The model sees exact candidates but still treats sibling variants as blocking ambiguity.
- For Starbucks latte, flavored siblings dominate the model's uncertainty despite a plain/default candidate being present.
- For `麥香雞`, multiple exact candidates across brands cause fallback instead of selecting the most plausible same-item interpretation.

Desired behavior:
- If a same-item exact candidate exists and flavored/customized siblings are only optional variants, prefer exact or anchored posture instead of heuristic.
- Follow-up should not be blocking by default when a useful answer is already supported by exact evidence.

Likely fix surface:
- nutrition prompt
- exact-candidate fact packaging
- possibly exact retrieval identity facts, but not deterministic final override

## Family B: Brand / Chain Exact Gap Still Falls Back To Heuristic

Symptoms:
- branded restaurant item
- no usable exact local truth
- route lands on heuristic instead of stronger evidence recovery or more grounded anchored answer

Cases:
- `case_007` `吉野家大碗牛丼`

Observed pattern:
- current run returned `heuristic_fallback`
- no search was triggered
- estimate quality is usable, but benchmark expects exact lookup posture for this case

Desired behavior:
- if branded chain signal exists and local exact is missing, decision/search loop should more aggressively try official evidence recovery
- if exact cannot be recovered, remain conservative, but this benchmark case suggests stronger external grounding should be reachable

Likely fix surface:
- decision prompt
- search observer loop trigger policy
- search query refinement
- evidence extractor

## Family C: Generic Drink Class Posture Not Yet Aligned

Symptoms:
- generic drink class should stay non-exact
- tea-shop prior should beat bottled drink priors
- customized generic drink should usually be anchored, not low bottled exact or too-low estimate

Cases:
- `case_010` `珍珠奶茶`
- `case_011` `珍珠奶茶半糖去冰`

Observed pattern:
- `case_010`: posture is still `heuristic_fallback`; benchmark expects `unknown` exactness and estimate-with-followup posture
- `case_011`: posture is `anchored_component`, which is directionally right, but kcal center is too low and follow-up is unnecessary

Desired behavior:
- plain `珍珠奶茶` should use tea-shop class prior, not bottled packaged values
- `珍珠奶茶半糖去冰` should produce direct anchored estimate with no follow-up unless remaining size uncertainty materially changes the answer

Likely fix surface:
- nutrition prompt
- drink evidence packaging facts
- class prior quality

## Family D: Anchored Estimate Still Over-Asks

Symptoms:
- estimate itself is acceptable
- route fails only because follow-up is still present

Cases:
- `case_015` `鹹酥雞有雞排甜不辣四季豆米血`

Observed pattern:
- estimate is close enough
- posture is `anchored_component`
- follow-up remains present even though the current answer is already useful

Desired behavior:
- multi-item fried-food lists should give the estimate first
- follow-up should be omitted unless it materially changes the answer enough to make the current estimate misleading

Likely fix surface:
- nutrition prompt
- final response follow-up restraint

## Family E: High-Variance Dish Should Stay Non-Exact, But Follow-Up Strategy Still Needs Work

Symptoms:
- no exact truth available
- model should stay heuristic/anchored and preserve uncertainty
- current answer may still over-ask or use the wrong posture details

Cases:
- `case_018` `鷹流拉麵2929豚骨拉麵`

Observed pattern:
- latest run no longer overclaims exact, which is an improvement
- but follow-up still remains, so action posture misses benchmark expectation

Desired behavior:
- high-variance ramen should usually return direct estimate with uncertainty, not a blocking or explicit follow-up by default
- keep broth / extra noodle uncertainty inside explanation unless clarification is truly necessary

Likely fix surface:
- nutrition prompt
- final response follow-up restraint

## Per-Case Snapshot

| Case | Family | Current | Expected Gap |
| --- | --- | --- | --- |
| `case_001` | A | heuristic + follow-up | should be exact/high/no follow-up |
| `case_002` | A | heuristic + follow-up | should be estimate-with-followup or ask-followup-only, not heuristic downgrade |
| `case_004` | A | heuristic + follow-up | should be exact/high |
| `case_007` | B | heuristic/no-search | should recover stronger branded evidence |
| `case_010` | C | heuristic + follow-up | should be generic drink unknown posture with stronger class prior |
| `case_011` | C | anchored + follow-up + low kcal | should be anchored direct estimate, higher kcal center |
| `case_015` | D | anchored + follow-up | should be anchored direct estimate without follow-up |
| `case_018` | E | heuristic + follow-up | should be heuristic direct estimate without follow-up |

## Next Optimization Order

1. Family A
2. Family C
3. Family D + E
4. Family B

Reason:
- Family A and C account for the biggest posture mismatch concentration.
- Family D and E are mostly follow-up restraint.
- Family B likely needs search / external grounding work and is structurally heavier.
