# Re-plan Log

> [!NOTE]
> This log records reality deviations and phase corrections. If a replan alters the capability dependency order, the change MUST be propagated to **[`WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)**.

## Purpose

This log records implementation reality shifts that require the next-step plan to be corrected.

It should be appended over time instead of rewritten.

## 2026-04-17 — Whole-Product Suite-Governance Correction

### Trigger

- semantic-routing benchmark work exposed that the repo still lacked an explicit whole-product suite-governance layer tying `L5A` eval mechanics, `L5B` benchmark buckets, existing benchmark fixtures, and existing test/runner assets into one taxonomy

### What The Planning Reality Became

- official benchmark truth cannot be grown slice by slice without a whole-product suite-governance layer
- semantic-routing provisional vs official split was a useful local fix, but it surfaced a repo-wide need for:
  - authority tiers
  - suite inventory
  - migration mapping
  - promotion flow
- the next bounded step is not more router-first case expansion; it is establishing suite-governance truth and mapping existing assets into it

### Assumptions That Expired

- "L5A and L5B are enough by themselves to govern benchmark inventory"
- "official router/boundary benchmark work can proceed safely before whole-product suite taxonomy is explicit"
- "existing tests and benchmark fixtures can stay implicitly classified"

### Next-Phase Corrections

- add an explicit suite-governance layer on top of `L5A` / `L5B`
- create a first migration mapping table for benchmarks, tests, registries, and runners
- keep semantic-routing artifacts in their provisional/official lanes, but stop treating them as the whole benchmark backbone
- promote the first approved intake/rescue candidate batches into workflow-specific official canonical packs once review decisions exist
- derive workflow-specific executable action-pack contracts from approved official utterance packs without upgrading those derived artifacts into new product-truth sources
- define suite archetypes so the utterance-governed tri-layer pattern is only used where official utterance truth and executable runtime input genuinely diverge
- shrink the human gate to high-impact-only, so non-semantic official follow-through defaults to autonomous execution and worker-worthy delegation instead of planner-local stoppage

## 2026-04-18 — `2.7d` Autonomous Follow-Through Wave Landed

- converted the new suite-governance layer into agent-runnable surfaces instead of stopping at docs-only governance
- added first `agent_allowed` official capability/service packs for retrieval candidate selection, context-packing sufficiency, and bounded-repair gate behavior
- added benchmark artifact templates plus a scaffolding helper so future suite expansion does not require hand-built JSON each time
- activated runnable executable workflow smoke lanes for rescue and intake, with metadata-discoverable runner/fixture registration
- added suite-wave orchestration so the current executable smoke lanes can be planned and executed by `suite_id` / `workflow_family` filters rather than manual script memory
- kept the remaining human gate limited to new architecture, new cross-workflow product semantics, and new utterance-governed official truth

## 2026-04-18 — `general_chat` Runnable Official Lane Landed

- implemented the `general_chat` 1-pass runtime surface as a deterministic-read, no-mutation answer lane for budget and goal queries plus open-workflow handoff
- promoted the first `general_chat` official canonical pack covering budget query, goal query, and open-workflow boundary truth
- added a runnable `general_chat` official-pack runner and registered it in suite-wave orchestration so `workflow_family=general_chat` can execute as a real official lane instead of staying fixture-only
- kept the lane bounded to official truth already approved in-product: workflow family, disposition, workflow effect, and required read surfaces

## 2026-04-18 — Workflow Graph / Official Truth v1 Locked

- locked the v1 canonical graph summary for `general_chat`, `intake`, `rescue`, `recommendation`, `calibration`, and `body_observation`
- locked the repo-wide rule that official utterance truth is two-layered: Layer A global routing truth plus Layer B workflow-specific decision truth
- clarified that `recommendation v1` remains non-mutating and does not create recommendation intent state
- clarified that `calibration proposal response surface` belongs to `calibration`, not `recommendation`

## 2026-04-16 — Semantic-Routing Benchmark Authority Split

### Trigger

- `2.7d` prompt/state-pack hardening had driven the legacy 15-case founder-fit pack to `15/15`, but product review clarified that this pack must not be treated as canonical benchmark truth.

### What The Planning Reality Became

- the legacy founder-fit pack is now only a provisional smoke pack for runner / harness / plumbing validation
- official semantic-routing benchmark truth must live in a separate canonical pack
- candidate cases must be reviewed and approved by the user per case before they can be promoted into the official canonical pack

### Assumptions That Expired

- "improving the old 15-case founder-fit pack pass rate is equivalent to validating product routing truth"
- "semantic-routing benchmark artifacts can stay in one authority lane"

### Next-Phase Corrections

- keep provisional smoke and official canonical benchmark artifacts separate
- keep official packs limited to primary oracle fields and exclude ambiguity cases
- use a candidate review queue as the only promotion path into official canonical benchmark truth

## 2026-04-11 — Canonical Core / Intake Transition

### Trigger

- typed canonical bridge was introduced into a repo that still carries legacy meal-log persistence and a heavy text intake entrypoint

### What The Code Actually Became

- canonical persistence is already real, not just a planned future layer
- `CommitRequestCandidate` is now the meaningful bridge between intake runtime and canonical writes
- stage trace events already have a typed runtime path
- `text_meal.py` remains active, but no longer owns all persistence/trace details

### Assumptions That Expired

- "Phase 1 is only persistence, Phase 2 is where typed runtime starts"
- "legacy meal-log persistence can keep its old canonical bridge signature"
- "execution planning can continue without recording reality drift in active plans"

### Boundary Pressure

- `app/usecases/text_meal.py` is still too large for a stable long-term entrypoint
- `app/schemas.py` is accumulating legacy and new typed contracts in one place
- future tasks must prefer extracting services over adding more orchestration to existing fat files

### Next-Phase Corrections

- treat typed contract alignment as part of the current execution phase, not a later cleanup
- require active execution plans to state reality drift explicitly
- do not start recommendation/calibration/rescue implementation until Phase B intake hardening is explicitly closed

## 2026-04-11 — Dependency/Context Ordering Correction

### Trigger

- the original execution grouping was too capability-centric and hid the true workflow dependency order

### What The Planning Reality Became

- build ordering must be driven by workflow dependencies and context density, not only by subsystem labels
- recommendation is not an early phase target; memory-aware recommendation belongs after stable intake, today/read models, rescue, calibration, and memory deepening
- proactive work must stay last

### Assumptions That Expired

- "the three execution planning artifacts can act as ordering truth on their own"
- "recommendation should be early just because it is a major product capability"

### Next-Phase Corrections

- treat [`docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md) as the canonical ordering authority
- keep the three execution planning artifacts, but only as execution-control tools
- make upcoming active work target `Today UI / Read Models` and `Weight / Body Observation` before recommendation

### Follow-up Checks

- confirm the next execution plan only contains micro-detail for the current and next phase
- confirm future active plans include re-plan metadata fields from the protocol

## 2026-04-11 — Operating Layer Activation

### Trigger

- planning governance existed, but real checked-in task and handoff artifacts did not yet exist

### What The Execution Reality Became

- execution operating layer is only genuinely usable once the repo contains at least:
  - active task artifacts
  - a structured handoff example
  - a current execution plan that points to concrete `slice_id` values
- execution plans now have to be read together with checked-in task artifacts, not by themselves

### Assumptions That Expired

- "protocol documents alone are enough to make multi-agent execution ready"
- "the current execution plan can stay at workflow-only granularity"

### Next-Phase Corrections

- treat `slice_id` and `task_id` as the active execution units, not only broad workflow labels
- require future current-plan updates to point to active tasks when work has been checked in
- prefer structured handoff updates over free-form status summaries

## 2026-04-11 — Rescue Deterministic Overlay Foundation

### Trigger

- the workflow order reached `2.5a-rescue-deterministic-overlay` after Today and Weight low-fi surfaces passed the first integrated manual check

### What The Code Actually Became

- rescue math now exists as a deterministic application-layer helper rather than as implicit ledger mutations
- overlay writes still go through canonical ledger entries and ledger recompute
- the implementation stopped short of rescue proposal generation and rescue UI, keeping the slice bounded

### Assumptions That Expired

- "rescue can infer `safety_floor(user)` immediately from canonical state"

### Boundary Pressure

- `L3M` specifies sex-based safety floors, but current canonical state does not yet expose a stable deterministic field for that lookup

### Next-Phase Corrections

- keep `safety_floor_kcal` explicit in v1 deterministic rescue math
- do not hide this gap inside a guessed fallback
- decide the canonical source for `safety_floor(user)` before rescue proposal formation or rescue UI work

## 2026-04-11 — Canonical Safety Floor Source

### Trigger

- rescue deterministic math exposed that `L3M` requires `safety_floor(user)` while current canonical state did not yet expose a stable scalar source

### What The Planning Reality Became

- the canonical deterministic source should be `active BodyPlan.safety_floor_kcal`
- runtime should prefer a resolved scalar over reconstructing user sex/gender inside guardrail math

### Assumptions That Expired

- "rescue or calibration runtime can safely infer floor from implicit user attributes later"

### Next-Phase Corrections

- add `safety_floor_kcal` to canonical BodyPlan state
- let onboarding / accepted plan setup populate that field
- keep rescue math explicit until read models and setup flows can supply the field reliably

## 2026-04-11 — Intake Correction Task Re-scope After Harness Hardening

### Trigger

- repo governance now protects `app/usecases/text_meal.py`, freezes growth in selected assembly files, and formalizes file-placement plus layer-dependency rules

### What The Planning Reality Became

- `TASK-2026-04-11-001-INTAKE-CORRECTION-FOUNDATION` can no longer treat `app/usecases/text_meal.py` as a normal implementation target
- historical correction work must land in `app/application/*`, `app/infrastructure/*`, and narrow `text_meal_*` service/support modules
- freeze-growth files now require explicit extraction-aware justification before they can be touched

### Assumptions That Expired

- "historical correction can safely keep using the old wide write scope"
- "protected legacy files are acceptable default landing zones as long as the task is bounded"

### Next-Phase Corrections

- re-scope worker write areas before any new historical-correction implementation resumes
- require layer-integrity and fat-file checks as part of this task's completion bar
- prefer narrower service/support modules over protected legacy entrypoints

## 2026-04-11 — Clarify-Required Lane Hardening

### Trigger

- `2.1c-clarify-required-lane` needed a deterministic guarantee that blocking clarify cannot drift into a proceedable commit path when provider output is internally contradictory

### What The Code Actually Became

- decision normalization now forces `can_proceed_without_clarify=false` whenever `clarify_is_blocking=true`
- clarify-required intake now has a direct regression proving the system stays on the clarify route and does not write canonical meal truth
- clarify/follow-up shaping was tightened without widening the slice into rescue, calibration, recommendation, or UI concerns

### Assumptions That Expired

- "prompt guidance alone is enough to keep blocking clarify behavior coherent"
- "no-commit clarify behavior is sufficiently covered without a direct regression"

### Next-Phase Corrections

- treat `2.1d-cannot-estimate-lane` as the next abstain-path hardening target
- keep clarify and cannot-estimate behavior separated from web-search fallback ownership
- prefer bounded lane-level worker tasks over reopening intake-core-wide refactors

## 2026-04-11 — Spec Boundary Clarifications

### Trigger

- architecture review identified three places where future agents could over-interpret the specs and widen scope in unsafe ways

### What Was Clarified

- `2.2` correction scope was narrowed to explicit / bounded correction targets; fuzzy cross-day or cross-week recall was pushed to later memory / retrieval work
- `2.5` rescue dependency was clarified to read canonical ledger truth via stable read-side surfaces, not UI route or presentation behavior
- recommendation cold-start behavior was made explicit: empty or sparse `PreferenceProfileSummary` is valid and must degrade to safe fallback sources instead of failing closed

### Why It Matters

- prevents intake correction from absorbing early memory-search complexity
- prevents rescue implementation from coupling to Today UI behavior
- prevents recommendation runtime from treating missing memory as an error condition

### Snapshot Record

- `artifacts/docs-snapshots/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md_20260411_170502/`
- `artifacts/docs-snapshots/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md_20260411_170502/`
- `artifacts/docs-snapshots/WORKFLOW_SLICE_REGISTRY.md_20260411_170502/`

## 2026-04-11 — Current Plan Memory Numbering Alignment

### Trigger

- `CURRENT_EXECUTION_PLAN.md` still labeled memory / retrieval next-work as `2.6`, which drifted from the canonical ordering spec where memory / retrieval is `2.7`

### What Was Clarified

## 2026-04-14 — Turn-2 Boundary/Persistence Continuity Re-scope

### Trigger

- the 9-case positive-path turn-2 replay pack showed that several turn-2 runs already resolved `meal_boundary=continue_active_meal` but still committed as new meals because persistence keyed parent attachment off `planner_intent`

### What The Runtime Reality Became

- same-intake recognition and persistence attachment are currently coupled too tightly to intent labels
- turn-2 follow-up continuity should be treated as a boundary/state contract first, not as a byproduct of `clarification` or `modification` intent names
- replay density is now sufficient; the next bounded step is continuity hardening, not more pack expansion

### Assumptions That Expired

- "if planner intent stays `food_estimation`, persistence should default to a new meal even when boundary already says continue the active meal"
- "turn-2 replay pack expansion is still the best-next slice after the first dense replay run"

### Next-Phase Corrections

- promote boundary-first same-intake continuity to the active `2.2j` slice
- allow `still_unresolved_followup` to remain attached on the same parent meal when turn 2 is clearly answering the pending follow-up
- defer further pack authoring cleanup until the boundary-to-persistence contract is fixed

## 2026-04-14 — Turn-2 Pack Tightening After Continuity Hardening

### Trigger

- `2.2j` fixed the primary runtime continuity bug; replay reruns now show the remaining misses are split between closure-threshold cases and turn-2 authoring ambiguity

