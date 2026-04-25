# V2 Wave 1 Coding Agent Bootstrap

## 目的

本文件是 coding agent 執行 **V2 Wave 1** 工作時的唯一入口文件。

使用方式：

> Start here. Do not begin implementation from Bundle 1 / Bundle 2 cases directly.

本文件不是完整規格本身，而是：

- reading order
- execution order
- anti-fake-pass rules
- Wave 1 implementation guardrails
- micro-suite-first working protocol

coding agent 應先讀本文件，再依本文件列出的順序閱讀必要文件。

---

## 核心指令

Wave 1 的目標不是把 Bundle 1 / Bundle 2 直接 patch 到 green。

Wave 1 的目標是建立：

> plan-or-fallback + meal-thread resolution + evidence-grounded nutrition resolution + ledger sync + same-truth surfaces + trace/artifact governance

請依 system-capability build order 建置，而不是依 product journey 或 bundle case 順序建置。

---

## 必讀文件順序

請按順序閱讀，不要跳過。

### 1. Execution overview
`docs/specs/V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md`

目的：理解 manager style、domain workflows/tools、wave plan、test layering。

### 2. Wave 1 deep spec
`docs/specs/V2_WAVE_1_DEEP_CAPABILITY_SPEC.md`

目的：理解 Wave 1 closure、must-deliver capabilities、must-not-sneak-in boundaries、state transitions、guards、harness contract。

### 3. Micro-suite design
`docs/quality/V2_WAVE_1_CAPABILITY_MICRO_SUITES.md`

目的：理解 Wave 1 system capabilities 如何拆成 micro-suites。

### 4. Micro-suite MVP cases
`docs/quality/V2_WAVE_1_MICRO_SUITE_CASES.md`

目的：理解第一批應實作與驗證的 case-level contracts。

### 5. Minimal implementation contracts
`docs/specs/V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md`

目的：理解 manager decision envelope、tool/workflow result shape、guard result、trace/artifact 最小輸出契約。

### 6. Failure taxonomy
`docs/quality/V2_FAILURE_TAXONOMY.md`

目的：修任何 failure 時，必須標記 primary failure family。

### 7. Grading rubric
`docs/quality/V2_GRADING_RUBRIC.md`

目的：理解 hard fail、soft pass、quality review、founder review 的分層。

### 8. Foundation patch addendum
`docs/quality/V2_FOUNDATION_DOCS_EXECUTION_PATCH.md`

目的：補充 evidence-path、Tavily、fake-pass、tool-correctness 的新增規則。

### 9. Bundle acceptance docs
只在 micro-suite phase 有初步進展後閱讀與執行：

- `docs/quality/V2_EVAL_BUNDLE_1_CASES.md`
- `docs/quality/V2_EVAL_BUNDLE_2_CASES.md`

目的：作為 acceptance gates，不作為 build order。

---

## Wave 1 implementation order

請依下列順序建置與驗證。

## Phase A — Routing & Boundary
先實作與驗證：

1. MS1 Intent / Thread Resolution
2. MS2 Clarify Mode Selection
3. MS7 Draft vs Commit Boundary
4. MS14 No-Plan Fallback Honesty

要求：
- 先讓 system routing / state boundary 穩定
- 不要先 patch Bundle 2 response wording
- 至少暴露 `manager_decision`、`thread_result`、`commit_result`、`guard_result`、`trace_artifact` 的必要欄位

---

## Phase B — Evidence Stack
再實作與驗證：

1. MS3 Evidence Path Selection
2. MS4 Tavily Retrieval Usage
3. MS5 Evidence Normalization
4. MS6 Estimate / Grounding Synthesis

要求：
- Tavily is candidate retrieval, not truth oracle
- Exact DB hit should not go to web search
- Homemade / composition-ambiguous food should usually clarify first, not search
- Retrieved evidence must be normalized before estimate synthesis
- 至少暴露 `selected_evidence_path`、`evidence_packet`、`estimate_result`、Tavily retrieval artifact

---

## Phase C — Mutation & Projection
再實作與驗證：