### What The Planning Reality Became

- the next bounded step is no longer runtime continuity
- the official 9-case turn-2 pack now needs explicit closure-complete authoring so live replay evidence tests workflow truth instead of shorthand follow-up answers
- fixture risk should be treated as a pack-authoring problem unless bytes or registry checks prove actual encoding corruption

### Assumptions That Expired

- "the existing turn-2 phrasings are already explicit enough for positive-path replay"
- "every replay miss after 2.2j must still be a runtime bug"

### Next-Phase Corrections

- promote `2.2k-turn2-closure-complete-pack-tightening` as the active slice
- rewrite official turn-2 inputs to be explicit answer-shaped completions/refinements
- rerun the full 9-case live replay pack before any new taxonomy or threshold work

## 2026-04-14 — 2.2k Replay Pack Closeout

### Trigger

- the official 9-case turn-2 pack was tightened into closure-complete answers and rerun end-to-end with fresh run-scoped users

### What The Execution Reality Became

- the remaining replay ambiguity was not a deeper context-architecture gap
- part of the observed instability came from two narrower issues:
  - turn-2 inputs that were still too shorthand to count as positive-path closure answers
  - replay reruns reusing stable per-case user ids, which contaminated evidence with prior unresolved state

### What Was Corrected

- official turn-2 replay inputs were rewritten into clearer closure-complete responses
- the replay runner now isolates each full run with a fresh run-scoped user id while preserving turn1/turn2 continuity inside the run
- the official 9-case live rerun now passes cleanly

### Next-Phase Corrections

- treat the reopened `2.2` branch as complete enough for the current wave
- return execution selection to the rescue human gate unless the user explicitly reopens another branch

## 2026-04-15 — Rescue Branch Reopened For 2.5c Formalization

### Trigger

- the user explicitly selected the rescue branch and asked to analyze and formalize `2.5c rescue option shaping`

### What The Planning Reality Became

- `2.5c` was referenced in the execution clock, but it was not yet a formal registry slice
- the missing work is not rescue math or proposal-artifact structure; it is the bounded non-user-facing layer that gives rescue families stable meaning, ranking, and activation timing before any response surface exists

### Assumptions That Expired

- "`2.5c` is already formalized just because the current plan names it"
- "the rescue human gate blocks all rescue work equally"

### Next-Phase Corrections

- formalize `2.5c-rescue-option-shaping` as the active rescue slice
- keep `2.5c` non-user-facing and deterministic-first / typed-artifact-first
- defer rescue response wording, UI surface, quick actions, and accept-side writeback to later `2.5d`

- `Next Workflow Focus` now refers to `2.7 Memory / Retrieval Deepening`
- queued `context-selector` placeholder was renumbered to `2.7a-context-selector`
- the correction is numbering-only and does not imply that a new formal slice registry entry has already been authored

### Why It Matters

- prevents future agents from planning memory work under the calibration number
- keeps active execution wording aligned with canonical ordering truth

### Snapshot Record

- `artifacts/docs-snapshots/CURRENT_EXECUTION_PLAN.md_20260411_170939/`

## 2026-04-11 — Fat-File Gate Hardening

### Trigger

- the repo already has known oversized boundary files, and soft warnings alone are no longer enough to stop future agents from adding more responsibility to them

### What The Planning Reality Became

- `app/usecases/text_meal.py`, `app/schemas.py`, and `app/routes.py` are now treated as protected files
- implementation planning protocol now defines a protected fat-file gate instead of only a review reminder

## 2026-04-11 — Cross-Domain LLM Pass Governance Alignment

### Trigger

- multiple runtime specs had drifted into a de facto "every major capability domain uses 4-pass" pattern
- this created a governance gap where agents could overgeneralize intake's 4-pass structure into recommendation, calibration proposal, and rescue

### What Was Clarified

- `graph-first, role-second` is now a canonical rule
- `L6E_LLM_PASS_DESIGN_POLICY_SPEC.md` was added as the cross-domain pass-design governance spec
- `L6C` was narrowed so it now maps roles for LLM-backed nodes, rather than implicitly defining fixed pass count for every domain
- `L3.2`, `L3.3B`, and `L3.4` now distinguish `canonical default graph` from `expanded mode`
- `L3.1` keeps intake's boundary-first guard and explicitly forbids collapsing boundary resolution into a single black-box nutrition pass

### Assumptions That Expired

## 2026-04-12 — `2.2d` Follow-Up Closure Validation Selection

### Trigger

- `2.2a` continuation and `2.2c` cross-midnight are already landed, but the repo still lacks an explicit validation wave for `ask_followup_only -> completion` and `estimate_with_followup -> refinement`

### What The Planning Reality Became

- the next missing mainline contract is backend two-turn follow-up closure, not more rescue or calibration foundation
- this wave should be validation-first and planner-local
- benchmark seeds should be pulled from:
  - `tests/fixtures/benchmark_test_set_v1.json`
  - `docs/quality/benchmark_test_set_v1.txt`
  - `docs/quality/benchmark_test_set_v2.txt`
- the right context-engineering boundary here is session-local pending follow-up continuity, not durable memory or retrieval deepening

### Assumptions That Expired

- "multi-turn validation can stay implicit inside continuation/cross-midnight regressions"
- "rescue semantics are the best next branch once 2.5b exists"
- "follow-up closure needs 2.7 memory/retrieval before it can be validated"

### Next-Phase Corrections

- formalize `2.2d-followup-closure-validation-foundation` as the current active slice
- author stateful benchmark cases for:
  - `ask_followup_only -> completion`
  - `estimate_with_followup -> refinement`
- run targeted backend closure regressions first
- only open `2.2e-followup-session-state-hardening` if the validation wave reveals a narrow deterministic gap

### Outcome

- `2.2d` landed as a validation-first wave
- the repo now has:
  - explicit follow-up closure seed inventory
  - two authored stateful multi-turn benchmark cases
  - targeted backend regressions for both closure contracts
- current deterministic checks did not require `2.2e`
- the next unresolved question is broader founder-fit validation density, not immediate session-state hardening

## 2026-04-13 — `2.2f` Founder-Fit Replay Pack Selection

### Trigger

- `2.2d` proved the backend two-turn closure contracts, but the project still needs a human-reviewable founder-fit replay pack before deciding whether the next increment should be more `2.2` validation or a return to `2.3`

### What The Planning Reality Became

- the next best increment is not more implementation by default
- it is a reviewable replay pack built from benchmark seeds plus a small number of founder-fit authored cases
- this should stay planner-local and review-first

### Next-Phase Corrections

- formalize `2.2f-founder-fit-multi-turn-replay-pack`
- recommend an initial pack size that is small enough for review but broad enough to cover both follow-up lanes plus boundary controls
- hand the pack to human review before asking for synthetic expansion from ChatGPT or further benchmark authoring

- "because role vocabulary exists, each domain should expose matching 4-pass structure"
- "recommendation, calibration proposal, and rescue should inherit intake's expanded pass decomposition as default truth"
- "`L6C` can safely act as both routing spec and pass-count authority"

### Why It Matters

- prevents future agents from pattern-matching 4-pass into domains that should be deterministic-first
- preserves intake's unique boundary-splitting responsibility without turning it into a cross-domain template
- gives future spec edits a canonical place to check pass-count, collapse, and deterministic-first policy before changing runtime flow

### Snapshot Record

- `artifacts/docs-snapshots/L6D_LLM_PASS_DESIGN_POLICY_SPEC.md_20260411_200135/`
- `artifacts/docs-snapshots/L6C_MODEL_ROUTING_PROVIDER_ABSTRACTION_SPEC.md_20260411_200135/`
- `artifacts/docs-snapshots/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md_20260411_200135/`
- `artifacts/docs-snapshots/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md_20260411_200136/`
- `artifacts/docs-snapshots/L3_3B_CALIBRATION_PROPOSAL_POLICY_RUNTIME_CONTRACT_SPEC.md_20260411_200136/`
- `artifacts/docs-snapshots/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md_20260411_200136/`
- `artifacts/docs-snapshots/index.md_20260411_200137/`
- `artifacts/docs-snapshots/CANONICAL_DOCS_MANIFEST.md_20260411_200137/`

## 2026-04-11 — Decision-Mode Annotation Alignment

### Trigger

- pass-count governance alone was still too coarse to protect the product from the two opposite failure modes:
  - over-determinizing ambiguous intake semantics
  - over-LLM-izing threshold gates and calibration / rescue math

### What Was Clarified

- cross-domain governance now includes an explicit `Decision Mode Rule`
- key runtime steps now distinguish `decision_mode` at the step level instead of relying only on domain-level labels
- intake keeps LLM-heavy semantic interpretation
- calibration truth, rescue viability, and proposal eligibility are now more explicitly documented as deterministic or deterministic-first

### Why It Matters

- prevents future agents from reading `LLM-first` as permission to move numeric gates into LLM passes
- prevents future agents from reading `deterministic-first` as permission to replace ambiguous intake understanding with if/else heuristics
- gives each major runtime step a local mode declaration that is harder to over-generalize

### Snapshot Record

- `artifacts/docs-snapshots/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md_20260411_203256/`
- `artifacts/docs-snapshots/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md_20260411_203256/`
- `artifacts/docs-snapshots/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md_20260411_203256/`
- `artifacts/docs-snapshots/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md_20260411_203257/`
- `artifacts/docs-snapshots/L3_3B_CALIBRATION_PROPOSAL_POLICY_RUNTIME_CONTRACT_SPEC.md_20260411_203257/`
- `artifacts/docs-snapshots/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md_20260411_203257/`

## 2026-04-13 — `2.2g` Post-Pass Override Cleanup

### Trigger

- accepted Golden V1 exposed one concrete runtime mismatch: generic `珍珠奶茶` drifted into `exact_item`
- architecture review confirmed that deterministic layers were still rewriting completed LLM posture fields after pass completion

### What The Planning Reality Became

- `poke` is not a Golden referee case; it moves to gray-zone / borderline
- the next best slice is not broader replay expansion yet
- first the runtime must remove deterministic post-pass posture overrides and keep generic drinks out of accidental exact finalization

### Next-Phase Corrections

- add a hard bootstrap/runtime rule forbidding deterministic post-pass overrides of completed LLM posture fields
- keep `soft avoid exact` for generic bubble tea as a bounded repair gate, not a direct overwrite
- rerun first-turn Golden audit after cleanup
- only then move into `2.2h` turn-2 hybrid replay

## 2026-04-14 — `2.2h` Turn-2 Hybrid Replay Foundation Built

### Trigger

- `2.2g` cleanup finished, and the next missing mainline asset was a reusable second-turn replay workflow that did not depend on full two-turn live reruns for every iteration

### What Landed

- a cleaned file-backed turn-2 replay pack with one `ask_followup_only -> completion` case and one `estimate_with_followup -> refinement` case
- runner artifacts now retain `request_id`, `turn_id`, full payload, `trace_contract`, `llm_traces`, and persistence decision
- replay summary now records same-intake attachment and expected lane/outcome fields
- targeted tests now lock the replay pack shape and summary contract

### What Did Not Change

- provider readiness remains the live-evidence gate
- `2.2h` foundation is built, but no fallback-only rerun should be treated as true LLM evidence

### Next-Phase Correction

- restore provider configuration
- rerun the `9`-case Golden single-turn live audit
- only then use the turn-2 replay foundation for real second-turn evaluation

## 2026-04-14 — `2.2` Live Evidence Closed; Read-Side Confidence Selected Next

### Trigger

- provider readiness was restored
- the official `9`-case Golden single-turn live audit passed with true provider usage
- both official `2.2h` turn-2 hybrid replay lanes passed with real evidence:
  - `ask_followup_only -> completion`
  - `estimate_with_followup -> refinement`

### What The Planning Reality Became

- `2.2` is now strong enough for current-wave domain advance
- the next bounded risk is no longer first-turn or second-turn intake behavior
- the next bounded risk is whether current-budget and today-facing read-side surfaces still reflect the newly confirmed multi-turn intake truth

### Assumptions That Expired

- "provider readiness is still blocking real `2.2` evidence"
- "`2.2h` remains the best-next slice even after live audit and replay evidence exist"
- "the next useful step after `2.2` evidence is more intake-core work by default"

### Next-Phase Corrections

- move the execution pointer from `2.2` to a narrow `2.3` confidence slice
- formalize `2.3c-read-side-confidence-follow-through`
- keep rescue semantics and later-domain work deferred until read-side confidence is reconfirmed

## 2026-04-14 — `2.3c` Read-Side Confidence Closed; Execution Stops At Rescue Gate

### Trigger

- the narrow `2.3c` regressions passed for:
  - unresolved turn-1 draft state staying out of current-budget/today
  - turn-2 completion surfacing the final active meal into current-budget/today

### What The Planning Reality Became

- the current wave's `2.2` and `2.3` confidence work is now complete enough
- the next legal product branch is still `2.5 Rescue`
- that branch remains intentionally paused at the existing human semantics gate

### Next-Phase Corrections

- stop active implementation here unless the user explicitly reopens rescue semantics or chooses another branch
- keep the current wave's evidence as the new baseline:
  - Golden single-turn live audit passed
  - turn-2 replay evidence passed
  - read-side confidence follow-through passed

## 2026-04-14 — User Reopened `2.2` For Turn-2 Replay Density Expansion

### Trigger

- after the initial `2.2h` and `2.3c` evidence closed, the user explicitly requested a next step focused on fixed turn-1 outputs and broader turn-2 planner attachment/refinement testing

### What The Planning Reality Became

- the next active slice is not rescue semantics
- it is a narrow planner-local `2.2` pack expansion using accepted Golden seeds and founder-fit follow-up cases to stress:
  - same-intake attachment
  - completion after ask-only turn 1
  - refinement after estimate-with-followup turn 1
  - no accidental duplicate meal creation

### Next-Phase Corrections

- formalize `2.2i-turn2-attachment-and-refinement-replay-pack`
- expand the file-backed turn-2 replay pack beyond the original two official cases
- keep this work inside replay fixtures, replay runner surfaces, and replay-pack validation only

## 2026-04-12 — Docs Bootstrap State-Machine Reorg

### Trigger

- bootstrap docs had become too flat and too redundant for planner-first execution
- `AGENTS.md`, `docs/index.md`, `docs/AGENT_LOADING_PATH.md`, and several root governance briefs were overlapping in purpose
- the desired runtime shape was a short planner path centered on `CURRENT_EXECUTION_PLAN.md`

### What Changed

- `AGENTS.md` now acts as the only bootstrap and points directly to the execution dashboard, slice registry, and ordering spec
- `docs/index.md` was compressed into a family-level human portal
- `docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md` was upgraded into the planner dashboard / execution clock
- root governance owner docs moved into `docs/governance/`
- merged owner docs were added:
  - `docs/governance/EXECUTION_OPERATING_MODEL.md`
  - `docs/governance/EXECUTION_SELECTION_POLICY.md`
  - `docs/governance/CHANGE_CONTROL_GUARDS.md`
- `docs/AGENT_LOADING_PATH.md` was archived and removed from the default bootstrap path
- `docs/exec-plans/active/MASTER_BUILD_MAP.md` was archived after its active-state role moved into the dashboard
- `docs/` root now retains only `index.md`

### Why It Matters

- the planner now has a short, obvious execution path:
  - `AGENTS.md -> CURRENT_EXECUTION_PLAN.md -> WORKFLOW_SLICE_REGISTRY.md -> ordering spec`
- governance material is still preserved, but no longer competes with active execution truth at bootstrap time
- archive, references, and snapshots remain available without polluting the default read path

### Editing Note

- `AGENTS.md`, `docs/index.md`, and `CURRENT_EXECUTION_PLAN.md` were finalized through same-path UTF-8-with-BOM overwrites after anchor-safe patching became unreliable during the reorg
- no delete-and-recreate was used for those files

### Snapshot Record

- `artifacts/docs-snapshots/AGENTS.md_20260412_130918/`
- `artifacts/docs-snapshots/index.md_20260412_130918/`
- `artifacts/docs-snapshots/CURRENT_EXECUTION_PLAN.md_20260412_130918/`
- `artifacts/docs-snapshots/SPEC_EDITING_PROTOCOL.md_20260412_130918/`
- `artifacts/docs-snapshots/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md_20260412_130918/`
- `artifacts/docs-snapshots/TASK_CHECKIN_PROTOCOL.md_20260412_130918/`
- `artifacts/docs-snapshots/HANDOFF_CONTRACT.md_20260412_130918/`
- `artifacts/docs-snapshots/ENCODING_POLICY.md_20260412_130918/`
- `artifacts/docs-snapshots/BUILD_FILE_PLACEMENT_RULES.md_20260412_130918/`

## 2026-04-12 — Deterministic Harness Wall Added

### Trigger

- markdown-heavy governance was intentionally reduced, but the repo still needed a stronger deterministic firewall against scope drift, dependency drift, test mutilation, truncation, and vague commit traceability

### What Changed

- added `scripts/check_git_diff_scope.py` for staged/range diff hard gates plus staged-python `ruff` support
- added `scripts/check_commit_format.py` for `commit-msg` and CI commit-contract validation
- added `scripts/check_runtime_boundaries.py` for focused runtime ownership boundary checks alongside the existing layer-integrity audit
- wired `pre-commit` to run diff scope, runtime boundaries, and staged `ruff`
- wired CI to run diff scope, commit format, runtime boundaries, and repo lint
- documented the active deterministic firewall in `docs/quality/HARNESS_EXECUTION_POLICY.md`

### Why It Matters

- the default harness wall now blocks the most common high-cost agent failures without restoring heavy task/handoff bureaucracy
- scope and commit checks operate on staged diff or commit/PR range, so they stay usable even when the overall repo history is large
- commit history now carries verification and drift intent explicitly instead of relying on handwritten task metadata

### Snapshot Record

- `artifacts/docs-snapshots/AGENTS.md_20260412_123500/`
- `artifacts/docs-snapshots/index.md_20260412_123500/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260412_123500/`
- `artifacts/docs-snapshots/pre-commit_20260412_123500/`
- `artifacts/docs-snapshots/ci.yml_20260412_123500/`
- `artifacts/docs-snapshots/install_git_hooks.ps1_20260412_123500/`
- `artifacts/docs-snapshots/requirements.txt_20260412_123500/`
- `artifacts/docs-snapshots/AGENTS.md_20260412_124800/`
- `artifacts/docs-snapshots/index.md_20260412_124800/`
- `artifacts/docs-snapshots/HARNESS_EXECUTION_POLICY.md_20260412_124800/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260412_124800/`
- `artifacts/docs-snapshots/pre-commit_20260412_124800/`
- `artifacts/docs-snapshots/commit-msg_20260412_124800/`
- `artifacts/docs-snapshots/ci.yml_20260412_124800/`
- `artifacts/docs-snapshots/install_git_hooks.ps1_20260412_124800/`
- `artifacts/docs-snapshots/check_git_diff_scope.py_20260412_124800/`
- `artifacts/docs-snapshots/check_commit_format.py_20260412_124800/`
- `artifacts/docs-snapshots/check_runtime_boundaries.py_20260412_124800/`
- `artifacts/docs-snapshots/requirements.txt_20260412_124800/`

## 2026-04-12 — Repo-Wide Ruff Debt Cleanup

### Trigger

- repo-wide `ruff` still had pre-existing `F401`, `F821`, and `F841` debt, which prevented upgrading from diff-scoped lint confidence to a genuinely clean repository baseline

### What Changed

- cleared the auto-fixable unused-import and unused-variable findings across `app/`, `scripts/`, and `tests/`
- fixed `app/application/context_assembly.py` as a contained bug fix by replacing the invalid `item.get("match_quality")` reference with `raw.get("match_quality")`
- added explicit `__all__` exports to `app/domain/__init__.py` and `app/observability/__init__.py` so package barrel modules remain intentional instead of lint debt
- updated `scripts/check_fat_files.ps1` to accept an empty governance-text collection without crashing the hook binder

### Why It Matters

- repo-wide `ruff check --select F401,F821,F841 app tests scripts` now has a clean baseline instead of relying on diff-only hygiene
- the freeze-growth touch on `app/application/context_assembly.py` is explicitly recorded as a contained bug fix instead of an undocumented growth event
- the fat-file gate now fails deterministically on policy violations instead of failing early on an empty-array binding error

## 2026-04-12 — Lean Governance Migration

### Trigger

- active governance remained stable but too quota-expensive
- default bootstrap still pulled agents into heavy pre-reading, task/handoff protocol overhead, and multi-agent framing that no longer matched the preferred `planner-local` operating mode

### What Changed

- `AGENTS.md` now points to a minimal bootstrap path and formalizes the execution-truth trio: git, harness output, and the minimal active execution board
- `docs/index.md` and `AGENTS.md` now mark task artifacts, handoffs, and role-model docs as optional or exception-path reads rather than default execution requirements
- `docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md` was reduced to a minimal operational board instead of a long historical narrative
- `docs/governance/TASK_CHECKIN_PROTOCOL.md` and `docs/governance/HANDOFF_CONTRACT.md` now define optional exception paths instead of default mandatory workflow artifacts
- `docs/governance/EXECUTION_SELECTION_POLICY.md` now defines `single-stream local planner` as the default loop shape, with delegation as an explicit exception
- `scripts/check_task_checkin_and_handoff.ps1` was downgraded to an advisory compatibility audit
- CI and pre-commit no longer treat task/handoff artifact validation as a default blocking gate

### Why It Matters

- execution visibility is preserved through a cheaper and more reliable trio: git diff or commit history, harness output, and a minimal active board
- agents no longer spend quota recreating information that version control and verification commands already provide
- optional governance docs remain available for real transfer or delegation scenarios without burdening every routine local slice

### Snapshot Record

- `artifacts/docs-snapshots/AGENT_LOADING_PATH.md_20260412_113200/`
- `artifacts/docs-snapshots/AGENTS.md_20260412_110500/`
- `artifacts/docs-snapshots/AGENTS.md_20260412_113200/`
- `artifacts/docs-snapshots/index.md_20260412_110500/`
- `artifacts/docs-snapshots/index.md_20260412_113200/`
- `artifacts/docs-snapshots/CURRENT_EXECUTION_PLAN.md_20260412_110500/`
- `artifacts/docs-snapshots/CURRENT_EXECUTION_PLAN.md_20260412_113200/`
- `artifacts/docs-snapshots/TASK_CHECKIN_PROTOCOL.md_20260412_110500/`
- `artifacts/docs-snapshots/TASK_CHECKIN_PROTOCOL.md_20260412_113200/`
- `artifacts/docs-snapshots/HANDOFF_CONTRACT.md_20260412_110500/`
- `artifacts/docs-snapshots/HANDOFF_CONTRACT.md_20260412_113200/`
- `artifacts/docs-snapshots/PLANNER_AUTONOMY_LOOP_POLICY.md_20260412_110500/`
- `artifacts/docs-snapshots/PLANNER_AUTONOMY_LOOP_POLICY.md_20260412_113200/`
- `artifacts/docs-snapshots/check_task_checkin_and_handoff.ps1_20260412_110500/`
- `artifacts/docs-snapshots/check_task_checkin_and_handoff.ps1_20260412_113200/`
- `artifacts/docs-snapshots/ci.yml_20260412_110500/`
- `artifacts/docs-snapshots/ci.yml_20260412_113200/`
- `artifacts/docs-snapshots/pre-commit_20260412_110500/`
- `artifacts/docs-snapshots/pre-commit_20260412_113200/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260412_113200/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260412_113450/`

## 2026-04-12 — Today-Surface Date-Aware Follow-Through

### Trigger

- current-budget read-model follow-through passed with the corrected local-date truth still intact
- the next execution risk moved from read-model truth to whether the Today surface still renders that truth without drift

### What The Planning Reality Became

- `2.3b-low-fi-today-ui` is now the next bounded follow-through slice
- the Today surface should stay low-fi and truthful, with no new product semantics introduced

### Assumptions That Expired

- "read-model truth alone is enough to guarantee the Today route still reflects corrected local-date behavior"

### Next-Phase Corrections

- keep the next worker scope limited to the Today surface and its direct regression coverage
- if the Today surface already remains aligned, close the follow-through and re-evaluate whether the next worthwhile branch is rescue or another mainline verification step

## 2026-04-12 — Today Surface Follow-Through Closed

### Trigger

- the Today-surface date-aware follow-through regression passed
- the active execution queue is now empty after the read-model and Today surface validation loops closed cleanly

### What The Planning Reality Became

- `2.3b-low-fi-today-ui` is now complete as a date-aware follow-through
- there is no remaining dispatchable bounded slice in the current wave
- any next step requires planner formalization of a new bounded task or a new product branch decision

### Assumptions That Expired

- "there is always one more bounded slice ready to dispatch after Today-surface follow-through"

### Next-Phase Corrections

- stop the bounded execution loop here
- do not invent a new worker task without formalizing it first
- resume with planner-level selection only after the next slice is explicitly defined

## 2026-04-11 — Entrypoint Rewrite Guard And Archival Cleanup

### Trigger

- the repo now has a single `AGENTS.md` bootstrap path, but protected entrypoint docs could still be replaced through a near-total same-path rewrite
- `docs/exec-plans/active/tasks/` and `docs/exec-plans/active/handoff/` had accumulated completed artifacts, which blurred active loading paths for future agents

### What The Planning Reality Became

- a new `scripts/check_protected_doc_rewrites.ps1` guard now blocks suspicious near-total staged rewrites for protected entrypoint and governance docs
- `.githooks/pre-commit` and `.github/workflows/ci.yml` now execute the protected-doc rewrite guard
- `scripts/check_task_checkin_and_handoff.ps1` now treats completed task artifacts under `active/tasks/` and completed-task handoffs under `handoff/active/` as validation failures
- `docs/governance/TASK_CHECKIN_PROTOCOL.md`, `docs/governance/SPEC_EDITING_PROTOCOL.md`, and `docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md` now explicitly document the rewrite/archival expectations
- completed tasks `002` through `012` were moved from `docs/exec-plans/active/tasks/` to `docs/exec-plans/completed/tasks/`
- completed handoffs tied to those tasks were moved from `docs/exec-plans/active/handoff/` to `docs/exec-plans/completed/handoff/`
- `docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md` now only points active readers at still-active task and handoff artifacts
- `docs/exec-plans/reference/handoff/README.md` and `docs/index.md` now clarify that root-level `docs/handoff/*.md` files are stable operator references, not the default per-task handoff queue

### Why It Matters

- reduces the chance of another accidental same-path rewrite on entrypoint or governance docs
- makes `active/` mean active again, instead of "active plus historical leftovers"
- keeps progressive loading predictable for later agents without forcing a large docs tree migration

### Snapshot Record

- `artifacts/docs-snapshots/TASK_CHECKIN_PROTOCOL.md_20260411_213400/`
- `artifacts/docs-snapshots/SPEC_EDITING_PROTOCOL.md_20260411_213400/`
- `artifacts/docs-snapshots/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md_20260411_213400/`
- `artifacts/docs-snapshots/CURRENT_EXECUTION_PLAN.md_20260411_213400/`
- `artifacts/docs-snapshots/index.md_20260411_213400/`
- `artifacts/docs-snapshots/handoff_README.md_20260411_213400/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260411_213400/`

## 2026-04-11 — Docs Index Compression

### Trigger

- `docs/index.md` still contained a long canonical checklist and duplicated too much of the detailed spec catalog, which made the index drift back toward handbook behavior