1. MS8 Correction Integrity & Versioning
2. MS9 Ledger Mutation & Overshoot Truth
3. MS10 Macro Visibility Policy
4. MS11 Same-Truth Read Path
5. MS12 Trace / Artifact Contract
6. MS13 Intake Response Realization

要求：
- Draft must not mutate ledger
- Correction must preserve non-target items
- Overshoot must come from ledger truth
- Chat / UI / later query must reflect the same truth
- No pass claim without artifacts
- 至少暴露 correction version delta、ledger mutation result、macro visibility result、same-truth read result

---

## Acceptance order

### During daily implementation
Run only relevant micro-suites for the changed capability.

### To claim Bundle 1 ready
Run at least:

- MS1
- MS7
- MS9
- MS11
- MS12
- MS14
- Bundle 1 acceptance cases

### To claim Bundle 2 ready
Run at least:

- MS2
- MS3
- MS4
- MS5
- MS6
- MS7
- MS8
- MS9
- MS10
- MS11
- MS12
- MS13
- Bundle 2 acceptance cases

### To claim Wave 1 ready
Run:

1. all MVP micro-suite cases
2. Bundle 1
3. Bundle 2
4. selected benchmark v1/v2 regression set
5. selected turn2 replay regression set

---

## Anti-fake-pass rules

Do not claim pass if any of the following is true:

1. Response text looks correct but product state mutation is missing
2. UI looks correct but ledger / meal_thread artifact is missing
3. Tavily was called but retrieval artifact is missing
4. Search snippet was used directly as final nutrition truth
5. Bundle summary says pass but case-level verdicts are missing
6. A fix targets a benchmark phrase / case id instead of a generalized capability rule
7. A hidden rewrite / repair layer changes output without updating product truth

Every fix should state:

```yaml
primary_failure_family:
changed_capability:
generalized_rule:
affected_micro_suites:
expected_bundle_impact:
```

---

## Manager / workflow / tool stance

Wave 1 should follow:

> single manager orchestration + domain-owned tools/workflows + guards + trace

Manager should own:
- multi-intent coordination
- thread / interaction classification
- clarify posture
- evidence-path selection
- commit decision
- final response planning

Tools / workflows should own:
- exact DB lookup
- generic DB lookup
- Tavily retrieval
- evidence normalization
- estimate synthesis
- ledger read/write
- correction mutation
- trace/artifact writing

Guards should enforce:
- no-plan honesty
- draft isolation
- evidence-path honesty
- Tavily candidate discipline
- macro visibility discipline
- overshoot source truth
- no rescue sneak-in
- no pass without artifacts

---

## Do not sneak in later-wave semantics

Wave 1 must not implement committed semantics for:

- rescue proposal negotiation
- future-day rescue overlays
- calibration proposal acceptance
- recommendation ranking / memory writes
- proactive outreach

Wave 1 may preserve boundaries for these future capabilities, but should not use them to make Wave 1 cases pass.

---

## What to do when a bundle case fails

Do not patch the bundle case directly.

Instead:

1. Identify the failed product behavior
2. Map it to a micro-suite
3. Map it to a failure family
4. Fix the generalized capability contract
5. Rerun the relevant micro-suite
6. Then rerun the bundle case

---

## Minimum implementation report format

When submitting a Wave 1 implementation step, report:

```yaml
implemented_phase:
implemented_micro_suites:
changed_files:
primary_failure_families_addressed:
runner_or_manual_checks:
artifacts:
known_gaps:
next_recommended_step:
```

---

## Definition of Done for this bootstrap

This bootstrap is complete when coding agent can answer:

- What should I read first?
- What should I build first?
- Which tests should I run first?
- What counts as fake pass?
- When can I run Bundle 1 / Bundle 2?
- What should not be implemented in Wave 1?
- What minimal structured contracts must be exposed for verification?

---

## 歷史

- 2026-04-24: v1 初始版本，建立 Wave 1 coding-agent entrypoint、reading order、execution order、anti-fake-pass protocol
- 2026-04-24: v1.1 補入 `V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md` 作為必讀文件與各 phase 的最小 contract 要求