### What The Planning Reality Became

- `docs/index.md` now stays as an index and loading map
- the long `Canonical Specs` section was compressed into a short default reading path plus links to `docs/specs/` and the canonical manifest
- `Quality`, `Active Execution`, and `Governance` were compressed to owner-path summaries instead of long enumerations
- detailed discovery remains available through owner folders and generated manifests instead of being duplicated inside the index

### Why It Matters

- keeps `docs/index.md` lightweight enough to function as a real entrypoint
- reduces repeated maintenance when canonical doc lists change
- makes progressive loading more predictable for later agents

### Snapshot Record

- `artifacts/docs-snapshots/index.md_20260411_214600/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260411_214600/`

## 2026-04-11 — Handoff Reference Split

### Trigger

- stable operator handoff reference docs were still sitting at `docs/handoff/` root, which created avoidable visual noise next to `active/` and `completed/`

### What The Planning Reality Became

- stable handoff reference docs now live under `docs/exec-plans/reference/handoff/`
- `docs/exec-plans/reference/handoff/README.md`, `docs/index.md`, `AGENTS.md`, and `AGENTS.md` now distinguish `active`, `completed`, and `reference` handoff paths
- internal links from `NEXT_AGENT_CHECKLIST.md` and `TEXT_MEAL_RUNTIME_CURRENT.md` now point to the new reference path

### Why It Matters

- reduces handoff-path ambiguity without changing `active/` or `completed/` semantics
- keeps the root handoff directory focused on path selection instead of mixed file discovery
- gives later agents a clearer separation between operational queue and stable reference docs

### Snapshot Record

- `artifacts/docs-snapshots/handoff_README.md_20260411_215800/`
- `artifacts/docs-snapshots/index.md_20260411_215800/`
- `artifacts/docs-snapshots/AGENT_LOADING_PATH.md_20260411_215800/`
- `artifacts/docs-snapshots/AGENTS.md_20260411_215800/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260411_215800/`

## 2026-04-11 — Harness Hard-Gate Hardening

### Trigger

- three governance gaps still remained before the next build wave:
  - task completion was not CI-audited across the tracked task set
  - freeze-growth files could still be touched flat without an explicit responsibility note
  - Alembic governance existed, but schema-sensitive ORM changes were not yet CI-blocked when migrations were missing

### What The Planning Reality Became

- `scripts/check_task_checkin_and_handoff.ps1` now supports repository-audit mode and block-mode validation for tracked task and handoff docs
- `COMPLETED` task artifacts are now required to carry non-empty `actual_touch_files[]` and `tests_run[]` lists during CI audit
- `scripts/check_fat_files.ps1` now blocks staged touches to freeze-growth files unless a staged task artifact or re-plan note names the file and classifies the change as shrink-only extraction, contained bug fix, or boundary-safe wiring
- `scripts/check_migration_discipline.py` now blocks schema-sensitive ORM changes to `app/models.py` unless the same change set includes an Alembic migration under `alembic/versions/`
- `.github/workflows/ci.yml` now runs task-governance audit and migration-discipline checks inside the required `layer-integrity` job
- governance docs now explicitly describe freeze-growth justification and migration-discipline expectations

### Why It Matters

- turns the remaining harness gaps into executable gates instead of reviewer memory
- stops freeze-growth files from silently becoming same-size dumping grounds
- prevents post-Alembic schema drift from re-entering through missing migrations

### Snapshot Record

- `artifacts/docs-snapshots/AGENTS.md_20260411_210500/`
- `artifacts/docs-snapshots/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md_20260411_210500/`
- `artifacts/docs-snapshots/TASK_CHECKIN_PROTOCOL.md_20260411_210500/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260411_210500/`
- `artifacts/docs-snapshots/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md_20260411_204024/`
- `artifacts/docs-snapshots/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md_20260411_204024/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260411_204024/`

## 2026-04-11 — Decision-Mode Governance Second-Pass Alignment

### Trigger

- step-level `decision_mode` 已經進入主要 `L3.x` runtime specs，但 supporting governance 還缺少對 `typed contract`、`guardrail math`、與 `model routing` 的對齊說明

### What Changed

- `L3M` 新增 decision-mode boundary，明確限制 guardrail math 不得被重新委派給 LLM truth decisions
- `L3T` 新增 decision-mode boundary，明確說 typed payload contract 不決定 mode，只約束 mode 選定後的輸出 shape
- `L6C` 收斂 rescue / recommendation routing wording，只對真正的 LLM-backed node 做 role mapping
- `docs/index.md` 補上 `L3T + L3M + L6E` 的閱讀關係說明

### Why It Matters

- 避免 agent 把 `L6C` 誤讀成「每個 expanded node 都必然需要 LLM role」
- 避免 agent 把 `L3T` 誤讀成 runtime reasoning policy，或把 `L3M` 誤讀成可自由讓 LLM 重算的 heuristic 區
- 讓 pass governance、typed contract、guardrail math、routing contract 四者形成單一一致的解讀路徑

### Snapshot Record

- `artifacts/docs-snapshots/L3M_GUARDRAIL_MATH_SPEC.md_20260411_204538/`
- `artifacts/docs-snapshots/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md_20260411_204538/`
- `artifacts/docs-snapshots/L6C_MODEL_ROUTING_PROVIDER_ABSTRACTION_SPEC.md_20260411_204538/`
- `artifacts/docs-snapshots/index.md_20260411_204538/`

## 2026-04-11 — Encoding Recovery For Canonical Governance Specs

### Trigger

- `L3M`、`L3T`、`L6D` 在 Windows / PowerShell 工作流中持續呈現亂碼風險，需要先判斷是內容損壞還是 encoding metadata 不足

### What Changed

- 檢查三份 canonical spec 的原始 bytes，確認內容本身為合法 UTF-8，並非語義層面的 mojibake
- 確認問題主要來自「UTF-8 無 BOM」在 Windows markdown / shell 流程中的顯示脆弱性
- 將以下文件原地轉寫為 `UTF-8 with BOM`，不改變任何語義內容：
  - `L3M_GUARDRAIL_MATH_SPEC.md`
  - `L3T_TYPED_RUNTIME_CONTRACT_SPEC.md`
  - `L6D_REPO_TECH_STACK_CODE_STYLE_SPEC.md`

### Why It Matters

- 這是恢復性 encoding 修復，不是內容重寫
- 後續 agent 在 Windows-heavy docs workflow 中較不容易把 canonical spec 誤判為壞檔或亂碼文件
- 符合 repo 的 cross-project encoding rule：先修 encoding，再做結構性編輯

### Snapshot Record

- `artifacts/docs-snapshots/L3M_GUARDRAIL_MATH_SPEC.md_20260411_205346/`
- `artifacts/docs-snapshots/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md_20260411_205346/`
- `artifacts/docs-snapshots/L6D_REPO_TECH_STACK_CODE_STYLE_SPEC.md_20260411_205346/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260411_205346/`

## 2026-04-11 — Deprecated L6D Pass-Policy Stub Conversion

### Trigger

- the legacy `L6D_LLM_PASS_DESIGN_POLICY_SPEC.md` path still contained a full duplicate body, which could mislead agents into treating it as a second canonical authority alongside `L6E`

### What Changed

- preserved the pre-conversion body via snapshot
- converted `docs/specs/L6D_LLM_PASS_DESIGN_POLICY_SPEC.md` into an explicit deprecated redirect stub
- the stub now points all readers to `L6E_LLM_PASS_DESIGN_POLICY_SPEC.md`
- the stub explicitly states that `L6D` must not be used as an independent authority for pass count, decision-mode governance, or graph-first policy

### Why It Matters

- removes an avoidable duplicate-source failure mode from the canonical docs surface
- keeps old links resolvable without letting the wrong layer label continue to masquerade as current truth
- makes archival snapshots the only place where the old body remains, which is the correct scope for historical material

### Snapshot Record

- `artifacts/docs-snapshots/L6D_LLM_PASS_DESIGN_POLICY_SPEC.md_20260411_205522/`
- `artifacts/docs-snapshots/L6D_LLM_PASS_DESIGN_POLICY_SPEC.md_20260411_205646/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260411_205646/`

## 2026-04-11 — Expanded-Mode Wording Cleanup

### Trigger

- live runtime specs still had a few expanded-mode role-mapping sentences that could be misread as "all named passes must map to LLM roles", especially in recommendation, calibration proposal, and rescue

### What Changed

- `L3.2` now states that only actually LLM-backed named passes need logical model role mapping in expanded mode
- `L3.3B` now explicitly preserves `proposal_gate_pass` as a deterministic gate even if kept as a named stage
- `L3.4` now explicitly preserves `rescue_trigger_pass` and `rescue_assessment_pass` as deterministic when they only perform math / viability / cooldown logic

### Why It Matters

- removes the last obvious wording path by which an agent could still infer that deterministic nodes should receive LLM roles just because they have named pass labels
- keeps expanded-mode observability without reintroducing "expanded mode = full LLM workflow" drift

### Snapshot Record

- `artifacts/docs-snapshots/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md_20260411_205925/`
- `artifacts/docs-snapshots/L3_3B_CALIBRATION_PROPOSAL_POLICY_RUNTIME_CONTRACT_SPEC.md_20260411_205925/`
- `artifacts/docs-snapshots/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md_20260411_205925/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260411_205925/`

## 2026-04-11 — Recovered Legacy Entry Boundary

### Recovery Note

- the block below was previously merged into the wrong entry during later REPLAN edits
- its original source entry cannot be recovered with full certainty from the current live file
- the content is preserved here as a recovered legacy boundary instead of being silently discarded or re-attributed

### Recovered Legacy Content

- a repo script and pre-commit hook now enforce staged protection for those files

### Current Boundary Pressure

- `app/usecases/text_meal.py` is still above the preferred entrypoint threshold
- `app/schemas.py` is still above the preferred schema threshold
- `app/routes.py` is still above the preferred route threshold
- `app/application/context_assembly.py` and `app/application/evidence_assembly.py` are also large enough to monitor next

### Why It Matters

- blocks protected files from quietly growing during ordinary feature work
- gives new agents an executable repo rule instead of relying on doc interpretation alone
- keeps future thinning work focused on extraction instead of repeated relapse into the same files

### Snapshot Record

- `artifacts/docs-snapshots/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md_20260411_171519/`

## 2026-04-11 — Final Spec Optimization Pass

### Trigger

- final spec review still identified three live inconsistencies:
  - corrupted `REPLAN_LOG` entry boundaries
  - calibration canonical node count drift between `L6C`, `L6E`, and `L3.3B`
  - recommendation document shape still biasing readers toward expanded 4-pass decomposition

### What Changed

- `L6E` now explicitly records the product posture as `LLM-first with deterministic carve-outs`
- `L6E` now states that pass count and step split are experiment-driven runtime hypotheses that must be justified by evaluation, not style preference
- `L6C` calibration proposal routing now matches the `2-3 node graph` vocabulary used by `L6E` and `L3.3B`
- `L3.2` now adds a `Canonical Path Walkthrough` and relabels the four pass sections as `Expanded Decomposition Only`
- `L3.3B` and `L3.4` now explicitly mark their lower pass sections as expanded decomposition only
- the previously merged `REPLAN_LOG` block was split, and the uncertain leftover content was preserved under `Recovered Legacy Entry Boundary`

### Why It Matters

- makes the repo’s official posture explicit without turning the system into deterministic-first governance
- removes the last canonical-count disagreement in the pass-governance chain
- reduces the chance that a skimming agent treats expanded pass headings as the default runtime truth
- restores `REPLAN_LOG` as a more reliable audit trail instead of a partially merged narrative

### Snapshot Record

- `artifacts/docs-snapshots/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md_20260411_211424/`
- `artifacts/docs-snapshots/L6C_MODEL_ROUTING_PROVIDER_ABSTRACTION_SPEC.md_20260411_211424/`
- `artifacts/docs-snapshots/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md_20260411_211424/`
- `artifacts/docs-snapshots/L3_3B_CALIBRATION_PROPOSAL_POLICY_RUNTIME_CONTRACT_SPEC.md_20260411_211424/`
- `artifacts/docs-snapshots/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md_20260411_211424/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260411_211424/`

## 2026-04-11 — Runtime Experiment Checklist

### Trigger

- pass-governance spec is now stable enough that runtime tuning needs an operational checklist, not more abstract policy wording

### What Changed

- added a quality-side `Runtime Experiment Checklist`
- translated `LLM-first with deterministic carve-outs` into a concrete experiment workflow
- defined the minimum fields, comparison variants, metrics, trace requirements, and adopt/reject criteria for pass-count and decision-mode tuning
- added a docs index entry so future agents can discover the checklist from the normal reading path

### Why It Matters

- turns "邊測邊試" into a repeatable method instead of ad hoc intuition
- gives future graph / split changes a standard preflight before they touch canonical specs
- helps preserve generic LLM behavior while still making deterministic carve-outs measurable and deliberate

### Snapshot Record

- `artifacts/docs-snapshots/RUNTIME_EXPERIMENT_CHECKLIST.md_20260411_211834/`
- `artifacts/docs-snapshots/index.md_20260411_211834/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260411_211834/`

## 2026-04-11 — Encoding Policy Hard Gate

### Trigger

- the repo already had an encoding policy document and a read-only audit script, but enforcement was missing from both CI and pre-commit
- the previous audit script also scanned all repo markdown, which did not match the intended policy scope

### What Changed

- formalized the hard-gate scope as `docs/**/*.md` plus `AGENTS.md`
- explicitly included `artifacts/docs-snapshots/**` in that policy scope
- updated `check_encoding.ps1` to support:
  - `-AuditDocsPolicy`
  - `-StagedOnly`
  - `-AuditAll`
- wired the encoding audit into `.github/workflows/ci.yml`
- wired the staged encoding audit into `.githooks/pre-commit`
- clarified in docs that BOM governance is a documentation policy, not a repo-wide markdown default
- ran a one-shot normalization wave to convert policy-scope markdown to `UTF-8 with BOM`
- verified both `-AuditDocsPolicy` and `-StagedOnly` pass after normalization

### Why It Matters

- turns encoding stability from advisory guidance into an executable hard gate
- aligns the audit script with the actual governance scope instead of failing on unrelated markdown under caches, virtualenvs, or scratch directories
- preserves Windows-heavy spec readability without forcing BOM onto every engineering artifact in the repository

### Snapshot Record

- `artifacts/docs-snapshots/ENCODING_POLICY.md_20260411_224309/`
- `artifacts/docs-snapshots/ENCODING_POLICY.md_20260411_225219/`
- `artifacts/docs-snapshots/index.md_20260411_224309/`
- `artifacts/docs-snapshots/index.md_20260411_225219/`
- `artifacts/docs-snapshots/AGENTS.md_20260411_225013/`
- `artifacts/docs-snapshots/AGENTS.md_20260411_225219/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260411_224309/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260411_225219/`

## 2026-04-11 — Encoding Normalization Utility

### Trigger

- the repo now has a hard-gated encoding audit, but repair still depended on ad hoc shell snippets instead of a dedicated repo script

### What Changed

- added `scripts/normalize_encoding.ps1` as the explicit repair companion to `scripts/check_encoding.ps1`
- scoped normalization to the same policy boundary:
  - `docs/**/*.md`
  - `AGENTS.md`
- supported both:
  - `-DocsPolicy`
  - `-StagedOnly`
- documented the repair script in `docs/governance/ENCODING_POLICY.md` and `docs/index.md`
- smoke-tested the repair script with `-DocsPolicy` and re-verified `check_encoding.ps1 -AuditDocsPolicy`

### Why It Matters

- keeps the audit script read-only while still giving operators and agents a single sanctioned repair path
- prevents future encoding repair from drifting into one-off shell commands with different scope rules
- makes policy enforcement and policy repair share the same repo-defined boundary

### Snapshot Record

- `artifacts/docs-snapshots/ENCODING_POLICY.md_20260411_225738/`
- `artifacts/docs-snapshots/index.md_20260411_225738/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260411_225738/`

## 2026-04-11 — File Placement Governance

### Trigger

- protected-file gates now exist, but agents still need a deterministic rule for where new code should go after a protected file rejects further growth

### What The Planning Reality Became

- repository governance now includes an explicit file placement decision table and naming discipline
- role-based placement is now first-class:
  - routes in `app/web/*`
  - contracts in `app/schema_defs/*`
  - orchestration/read-side logic in `app/application/*`
  - domain invariants in `app/domain/*`
  - persistence in `app/infrastructure/*`
- boundary-sensitive tasks are expected to declare `allowed_touch_areas`, `forbidden_touch_areas`, and `new_files_expected`

### Why It Matters

- prevents agents from responding to protected-file gates with ad-hoc file creation
- makes "cannot go here" resolve into a deterministic build path
- keeps file growth control tied to architecture ownership instead of only line counts

### Snapshot Record

- `artifacts/docs-snapshots/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md_20260411_183000/`
- `artifacts/docs-snapshots/AGENTS.md_20260411_183000/`

## 2026-04-11 — Layer Integrity Warning Cleanup

### Trigger

- `check_layer_integrity.py` was added and immediately exposed five warning-level ownership drifts in `app/web/*` and `app/agent/*`

### What The Code Actually Became

- route modules no longer import `sqlalchemy.orm`; DB session dependencies stay injected but route code no longer advertises direct ORM ownership
- exact-item FTS lookup now lives in infrastructure via `app/infrastructure/exact_item_search.py`
- a lightweight `app/search/exact_item_lookup.py` facade now shields higher-level callers from direct infrastructure imports

### Assumptions That Expired

- "route modules can keep SQLAlchemy type imports without meaningful layer drift"
- "exact-item search can stay under `app/agent/*` even though it owns SQL-backed lookup behavior"
- "application is the best facade location by default" once package import side effects are present

### Next-Phase Corrections

- if stricter layer linting is introduced later, review `app/application/__init__.py` package side effects before using `application/*` as a facade namespace
- consider whether `app/search/*` should be documented as a lightweight query-facade family in future placement rules

## 2026-04-11 — Existing Code File Edit Rule

### Trigger

- repo rules already forbade delete-and-recreate behavior for spec documents, but the same expectation was not yet explicit for ordinary code files

### What The Planning Reality Became

- existing code files now default to targeted edits rather than delete-and-recreate replacement
- delete-and-recreate is now treated as an exception path for code files, not a normal editing method

### Allowed Exception Cases

- explicit retirement or move during a boundary refactor
- patch-anchor, tooling, or encoding blockers that make targeted edits impractical
- deliberate conversion into a thin entrypoint or compatibility shim

### Why It Matters

- keeps long-lived code history easier to review
- reduces accidental semantic loss during large refactors
- aligns code-editing behavior with the stricter document-editing discipline already used for specs and planning artifacts

### Snapshot Record

- `artifacts/docs-snapshots/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md_20260411_191500/`
- `artifacts/docs-snapshots/AGENTS.md_20260411_191500/`

## 2026-04-11 — CI Consolidation And Search Layer Formalization

### Trigger

- layer integrity now exists as a standalone workflow, but repo governance still lacked a main test workflow and `app/search/*` was functioning as an implicit layer rather than a documented one

### What The Planning Reality Became

- CI is now centered on a main `ci` workflow with both `layer-integrity` and `tests` jobs
- the standalone layer-only workflow was retired to avoid duplicated pipeline surfaces
- `app/search/*` is now explicitly documented as a query-time retrieval layer with its own placement and dependency rules

### Why It Matters

- makes layer integrity part of the normal CI path instead of an isolated check
- reduces future facade-placement drift by giving `app/search/*` a formal ownership boundary
- keeps retrieval composition out of `app/application/*` and `app/agent/*` when the code is really query-time lookup or ranking logic

### Snapshot Record

- `artifacts/docs-snapshots/BUILD_FILE_PLACEMENT_RULES.md_20260411_193500/`
- `artifacts/docs-snapshots/LAYER_DEPENDENCY_RULES.md_20260411_193500/`
- `artifacts/docs-snapshots/AGENTS.md_20260411_193500/`

## 2026-04-11 — Build-Start Harness Baseline

### Trigger

- next implementation phases should not proceed until repo governance covers platform settings, freeze-growth blind spots, structured task completion, and CI test layering

### What The Planning Reality Became

- platform-side GitHub governance is now recorded explicitly in repo docs instead of being left as verbal expectation
- fat-file governance now distinguishes protected legacy files from freeze-growth architecture risk files
- task completion records are being standardized around explicit structured fields
- CI is being split into layer integrity, smoke tests, and integration tests before the next feature-heavy build wave

### Why It Matters

- reduces silent relapses into oversized application or agent aggregation files
- makes task completion machine-readable for later agents
- prevents local hooks from being the only enforcement point

### What The Code Actually Became

- `docs/governance/GITHUB_REPO_GOVERNANCE.md` now records required branch protection and required status check names for platform-side enforcement
- `scripts/check_fat_files.ps1` now distinguishes protected legacy files from freeze-growth architecture risk files and a watchlist
- `pytest.ini`, `tests/conftest.py`, and `.github/workflows/ci.yml` now define a layered `smoke` / `integration` / `e2e` test path
- `.github/dependabot.yml` now governs weekly `pip` and `github-actions` updates
- `app/infrastructure/conversation_state_loader.py` now owns retrieval and sync only, while `app/application/conversation_state_assembler.py` owns `ConversationState` assembly
- `scripts/check_task_checkin_and_handoff.ps1` now requires structured completion fields for `COMPLETED` task artifacts

### Implementation Note

- `app/infrastructure/conversation_state_loader.py` required a delete-and-recreate exception during the split because garbled content blocked safe anchor-based patching; ownership was preserved and re-established immediately on the same path

### Snapshot Record

- `artifacts/docs-snapshots/AGENTS.md_20260411_201500/`
- `artifacts/docs-snapshots/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md_20260411_201500/`
- `artifacts/docs-snapshots/TASK_CHECKIN_PROTOCOL.md_20260411_201500/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260411_201500/`
- `artifacts/docs-snapshots/AGENTS.md_20260411_194024/`
- `artifacts/docs-snapshots/GITHUB_REPO_GOVERNANCE.md_20260411_194024/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260411_194024/`

## 2026-04-11 — Alembic Migration Governance

### Trigger

- runtime schema repair via `_ensure_sqlite_compat_columns()` was still present, which is unsafe for production-grade SQLite/PostgreSQL parity

### What The Planning Reality Became

- schema management now has an Alembic baseline revision
- `app.database.init_db()` now runs migration-aware bootstrap logic instead of ad hoc `ALTER TABLE` repair
- `app.infrastructure.__init__` was converted to lazy exports to prevent import cycles during migration bootstrap
- requirements now include `alembic` and `psycopg2-binary` so the same migration path can serve SQLite and PostgreSQL
- the Alembic baseline revision was verified on a fresh temporary SQLite database with `upgrade head`
- `app.database.init_db()` was verified against both stamped legacy SQLite state and a fresh SQLite database using the new baseline revision
- legacy `stamp head` fallback was removed; legacy schemas now fail fast unless they are migrated through Alembic
- `app.database.init_db()` now refuses to auto-stamp legacy schemas and only accepts clean Alembic upgrades on startup

### Why It Matters

- removes startup-time DDL drift from the app runtime path
- gives SQLite and Supabase/PostgreSQL a shared migration history
- makes future schema changes explicit and reviewable

### Snapshot Record

- `artifacts/docs-snapshots/REPLAN_LOG.md_20260411_200000/`
- `artifacts/docs-snapshots/GITHUB_REPO_GOVERNANCE.md_20260411_200000/`
- `artifacts/docs-snapshots/AGENTS.md_20260411_200000/`
- `artifacts/docs-snapshots/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md_20260411_200000/`

## 2026-04-11 — Freeze-Growth Extraction Map

### Trigger

- repo-level placement rules already existed, but freeze-growth files still lacked file-level extraction maps describing what to move first and where

### What The Planning Reality Became

- freeze-growth ownership is now paired with a per-file extraction map
- the repo now distinguishes:
  - placement rules for new code
  - extraction targets for existing oversized files
- the extraction map now covers:
  - `app/application/evidence_assembly.py`
  - `app/application/context_assembly.py`
  - `app/agent/knowledge_packets.py`
  - `app/agent/nutrition_engine.py`

### Why It Matters

- prevents future "support.py" style panic-splitting when a frozen file is touched
- turns large-file cleanup into a planned boundary move instead of an improvised refactor
- makes it clearer when a task should trigger extraction immediately versus defer until the next slice

### Snapshot Record

- `artifacts/docs-snapshots/FREEZE_GROWTH_EXTRACTION_MAP.md_20260411_201500/`
- `artifacts/docs-snapshots/index.md_20260411_201500/`
- `artifacts/docs-snapshots/REPLAN_LOG.md_20260411_201500/`

## 2026-04-11 — Shift Back To Read-Model Follow-Through

### Trigger

- historical correction hardening is now complete under the new harness gates, and the next ambiguity sits on the read side rather than the commit path

### What The Planning Reality Became

- `2.3a-current-budget-read-model` needs a follow-through pass that validates correction-safe read semantics after the correction target resolver changes
- this is not a rerun of the original read-model foundation task; it is a narrower read-side alignment task after correction hardening

### Assumptions That Expired

- "the original `2.3a` foundation task fully closes read-model concerns even after correction semantics change"

### Next-Phase Corrections

- treat the next active task as read-model follow-through, not another intake-core task
- keep the new task narrow: read model only, no UI or rescue expansion

## 2026-04-11 — Shift To Today-UI Follow-Through

### Trigger

- the read-model follow-through closed by regression, so the next ambiguity moved up to the Today surface that consumes that read model

### What The Planning Reality Became

- `2.3b-low-fi-today-ui` needs a follow-through pass under the new `app/web/*` placement rules
- the route-level follow-through should stay additive and correction-safe, not reopen broader UI or read-model work

### Assumptions That Expired

- "the old `2.3b` completion is sufficient after the repo moved route ownership into `app/web/*` and correction semantics were tightened underneath it"

### Next-Phase Corrections

- make the next active task a Today-surface follow-through scoped to `app/web/today_routes.py`
- keep `app/routes.py` protected and untouched

## 2026-04-12 — Return To Web-Search Fallback Lane

### Trigger

- the read-model and Today-surface follow-through slices both closed via regression coverage, so the next bounded gap moved back to intake search ownership

### What The Planning Reality Became

- `2.1e-web-search-fallback-lane` is the next active intake slice after exact-db, clarify-required, and cannot-estimate all completed
- the slice should land in retrieval/search modules and only touch pass modules if escalation vocabulary truly needs alignment

### Assumptions That Expired

- "more read-side follow-through is still the highest-value active work"

### Next-Phase Corrections

- make the next active task a search-ownership slice, not another read-side slice
- keep `app/routes.py`, `app/usecases/text_meal.py`, and `app/schemas.py` untouched

## 2026-04-12 — Web-Search Fallback Re-plan Trigger

### Trigger

- `2.1e-web-search-fallback-lane` needs exact-vs-search authority separation, but the relevant `source_tier_for_item` seam still lives in freeze-growth `app/application/evidence_assembly.py`

### What The Planning Reality Became

- the active web-search fallback task is blocked by a valid freeze-growth boundary, not by a failing runtime test
- the next correct step is a narrow extraction task that isolates `source_class_for_item` / `source_tier_for_item` into a non-frozen application module
- `2.1e` should resume only after that extraction task lands

### Assumptions That Expired

- "the existing `2.1e` worker scope can complete the lane without touching a frozen file"
- "authority-policy refinement can happen directly inside `app/application/evidence_assembly.py` without violating current harness rules"

### Next-Phase Corrections

- keep `TASK-2026-04-12-016-WEB-SEARCH-FALLBACK-LANE` in blocked state with an active handoff
- make `TASK-2026-04-12-017-EVIDENCE-TIER-POLICY-EXTRACTION` the current bounded prerequisite task
- do not reopen `2.1e` until the source-tier seam is isolated from the freeze-growth file

## 2026-04-12 — Web-Search Authority Tier Sync

### Trigger

- `TASK-2026-04-12-018-SEARCH-AUTHORITY-TIER-SEPARATION` completed and reviewer confirmed that code-level authority semantics had drifted ahead of canonical spec wording

### What The Planning Reality Became

- `web_search_official` now explicitly sits below `exact_item_db`
- canonical retrieval / ownership docs must say that official web evidence is fallback grounding, not default exact truth
- the prerequisite extraction work is complete, so `TASK-2026-04-12-016-WEB-SEARCH-FALLBACK-LANE` can resume as the active slice

### Assumptions That Expired

- "`official_web` can remain in the exact-verified tier by default"
- "the prerequisite extraction tasks can stay in active state after the authority seam is resolved"

### Next-Phase Corrections

- move completed extraction tasks out of `active/tasks`
- clear the stale blocked handoff for `TASK-2026-04-12-016-WEB-SEARCH-FALLBACK-LANE`
- resume `2.1e` on the narrowed retrieval/search scope

## 2026-04-12 — Post-Fallback Shift To Rescue Follow-through

### Trigger

- `TASK-2026-04-12-016-WEB-SEARCH-FALLBACK-LANE` closed successfully under the repaired planner loop runner
- active control docs still pointed at `2.1e` after the task had already been archived
- `2.7a-context-selector` remains explicitly unformalized in the slice registry and is not ready for autonomous loop execution

### What The Planning Reality Became

- `2.1e-web-search-fallback-lane` is now complete enough to leave active execution
- the next safe bounded slice is a `2.5a-rescue-deterministic-overlay` follow-through that aligns rescue runtime with the canonical `BodyPlan.safety_floor_kcal` source
- context-selector work remains queued, but must not become an active loop task until it has a formal registry entry and bounded task definition

### Assumptions That Expired

- "`2.1e` is still the active slice after the runner closes it"
- "`2.7a-context-selector` is ready for autonomous loop execution without a formal slice/task definition"

### Next-Phase Corrections

- remove `TASK-2026-04-12-016-WEB-SEARCH-FALLBACK-LANE` from active control state
- activate a bounded rescue follow-through task focused on safety-floor source alignment
- keep context-selector as queued planning work only until its registry entry exists

## 2026-04-12 — Rescue Safety-Floor Truth Sync Closed

### Trigger

- `TASK-2026-04-12-019-RESCUE-SAFETY-FLOOR-SOURCE-ALIGNMENT` completed and reviewer correctly detected that rescue runtime truth had moved ahead of the rescue spec wording

### What The Planning Reality Became

- `BodyPlan.safety_floor_kcal` is now the canonical runtime hard floor for rescue
- `1200 / 1500` remain baseline lower-bound policy values, not the user’s personalized daily target
- personalized deterministic daily target calculation is now explicitly split into queued `TASK-2026-04-12-020-RECOMMENDED-TARGET-KCAL-FOUNDATION`

### Assumptions That Expired

- "rescue runtime may still heuristic-fallback inside the runtime contract when canonical state is missing"
- "hard floor and personalized daily target can stay implicit in the same scalar"

### Next-Phase Corrections

- archive `TASK-2026-04-12-019-RESCUE-SAFETY-FLOOR-SOURCE-ALIGNMENT` with a completed handoff
- leave `TASK-2026-04-12-020-RECOMMENDED-TARGET-KCAL-FOUNDATION` queued until its slice registry entry is formalized

## 2026-04-12 — Completed Handoff Debt Cleanup And Next-Slice Selection

### Trigger

- older completed tasks `016/017/018` still lacked complete `handoff_doc_path` coverage even though the completed queue had become the canonical execution history
- `CURRENT_EXECUTION_PLAN.md` still carried a stale active-task pointer to `TASK-019` after `TASK-019` and `TASK-020` had already been archived

### What The Planning Reality Became

- completed-task governance debt must be closed before using the completed queue as reliable planner history
- `2.7a-context-selector` remains the next product-relevant slice, but it is still planning-only because it has no formal registry entry or bounded task definition
- after `2.6a-recommended-target-kcal-foundation`, the next worthwhile work is not another rescue patch; it is either:
  - formalize `2.7a-context-selector`, or
  - formalize the next calibration-core slice if calibration is chosen ahead of memory/retrieval deepening

### Assumptions That Expired

- "the completed queue is already fully governance-complete even when handoff links are missing"
- "`TASK-019` is still the active execution reference after archival"
- "`2.7a-context-selector` is dispatch-ready without planner formalization"

### Next-Phase Corrections

- keep `CURRENT_EXECUTION_PLAN.md` free of stale active-task references once tasks are archived
- treat `2.7a-context-selector` as the next highest-value planning slice, not an implementation task yet
- do not open a bounded worker for context-selector until a formal registry entry and narrow write scope exist

## 2026-04-12 — First Calibration-Core Slice Formalized

### Trigger

- `2.6a-recommended-target-kcal-foundation` is complete, so the next worthwhile work must enter canonical `2.6 Calibration Core` rather than jump straight to `2.7 Memory / Retrieval Deepening`
- `2.7a-context-selector` remains unformalized and therefore not dispatch-safe

### What The Planning Reality Became

- the first bounded calibration-core slice is `2.6b-calibration-posture-foundation`
- this slice is intentionally narrower than proposal policy:
  - it only computes deterministic posture classification and operating-estimate outputs
  - it does not create proposals
  - it does not write canonical BodyPlan adoption yet
  - it does not introduce UI or recommendation wiring

### Assumptions That Expired

- "after `2.6a`, the next best move is direct memory / retrieval work"
- "calibration-core should start at proposal or UI level"

### Next-Phase Corrections

- queue `TASK-2026-04-12-021-CALIBRATION-POSTURE-FOUNDATION` as the next dispatchable bounded task
- treat the next calibration step after `2.6b` as a separate decision:
  - canonical writeback / active-BodyPlan adoption
  - or `L3.3B` proposal-policy runtime

## 2026-04-12 — Calibration Posture Foundation Closed; Proposal Gate Selected Next

### Trigger

- `TASK-2026-04-12-021-CALIBRATION-POSTURE-FOUNDATION` completed with green deterministic tests and preserved the intended boundary: no proposal shaping, no UI, and no writeback
- the next calibration decision had to choose between direct `BodyPlan` adoption and proposal-first gating

### What The Planning Reality Became

- `L3.3A` posture outputs are now real enough to feed a deterministic proposal gate
- direct `BodyPlan` writeback would violate the proposal-first boundary from `L3.3B`
- the next bounded calibration-core slice is therefore `2.6c-calibration-proposal-gate-foundation`

### Assumptions That Expired

- "after posture exists, the next safe step is immediate canonical writeback"
- "proposal gate and option generation should be collapsed into one first follow-up slice"

### Next-Phase Corrections

- archive `TASK-2026-04-12-021-CALIBRATION-POSTURE-FOUNDATION` with a completed handoff
- queue `TASK-2026-04-12-022-CALIBRATION-PROPOSAL-GATE-FOUNDATION`
- keep option generation, response shaping, and accept-side writeback for later bounded slices

## 2026-04-12 — Calibration Drift Versus Main-Flow Priority

### Trigger

- `2.6b` and `2.6c` both completed cleanly as bounded slices, but user priority remained the unfinished multi-turn intake main flow rather than deeper calibration scaffolding
- the planner had followed canonical ordering legality, but not the stronger product-priority question: "what is the next highest-value unfinished founder flow?"

### What The Planning Reality Became

- calibration-core work was not architecturally illegal, but it pulled focus away from the still-unfinished `2.2` main flow
- the repo now has enough calibration foundation to pause safely
- active execution should return to `2.2a-active-meal-continuation` and then `2.2c-cross-midnight-attribution` before more calibration or memory/retrieval deepening

### Why The Drift Happened

- the harness is stronger at enforcing local boundedness than at enforcing product-priority re-centering
- the execution plan still mixed "next legal slice" with "next highest-value slice"
- there is not yet an explicit main-flow-completeness gate that blocks deeper scaffolding once the current main flow is still incomplete

### Assumptions That Expired

- "if a slice is legal in the dependency graph, it is automatically the right next slice"
- "bounded deterministic scaffolding is always harmless to continue while the main flow remains incomplete"

### Next-Phase Corrections

- pause further calibration-core execution after `2.6c`
- restore `2.2a-active-meal-continuation` as the active product-main-flow slice
- treat `2.2` founder-fit validation as a higher-priority gate than additional calibration or memory scaffolding

## 2026-04-12 — Continuation Proof Closed, Date Attribution Remains

### Trigger

- `TASK-2026-04-12-023-ACTIVE-MEAL-CONTINUATION-FOUNDATION` completed without required production-code changes
- the bounded worker proved, through regression, that clear active-meal continuation already preserves canonical thread lineage

### What The Planning Reality Became

- active-meal continuation is no longer the highest-risk unresolved `2.2` behavior
- the remaining `2.2` execution risk is cross-midnight local-date attribution for intake and correction
- the next best-next slice is therefore `2.2c-cross-midnight-attribution`

### Assumptions That Expired

- "continuation likely still needs a production-code patch in state transition or commit plumbing"
- "continuation must remain the active main-flow task until code is changed"

### Next-Phase Corrections

- archive `TASK-2026-04-12-023-ACTIVE-MEAL-CONTINUATION-FOUNDATION` with a completed handoff
- dispatch `TASK-2026-04-12-024-CROSS-MIDNIGHT-ATTRIBUTION-FOUNDATION`
- keep calibration, memory, and read-side follow-through deferred until `2.2` main-flow date attribution is proven stable

## 2026-04-12 — 2.2 Main-Flow Stabilized, Read Side Must Reconfirm

### Trigger

- `TASK-2026-04-12-024-CROSS-MIDNIGHT-ATTRIBUTION-FOUNDATION` completed with green targeted tests and governance checks
- late-night intake and correction now backfill local attribution before persistence, changing the effective truth that downstream read-side logic must surface

### What The Planning Reality Became

- `2.2a` and `2.2c` are both complete enough to move the critical path forward
- the next best-next slice is no longer inside `2.2`
- the next execution risk is whether the `2.3` read side still faithfully reflects correction and cross-midnight local-date truth

### Assumptions That Expired

- "after `2.2c`, the next meaningful work is still inside intake-core"
- "read-side follow-through already has enough coverage regardless of local-date attribution changes"

### Next-Phase Corrections

- archive `TASK-2026-04-12-024-CROSS-MIDNIGHT-ATTRIBUTION-FOUNDATION` with a completed handoff
- re-enter `2.3a-current-budget-read-model` with a narrow follow-through scope
- keep `2.3b`, `2.5`, and later-domain work behind that read-side verification step

## 2026-04-12 — Read-Side Re-entry After 2.2 Stabilization

### Trigger

- `2.2a` and `2.2c` are both now complete enough that the critical path can leave intake-core
- the current execution risk moved from intake semantics to whether the read side still reflects the updated continuation and local-date truth

### What The Planning Reality Became

- `2.3a-current-budget-read-model` is again the best-next slice, but as a narrow date-and-lineage follow-through rather than a fresh foundation task
- `2.3b-low-fi-today-ui` should stay deferred until the read model is reconfirmed against the new `2.2` behavior

### Assumptions That Expired

- "existing `2.3a` coverage is enough regardless of `2.2c` local-date changes"
- "the next best-next after `2.2c` is automatically the Today UI surface"

### Next-Phase Corrections

- queue `TASK-2026-04-12-025-CURRENT-BUDGET-READMODEL-DATE-FOLLOWTHROUGH`
- keep the worker scope limited to read-model assembly, infrastructure query shape, and regression coverage
- use the result to choose between `2.3b` and `2.5`

## 2026-04-12 — Re-enter Rescue After 2.3 Wave Closure

### Trigger

- `2.3a` and `2.3b` follow-through both closed cleanly
- `2.4a` and `2.4b` already exist, so the next worthwhile bounded branch is no longer inside read-side or body-observation work
- `2.6` remains intentionally paused and `2.7a` is still not formalized

### What The Planning Reality Became

- the next best-next slice is `2.5b-rescue-proposal-artifact-foundation`
- this slice should stop at structured rescue proposal artifact formation
- response wording, rescue-family product semantics, and user-facing surfaces remain behind the next human gate

### Assumptions That Expired

- "after `2.3b`, the next best move is deeper calibration or memory/retrieval work"
- "rescue can wait until later even when the preconditions for non-user-facing proposal artifact work are already in place"

### Next-Phase Corrections

- formalize and dispatch `TASK-2026-04-12-027-RESCUE-PROPOSAL-ARTIFACT-FOUNDATION`
- keep the worker scope inside rescue application modules and rescue tests
- stop after `2.5b` closes, before `2.5c` option shaping or `2.5d` response work

## 2026-04-12 — Rescue Proposal Artifact Closed; Human Gate Reached

### Trigger

- `TASK-2026-04-12-027-RESCUE-PROPOSAL-ARTIFACT-FOUNDATION` completed with green targeted tests and governance checks
- the bounded rescue work now covers deterministic proposal artifact structure without touching user-facing response behavior

### What The Planning Reality Became

- `2.5b` is complete
- the next rescue step would move into option-family semantics, proposal framing, and possibly LLM-backed or human-facing wording decisions
- that boundary is the planned human gate for the current rescue wave

### Assumptions That Expired

- "rescue can continue straight from deterministic artifact formation into option shaping without a product-semantics stop"

### Next-Phase Corrections

- archive `TASK-2026-04-12-027-RESCUE-PROPOSAL-ARTIFACT-FOUNDATION` with a completed handoff
- stop active implementation here
- discuss rescue-family meaning and `2.5c` boundaries before formalizing the next rescue slice

## 2026-04-11 — Decision-Mode Annotation Alignment

### Trigger

- pass governance 已改成 `graph-first, role-second`，但 runtime spec 的 step 級責任仍缺少明確 `decision_mode` 標記，容易讓 agent 把 domain-level 原則過度泛化

### What Changed

- `L6E_LLM_PASS_DESIGN_POLICY_SPEC.md` 新增 `Decision Mode Rule` 與 `Required Step Annotation`
- `L3.1` 在 `task_meal_link / decision / nutrition_resolution / final_response` 補上 `decision_mode` 與 `decision_reason`
- `L3.2` 在 `context / candidate retrieval / ranking / response` 補上 `decision_mode` 與 `decision_reason`
- `L3.3A` 在五個 calibration steps 與 `insufficient_data` 說明補上 `decision_mode` 與 `decision_reason`
- `L3.3B` 在 proposal gate、option shaping、ranking、response 補上 `decision_mode` 與 `decision_reason`
- `L3.4` 在 trigger、assessment、option、response 補上 `decision_mode` 與 `decision_reason`

### Why It Matters

- 把「LLM first vs deterministic first」從 domain-level slogan 收斂成 step-level contract
- 保留 intake 的語義解讀能力，同時避免 calibration / rescue 的閾值與數學被錯誤 LLM 化
- 讓後續 agent 可以直接從 spec 讀出每個 decision point 的合法執行模式，而不是自行猜測

### Snapshot Record

- `artifacts/docs-snapshots/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md_20260411_203256/`
- `artifacts/docs-snapshots/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md_20260411_203256/`
- `artifacts/docs-snapshots/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md_20260411_203256/`
- `artifacts/docs-snapshots/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md_20260411_203257/`
- `artifacts/docs-snapshots/L3_3B_CALIBRATION_PROPOSAL_POLICY_RUNTIME_CONTRACT_SPEC.md_20260411_203257/`
- `artifacts/docs-snapshots/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md_20260411_203257/`

## 2026-04-14 — Anti-Bloat Preemptive Extraction: `context_assembly.py`

### Trigger

- `app/application/context_assembly.py` had exceeded its 636-line freeze-growth threshold (reached 706 lines) due to Role Mix (text processing, heuristics, planner assembly, and prompt formatting combined).
- Turn 2 construction was actively ongoing and would have further bloated the file, pushing it into hard-blocked territory by `check_fat_files.ps1`.

### What The Planning Reality Became

- The system must proactively perform architecture extraction ("pave the way") rather than waiting for an active branch to fail the fat-file gate.
- Pure functions and heuristic policies must be moved to specialized layers, leaving `context_assembly.py` only with payload orchestration (and legacy re-exports to maintain 0% disruption).
- We established `context_normalizer.py`, `pass_payload_policies.py`, `planner_context_assembler.py`, and `context_pack_builder.py`.

### Assumptions That Expired

- "Refactoring large files should only happen after they block a feature."
- "Legacy files under watch will shrink naturally during feature development."

### Next-Phase Corrections

- The `context_assembly.py` size has dropped to ~412 lines (now marked `[SHRUNK]`), freeing up space for proper Turn 2 additions.
- Legacy text and policy features maintain active paths backwards via re-exports so no `turn-1` consumers break.
- For future development, new pure rules or pass rendering logic must land in these newly extracted files, not the orchestrator.

## 2026-04-15 — `2.5c` Deterministic Option Shaping Implemented

### Trigger

- the user explicitly asked to start the `2.5c rescue option shaping` implementation scope

### What Changed

- `rescue_proposal.py` now emits activation-aware rescue option artifacts with:
  - `activation_mode`
  - `horizon_days`
  - `daily_kcal_adjustments`
- rescue shaping now applies the `11:00` activation rule:
  - `next_meal_protection` stays `immediate_next_meal`
  - future-affecting rescue families resolve to `today_lunch` before the cutoff and `tomorrow_0000` after the cutoff
- `same_day_soft_cap` is no longer shaped after the cutoff
- ranking semantics now explicitly preserve:
  - `non_viable -> rescue_stop_and_escalate`
  - one-day rescue -> `next_meal_protection`
  - viable multi-day rescue -> `short_horizon_spread`
  - `strained` rescue -> near-term protection before wider spreading

### Why This Is The Correct Boundary

- it advances `2.5c` without opening rescue response wording, UI, quick actions, or accept-side writeback
- it keeps rescue shaping deterministic-first, which matches the rescue runtime contract
- it improves typed artifact alignment without introducing any deterministic overwrite of completed LLM pass outputs

### Evidence

- `python -m pytest tests/test_rescue_proposal.py -q`
- `python scripts/check_layer_integrity.py`
- `powershell -ExecutionPolicy Bypass -File scripts/check_encoding.ps1 -AuditDocsPolicy`
- `python scripts/harness_garbage_collect.py`

## 2026-04-15 — `2.5c` Rescue Runtime Entrypoint Wired

### Trigger

- after deterministic option shaping landed, the next bounded move was to stop treating `rescue_proposal.py` as an isolated builder and expose a thin non-user-facing rescue runtime entrypoint

### What Changed

- added `app/application/rescue_runtime.py`
- the new runtime entrypoint now accepts deterministic trigger truth plus deterministic assessment truth and emits:
  - `rescue_assessment_packet`
  - `rescue_result`
- the integration remains intentionally thin:
  - no response wording
  - no UI
  - no quick actions
  - no accept-side commit behavior

### Why This Is The Correct Boundary

- it advances `2.5c` from isolated artifact generation into dispatch-safe non-user-facing runtime integration
- it preserves the canonical `trigger -> assessment -> option shaping -> response(optional)` graph without prematurely opening `2.5d`
- it gives later rescue work a stable application entrypoint instead of forcing future layers to call the proposal builder directly

### Evidence

- `python -m pytest tests/test_rescue_proposal.py tests/test_rescue_runtime.py -q`
- `python scripts/check_layer_integrity.py`

## 2026-04-15 — `2.5c` Rescue Proposal Persistence Wired

### Trigger

- after the thin rescue runtime entrypoint existed, the next bounded step was to persist rescue option artifacts as formal proposal containers instead of leaving them as in-memory runtime-only objects

### What Changed

- generalized proposal persistence from single-option skeletons to multi-option artifact persistence
- rescue runtime can now persist:
  - proposal container metadata
  - ranked rescue options
  - top-option linkage
  - effect payloads including activation mode and daily kcal adjustments

### Why This Is The Correct Boundary

- it keeps `2.5c` non-user-facing and proposal-first
- it does not accept or apply rescue overlays
- it prepares the canonical proposal state that later rescue response or accept flows can read without reopening deterministic shaping work

### Evidence

- `python -m pytest tests/test_rescue_proposal.py tests/test_rescue_runtime.py tests/test_canonical_persistence.py -q`
- `python scripts/check_layer_integrity.py`

## 2026-04-15 — `2.5c` Open Rescue Proposal Read-Side Added

### Trigger

- after rescue proposal persistence landed, the next bounded need was a read path that can retrieve the current open rescue proposal and its ranked top option without opening any response surface

### What Changed

- added a rescue-only proposal read model:
  - infrastructure loader for open rescue proposals
  - application read-side entrypoint that returns open rescue proposal containers and their options
- retrieval is intentionally narrow:
  - `proposal_type = rescue`
  - `proposal_status = open`
  - sorted ranked options
  - top option preserved via `top_option_id`

### Why This Is The Correct Boundary

- it keeps `2.5c` proposal-first and non-user-facing
- it gives later rescue response / planner layers a stable read path instead of forcing direct ORM reads
- it still stops before wording, quick actions, accept-side effects, or channel behavior

### Evidence

- `python -m pytest tests/test_open_proposals_read_model.py tests/test_rescue_runtime.py tests/test_rescue_proposal.py -q`
- `python scripts/check_layer_integrity.py`

## 2026-04-15 — `2.5c` Reaches Review Boundary

### Trigger

- the user asked to continue implementation only until review became necessary

### What The Build State Became

- `2.5c` now has the full intended non-user-facing spine:
  - deterministic rescue option shaping
  - thin rescue runtime entrypoint
  - proposal-container persistence
  - open rescue proposal read-side
- any further rescue work would move into response-surface semantics, intervention wording, quick actions, or accept-side interaction design

### Why Work Stops Here

- those next-step questions belong to `2.5d`, not `2.5c`
- they require explicit product review because they define how rescue should surface to users, not just how rescue should be shaped internally

### Execution Correction

- hold the rescue branch at the human review gate
- do not dispatch `2.5d` automatically
- treat `2.5c` as completed enough pending review of rescue response-surface semantics

## 2026-04-15 — `2.5d` Chat-First Single-Plan Rescue Surface Started

### Trigger

- the user explicitly approved the `2.5d` rescue surface direction
- rescue was narrowed from a multi-option surface into a single recovery-plan surface with adjustable intensity

### What Changed

- added a deterministic rescue response layer in `app/application/rescue_response.py`
- the response layer now:
  - gates rescue surface to open rescue proposals only
  - keeps rescue and intake separated
  - renders one recommended recovery plan instead of backup-option menus
  - supports chat actions for accept, shorten, extend, reject, and explain
- the surface uses:
  - `15%` daily-budget cap for the standard recommendation
  - `20%` daily-budget cap for the more aggressive shortening path
  - `5` days as the maximum recovery window

### Why This Is The Correct Boundary

- it advances rescue into a real user-facing surface without reopening intake
- it respects the newly fixed product rule that chat is the primary interaction surface
- it keeps UI in a mirror role and does not open accept-side writeback semantics yet

### Evidence

- `python -m pytest tests/test_rescue_response.py tests/test_rescue_runtime.py tests/test_rescue_proposal.py tests/test_open_proposals_read_model.py -q`
- `python scripts/check_layer_integrity.py`

## 2026-04-15 — `2.5d` Rescue Chat Surface And Proposal Decisions Wired

### Trigger

- after the rescue response builder existed, the next bounded gap was to connect it to a real chat/proactive entrypoint and define how accept / reject should change proposal state

### What Changed

- added a thin `rescue_chat_surface` application layer
- proactive and explicit reactive rescue now share the same open-proposal retrieval and single-plan response surface
- accept now marks the rescue proposal `accepted`
- reject now has two stages:
  - no reason yet -> ask for reason in chat and keep proposal open
  - reason supplied -> mark proposal `rejected` and close it

### Why This Is The Correct Boundary

- it connects `2.5d` to a real chat-facing application entrypoint without mixing rescue into intake routes
- it introduces proposal decision semantics without prematurely doing accept-side rescue overlay writeback
- it preserves the product rule that chat is primary and UI is mirror-only

### Evidence

- `python -m pytest tests/test_rescue_chat_surface.py tests/test_rescue_response.py tests/test_rescue_runtime.py tests/test_open_proposals_read_model.py -q`
- `python scripts/check_layer_integrity.py`

## 2026-04-15 — `2.5d` Accept-Side Rescue Overlay Writeback And Rescue Routes Added

### Trigger

- after the rescue chat surface existed, the next bounded gap was to stop treating accept as metadata-only and connect it to real rescue overlay writeback
- the user also asked to wire rescue into actual web/chat runtime routes instead of keeping it as an application-only surface

### What Changed

- accept on an open rescue proposal now:
  - reads the persisted `overlay_days` payload from the top rescue option
  - applies those overlay deltas into ledger writeback
  - records writeback metadata on the accepted proposal
- added dedicated rescue web/chat routes:
  - route to read the current rescue chat surface
  - route to apply rescue chat actions
- rescue remains on its own route family and is not mixed into intake endpoints

### Why This Is The Correct Boundary

- it preserves the single-plan, chat-first rescue posture
- it upgrades accept from a placeholder state transition into a real rescue effect path
- it keeps intake and rescue separated while still giving rescue a real runtime surface

### Evidence

- `python -m pytest tests/test_rescue_response.py tests/test_rescue_chat_surface.py tests/test_rescue_routes.py tests/test_rescue_runtime.py tests/test_open_proposals_read_model.py -q`
- `python -m pytest tests/test_rescue_overlay.py tests/test_canonical_persistence.py -q -k "rescue"`

## 2026-04-15 — Overnight Checkpoint And `2.5d` Rescue Contract Hardening

### Trigger

- before unattended overnight work, the workspace needed a clean checkpoint boundary
- after the first `2.5d` route/writeback landing, the remaining safe gap was not new product semantics but contract hardening:
  - garbled rescue surface text
  - repeat-action / no-open-proposal behavior
  - reject-with-reason route regression coverage

### What Changed

- created a workspace checkpoint commit before continuing low-risk overnight work
- rewrote the rescue chat/response text layer into clean reviewable Chinese copy without changing the approved product semantics
- hardened `2.5d` route/state behavior for:
  - second accept after proposal close -> `no_open_rescue_proposal`
  - reject with reason -> proposal closes and reason persists
  - post-accept open-proposal read-side stays empty
- expanded targeted rescue tests to cover these regressions

### Why This Is The Correct Boundary

- it improves the rescue branch's reliability and reviewability without reopening any unresolved product decisions
- it stays inside spec-backed route/application/persistence contracts
- it reduces the chance that overnight progress creates text-level noise or repeat-action drift that would force avoidable rework tomorrow

### Evidence

- `python -m pytest tests/test_rescue_response.py tests/test_rescue_chat_surface.py tests/test_rescue_routes.py tests/test_rescue_runtime.py tests/test_open_proposals_read_model.py tests/test_rescue_overlay.py tests/test_canonical_persistence.py -q -k "rescue or overlay or proposal or open_proposal"`
- `python scripts/check_layer_integrity.py`
- `powershell -ExecutionPolicy Bypass -File scripts/check_encoding.ps1 -AuditDocsPolicy`

## 2026-04-15 — Repo-Level User-Facing Mojibake Guard Added

### Trigger

- rescue surface cleanup exposed that garbled text is not only an audit-fixture problem; user-facing application/web/test surfaces also needed a shared prevention wall

### What Changed

- added `scripts/check_user_facing_mojibake.py`
- added `docs/quality/USER_FACING_STRING_GUARD_REGISTRY.json` to define the scanned surfaces:
  - `app/application`
  - `app/web`
  - `tests`
- added `docs/quality/USER_FACING_STRING_GUARD_ALLOWLIST.json` for intentional mojibake test fixtures
- wired the guard into:
  - `.githooks/pre-commit`
  - `.github/workflows/ci.yml`
- documented the guard in `docs/quality/HARNESS_EXECUTION_POLICY.md`

### Why This Is The Correct Boundary

- it upgrades mojibake prevention from local cleanup into a repo-level safety wall
- it stays in the low-risk foundation layer: contract/harness hardening, not product semantics
- it protects the main user-facing string surfaces without turning into a noisy whole-repo unicode policy

### Evidence

- `python scripts/check_user_facing_mojibake.py`
- `python -m pytest tests/test_user_facing_mojibake_guard.py tests/test_rescue_response.py tests/test_rescue_chat_surface.py tests/test_rescue_routes.py -q`
- `python scripts/check_layer_integrity.py`
- `powershell -ExecutionPolicy Bypass -File scripts/check_encoding.ps1 -AuditDocsPolicy`

## 2026-04-15 — `2.5d` Defer Reminder And Thin Reason Bridge Closeout

### Trigger

- `2.5d` still lacked a complete deferred rescue state contract, a 12-hour proactive reminder gate, and a spec-bounded bridge for reject/defer reasons
- the user explicitly decided:
  - defer should keep the proposal pending
  - UI should show the proposal as pending
  - proactive rescue should ask again after 12 hours
  - reject/defer reasons should matter later, but `2.5d` should stop at a thin bridge rather than building full personalized memory

### What Changed

- completed the rescue proposal state machine additions for:
  - `deferred_pending_reminder`
  - reminder-due gating on proactive rescue surface
- added `defer_rescue_plan` to the rescue chat and route action contract
- added a thin reason bridge payload for reject/defer:
  - `raw_reason_text`
  - `reason_hint`
  - `reason_source`
  - `captured_at`
- widened open rescue read-side loading to include deferred-but-still-open rescue proposals
- cleaned rescue user-facing strings in the touched runtime/test surfaces so the new contract is reviewable and guard-compliant

### Why This Is The Correct Boundary

- it finishes the remaining `2.5d` rescue surface state semantics without inventing new product behavior
- it keeps personalization work bounded:
  - `2.5d` stores only a bridge artifact
  - `2.7` remains responsible for durable contextualization and fuzzy reactive routing design
- it preserves the chat-first product posture and UI mirror-only rule

### Evidence

- `python -m pytest tests/test_rescue_response.py tests/test_rescue_chat_surface.py tests/test_rescue_routes.py tests/test_open_proposals_read_model.py tests/test_rescue_runtime.py -q`
- `python -m pytest tests/test_user_facing_mojibake_guard.py -q`

## 2026-04-15 — `2.7a` Semantic Routing Eval Foundation Opened

### Trigger

- the user explicitly approved moving on from `2.5d` into semantic judgment work
- the user also fixed the product posture:
  - UI remains structured/minimal
  - chat remains open-world and should not be hard-limited by UI action vocabulary
  - semantic judgment must remain LLM-led rather than deterministic

### What The Planning Reality Became

- the next bounded branch is not production routing
- it is an eval-first foundation for semantic routing:
  - taxonomy
  - minimal state pack
  - founder-fit benchmark pack
  - runner/oracle
- `2.5d` is now complete enough to act as one source family for semantic-routing cases

### Assumptions That Expired

- "after rescue closeout, the next move should be calibration first"
- "semantic routing can be safely specified as a deterministic action table before evidence exists"

### Next-Phase Corrections

- formalize `2.7a-semantic-routing-eval-foundation`
- keep `2.7a` out of production routing logic
- record that the repo still lacks a canonical `conversation_style_profile` / `sour.md` equivalent
- treat style adaptation as a later `2.7` extension after semantic-routing evidence is stable

### Initial Evidence

- the checked-in founder-fit pack now has:
  - mock evidence that validates the pack/oracle/runner contract
  - an initial live provider run that records broad routing drift across the pack
- this means `2.7a` is doing the intended job:
  - semantic judgment is now visible and reviewable
  - production routing should not be implemented yet

## 2026-04-15 — `2.7b` Semantic Routing Evidence Hardening Selected

### Trigger

- `2.7a` landed the taxonomy, pack, and runner, but the first live eval exposed broad routing drift
- the user explicitly chose to harden semantic-routing evidence next
- the user also approved treating `sour.md` as a good idea only if it stays a dormant extension rather than an active runtime dependency

### What The Planning Reality Became

- the next bounded step is not production routing
- it is evidence hardening:
  - repair corrupted eval artifacts
  - expand founder-fit benchmark coverage
  - cluster live drift into reviewable failure families
  - emit a thin triage artifact per run
- `sour.md` should enter repo truth only as an owner-level dormant note, not as a runtime contract

### Assumptions That Expired

- "after `2.7a`, the next useful move is to start wiring a semantic router"
- "style-profile work should start before semantic-routing evidence is stable"
- "the initial live failures can be interpreted case-by-case without a formal drift triage layer"

### Next-Phase Corrections

- formalize `2.7b-semantic-routing-evidence-hardening`
- keep work inside benchmark docs, eval runner/tests, and owner-level memory truth only
- explicitly forbid deterministic keyword-router shortcuts
- record ambiguity and state-pack insufficiency as first-class triage outputs instead of hiding them inside prompt anecdotes

## 2026-04-15 — `2.7b` Drift-Triage Evidence Landed

### Trigger

- the initial `2.7a` semantic-routing artifacts were not yet sufficient because:
  - the checked-in founder-fit pack and runner/test strings had suffered mojibake in shell-facing review paths
  - live eval still returned a flat `0/12` black-box failure signal

### What Changed

- repaired the semantic-routing founder-fit pack, runner, and targeted tests into clean reviewable UTF-8 artifacts
- expanded the founder-fit pack with:
  - rescue complaint vs true reject
  - defer vs soft not-now complaint
  - explain request vs inquiry
  - follow-up answer vs new intake switch
  - one ambiguity bucket that allows `ask_clarify_before_mutation`
- added drift-triage output to the eval runner so each run now records:
  - `semantic_failure_cluster`
  - mismatch types
  - ambiguity posture
  - state-pack sufficiency
  - provisional hypothesis
- added a dormant `conversation_style_profile` extension note to `L4A` rather than inventing active style runtime

### Evidence

- mock semantic-routing eval now passes cleanly across the expanded pack
- live semantic-routing eval still fails broadly, but no longer as a black box:
  - rescue action family drift
  - intake follow-up continuation drift
  - boundary discrimination drift

### Why This Matters

- the next phase can now target concrete routing/prompt/state-pack problems instead of reacting to one aggregate fail count
- the repo has explicit proof that semantic judgment remains LLM-led and not papered over by deterministic overrides

## 2026-04-15 — `2.7c` Official Text-Surface Guard Hardening Selected

### Trigger

- semantic-routing benchmark packs, runners, and tests were shown to be vulnerable to UTF-8-readable mojibake corruption
- existing guards were too fragmented:
  - markdown policy only protected docs
  - audit fixture safety only guaranteed parseability plus weak text checks
  - user-facing mojibake guard did not cover official benchmark/docs/script surfaces
- the user explicitly asked for a more complete systemic defense before more semantic-routing hardening

### What The Planning Reality Became

- the best next bounded step is not prompt/state-pack work yet
- it is official text-surface guard hardening:
  - shared detector
  - official-surface registry
  - semantic-field fixture validation
  - pre-commit/CI enforcement

### Assumptions That Expired

- "existing mojibake defense is good enough because user-facing surfaces are already guarded"
- "fixture parseability is enough to trust semantic-routing evidence"

### Next-Phase Corrections

- formalize `2.7c-official-text-surface-mojibake-guard-hardening`
- extend the guard wall to official benchmark fixtures, eval docs, runners, and targeted tests
- keep the work entirely inside harness/safety truth
- defer the next semantic-routing prompt/state-pack hardening wave until the official text surfaces are protected

## 2026-04-15 — Rescue Closeout Reviewed; Cut To `2.7d`

### Trigger

- the rescue-side dirty files were inspected as a distinct `2.5d` closeout batch before further semantic-routing work
- UTF-8-explicit inspection showed the rescue user-facing strings are not actually mojibake-corrupted bytes; the earlier concern was shell display noise
- targeted rescue closeout tests passed across chat surface, response, routes, and open-proposal read model
- `2.7c` guard hardening is now complete enough, so the deferred semantic-routing prompt/state-pack wave can legally resume

### What The Review Established

- the rescue dirty files form one coherent `2.5d` closeout cluster:
  - defer reminder contract
  - reject/defer reason bridge
  - proactive reminder-due gating
  - open proposal read-model support for deferred rescue proposals
- no blocking implementation defect was found in that batch during targeted review
- remaining risk is operational, not conceptual:
  - the rescue closeout changes should be reviewed and landed as a distinct `2.5d` commit instead of being mixed into later `2.7` work

### Next-Phase Corrections

- formalize `2.7d-semantic-routing-prompt-state-pack-hardening`
- move the active pointer from guard hardening to semantic-routing prompt/state-pack hardening
- keep `2.7d` LLM-led:
  - use prompt/state-pack and target-vocabulary improvements
  - do not introduce deterministic semantic override tables

## 2026-04-15 — `2.7d` First Hardening Wave Landed

### What Changed

- tightened the semantic-routing eval prompt with explicit canonical target vocabulary:
  - `rescue_proposal`
  - `intake_followup`
  - `new_topic`
- added normalized state-pack shaping so the eval LLM sees active-object descriptors and lane-family hints instead of only raw nested state
- kept the change eval-only:
  - no production routing rewrite
  - no deterministic semantic override

### Evidence Shift

- mock eval remains green: `15/15`
- live eval improved from `0/15` to `11/15`
- the broad workflow-family drift is no longer the main problem
- the remaining failures now concentrate into a small boundary-semantics group:
  - reject vs defer
  - inquiry vs explain
  - complaint vs reject
  - ambiguous `先這樣吧` handling

### Why This Matters

- prompt/state-pack work is now producing measurable semantic-routing gains instead of just better observability
- the next blocker is no longer generic routing drift
- it is product-level boundary semantics that need explicit review

## 2026-04-18 — Active Pointer Shifted From Suite Governance To Budget / Ledger Happy Path

### Trigger

- the repo now has enough suite-governance and runner machinery for the current autonomous wave
- product direction shifted from expanding governance machinery to proving one concrete budget-aware end-to-end trunk
- the chosen trunk is:
  - bootstrap `BodyProfile`
  - seed active `BodyPlan`
  - seed today's `DayBudgetLedger`
  - commit two meals through intake
  - keep `/today`, `/body-plan`, and remaining-budget chat answers reading the same truth

### What Changed

- active execution moved from `2.7d-semantic-routing-prompt-state-pack-hardening` to `0.a-onboarding-ui-and-body-plan-bootstrap`
- a focused companion spec was added:
  - `docs/specs/L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md`
- the implementation trunk now includes:
  - `BodyProfile` persistence
  - deterministic onboarding bootstrap
  - active body-plan read model
  - `/body-plan` surface
  - active-budget fallback for intake ledger writes
  - deterministic remaining-budget answer contract

### Why This Replan Matters

- recommendation, calibration, rescue, and budget-aware chat all depend on a stable budget truth
- `/today` and chat cannot feel coherent if they do not share one deterministic source for target / consumed / remaining
- this branch gives the project one concrete happy path that can be validated before higher-level workflow/pass decisions resume

## 2026-04-15 — Global Routing Governance Spec Added Without Widening `2.7d`

### Trigger

- product review established that the remaining semantic-routing problem is no longer just prompt wording
- the repo needed an explicit governance rule preventing response-side distinctions from being promoted into primary routing taxonomy
- external review also showed that turning `2.7d` into a whole-product routing reset would be premature abstraction and scope drift

### What Changed

- added an independent governance spec:
  - `docs/specs/L6F_GLOBAL_ROUTING_GOVERNANCE_SPEC.md`
- kept `2.7d` as `semantic-routing prompt/state-pack hardening`
- synced the new rule into:
  - `AGENTS.md`
  - `L6E_LLM_PASS_DESIGN_POLICY_SPEC.md`
  - `WORKFLOW_SLICE_REGISTRY.md`
  - `CURRENT_EXECUTION_PLAN.md`

### Governance Outcome

- routing-vs-response boundaries are now explicit repo truth
- anti-premature-taxonomy is now a hard governance rule instead of an implicit conversation norm
- deterministic gates are reaffirmed as legality / structure / safety boundaries only
- the product now has cross-workflow routing guidance without claiming a shared production head router or shared runtime pass graph

### Why This Matters

- future `2.7d` hardening can keep improving prompts and state packs without drifting into response-taxonomy patching
- rescue / calibration / recommendation follow-through can later reuse the same governance rule set without being forced into intake-shaped implementation
- the repo now records the shared principle while explicitly avoiding premature runtime abstraction
