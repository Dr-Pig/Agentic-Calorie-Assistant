# V2 Documentation Index

## 目的

本文件是 V2 文件系統的索引與治理說明。

它回答：

- coding agent 應從哪份文件開始
- 哪些文件是 active / canonical / reference / legacy
- Wave 1 的建置文件與 eval 文件如何分層
- 舊的 L0–L6 文件應如何處理
- 哪些文件不應再作為 implementation entrypoint

---

## Coding Agent Entry Point

### Product-wide anti-drift entry

所有高影響 implementation slice，先讀：

`docs/specs/APP_V2_ENGINEERING_OPERATING_ENTRY.md`

它的角色是：

- product-wide operating layer
- anti-drift entrypoint
- owner docs / phase bootstrap 的讀取橋樑
- high-impact slice 的 planning checklist 與 forbidden shortcuts
- capability dependency build order guardrail for future slice selection

它不是 phase build order，也不是完整產品規格。

`AGENTS.md` and `APP_V2_ENGINEERING_OPERATING_ENTRY.md` now jointly enforce the rule that implementation order follows capability dependency order, not bundle order, benchmark order, product journey order, or local slice momentum.

### Wave 1 phase bootstrap

所有 V2 Wave 1 implementation 工作，在讀完 product-wide operating entry 後，再進入以下 phase bootstrap：

`docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md`

不要直接從以下來源開始 implementation：

- deleted legacy Bundle Version 1 / Bundle Version 2 cases
- benchmark files
- replay packs
- old L0–L6 docs
- whole-product capability lattice

原因：

- legacy Bundle / benchmark 是 historical acceptance 或 regression，不是 build order
- whole-product lattice 是 product capability map，不是施工指令
- operating entry 會先鎖定 anti-drift operating rules
- phase bootstrap 會再引導 coding agent 依正確順序閱讀 Wave 1 必要文件

---

## Current Active V2 Files

## 1. Product-Wide Operating Entry

| File | Status | Purpose | Coding Agent Use |
|---|---|---|---|
| `docs/specs/APP_V2_ENGINEERING_OPERATING_ENTRY.md` | Active operating entry | Product-wide anti-drift operating layer | Read before high-impact slices |

---

## 2. Execution / Build Planning

| File | Status | Purpose | Coding Agent Use |
|---|---|---|---|
| `docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md` | Active phase bootstrap | Wave 1 coding agent phase-specific entrypoint | Read after operating entry |
| `docs/specs/V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md` | Active overview | manager/workflow/tool stance, wave plan, test layering | Required via bootstrap |
| `docs/specs/V2_WAVE_1_DEEP_CAPABILITY_SPEC.md` | Active Wave 1 spec | Wave 1 closure, state transitions, guards, harness | Required via bootstrap |
| `docs/specs/V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md` | Active implementation contract | 最小 structured outputs / tool contracts / guard outputs | Required via bootstrap |

---

## 3. Whole-Product Foundation

| File | Status | Purpose | Coding Agent Use |
|---|---|---|---|
| `docs/specs/V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md` | Active foundation | Whole-product capability map | Reference, not entrypoint |
| `docs/quality/V2_FAILURE_TAXONOMY.md` | Active foundation | Failure family vocabulary | Required for fixes |
| `docs/quality/V2_GRADING_RUBRIC.md` | Active foundation | Pass/fail, soft-pass, quality grading | Required for eval interpretation |
| `docs/quality/V2_FOUNDATION_DOCS_EXECUTION_PATCH.md` | Active patch addendum | Evidence-path / fake-pass / Tavily patch queue | Required until merged into foundation docs |

---

## 4. Wave 1 Eval / Micro-Suite Layer

| File | Status | Purpose | Coding Agent Use |
|---|---|---|---|
| `docs/quality/V2_WAVE_1_CAPABILITY_MICRO_SUITES.md` | Active eval design | Wave 1 system-capability micro-suite design | Required via bootstrap |
| `docs/quality/V2_WAVE_1_MICRO_SUITE_CASES.md` | Active eval cases | First MVP micro-suite cases | Required via bootstrap |
| Manager-style Founder E2E diagnostics | Active acceptance evidence | Active runtime / manager contract acceptance | Use after micro-suite progress |
| Wave 1 B1/B2 capability harnesses | Active capability evidence | Manager/tool-loop and B2 evidence-stack checks | Use as capability gates, not legacy bundle truth |

---

## 5. Existing Benchmark / Replay Assets

| Asset | Status | Purpose | Coding Agent Use |
|---|---|---|---|
| benchmark v1 | Active regression/reference | Realism / edge regression | Use after manager-style capability readiness |
| benchmark v2 | Active regression/reference | Expanded realism / edge regression | Use after manager-style capability readiness |
| turn2 hybrid replay | Active replay/regression | Multi-turn / same-meal / correction realism | Use after manager-style capability readiness |

These should not be used as implementation order.
They should be remapped to Wave 1 micro-suites and used as regression / anti-overfit gates.

---

## Legacy / L-Series Handling

## Important Note

This repo contains older L-series specs that still include canonical truth. They should not be blindly archived.

The correct handling is:

- keep canonical L-series specs as upstream reference
- do not use L-series specs as Wave 1 implementation entrypoint
- mark superseded routing/pass-era specs as archive/reference only
- use `V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md` as the active Wave 1 coding entrypoint

---

## Concrete L-Series Decisions So Far

The following files have been inspected or identified from existing canonical docs / implementation plan.

| Legacy File | Status | New Role | Replacement / Reference | Action |
|---|---|---|---|---|
| `docs/specs/L0_PRODUCT_CAPABILITY_SPEC.md` | Active canonical reference | Product semantics, shared product objects, chat/UI product model | Referenced by V2 lattice and execution plan | Keep; do not archive |
| `docs/specs/L0A_ONBOARDING_FLOW_SPEC.md` | Active canonical reference for onboarding | Onboarding fields, BodyPlan bootstrap, no-onboarding fallback | Referenced by Wave 1 F1 / intake-entry readiness | Keep; do not archive |
| `docs/specs/L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md` | Active canonical reference for budget happy path | BodyPlan → DayBudgetLedger → chat/UI shared truth | Referenced by Wave 1 F3 / intake readiness | Keep; do not archive |
| `docs/specs/app_v2_ideal_architecture_final.md` | Active canonical architecture truth | Business-domain-first modular monolith and layer rules | Required by bootstrap and implementation plan | Keep; do not archive |
| `docs/specs/APP_V2_IMPLEMENTATION_PLAN.md` | Active repo-aware implementation plan, but partially older bundle framing | Repo reality, existing module evidence, bundle/tool history, EDD stage guardrails | Use as architecture/repo evidence, not as current Wave 1 build order | Keep; update only if actively misleading |
| `docs/specs/L3_1_INTAKE_RUNTIME_CONTRACT_SPEC.md` | Active canonical intake runtime contract | Single-manager intake shape, tool batch, guard, sidecar, sync rules | Aligns strongly with Wave 1 specs and minimal contracts | Keep; do not archive |
| `docs/specs/L4A_MEMORY_MODEL_SPEC.md` | Active later-wave canonical reference | Memory layers, preference memory, consolidation, style-profile extension note | Required before Wave 3 / memory work | Keep; not required for Wave 1 Phase A except as reference |
| `docs/specs/L4B_RETRIEVAL_POLICY_SPEC.md` | Active canonical retrieval policy | Typed-first retrieval, web search retrieval policy, source/evidence classification | Useful for Wave 1 Phase B evidence/Tavily work | Keep; do not archive |
| `docs/specs/L6F_GLOBAL_ROUTING_GOVERNANCE_SPEC.md` | Superseded / archive according to implementation plan | Old router governance | Replaced by single-manager + semantic routing governance | Do not use as active implementation truth |
| `docs/specs/L6G_MULTI_DISPATCH_SEQUENTIAL_CHAINING_SPEC.md` | Superseded / archive according to implementation plan | Old multi-dispatch / sequential chaining framing | Replaced by single-manager orchestration + domain workflows/tools | Do not use as active implementation truth |
| `docs/specs/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md` | Superseded / archive according to implementation plan | Old pass-centered design policy | Replaced by single-manager frame | Do not use as active implementation truth |

---

## L-Series Still Needing Local Confirmation

Some files are referenced by canonical specs but were not directly fetched through the GitHub connector in this audit. They should be inspected locally before any archive/move action.

| Referenced File | Likely Role | Recommended Action |
|---|---|---|
| `docs/specs/L2_DATA_STATE_SPEC.md` | Canonical data/state model | Keep if exists; likely active canonical |
| `docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md` | Calibration model | Keep for Wave 2 |
| `docs/specs/L3_3B...` | Calibration proposal / body plan proposal gate if exists | Keep for Wave 2 if canonical |
| `docs/specs/L3_4...` | Rescue logic / safety floor / proposal flow if exists | Keep for Wave 2 |
| `docs/specs/L4C...` | Context packing / retrieval context ordering if exists | Keep as reference; maybe active for manager context |
| `docs/specs/L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md` | Memory lifecycle details | Keep for Wave 3 |
| `docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md` | Workflow/context dependency order | Keep as reference if still aligned |
| `docs/quality/L5A_EVAL_SPEC.md` | Eval policy | Compare with V2 grading/micro-suite docs before deciding |
| `docs/quality/BENCHMARK_CASE_SCHEMA.md` | Benchmark schema | Keep if current benchmark runner still uses it |

Do not archive these until inspected.

---

## Superseded Content Rule

Superseded material should not be kept as repo-visible agent truth. Remove it only if all are true:

1. It no longer contains unique canonical product / architecture / data / eval truth
2. Its responsibility is clearly replaced by a V2 file
3. It is not required by tests, scripts, or active docs
4. User / maintainer confirms the deletion

If preservation is required, use an external snapshot outside the active repo truth path.

```md
> SUPERSEDED / DELETION CANDIDATE
> Do not use as implementation entrypoint.
> Current replacement: <new V2 file>
```

---

## Current Recommended Canonical Flow

For Wave 1:

1. Start with `APP_V2_ENGINEERING_OPERATING_ENTRY.md`
2. Enter `V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md`
3. Read execution overview
4. Read Wave 1 deep spec
5. Read micro-suite design
6. Read micro-suite cases
7. Read minimal implementation contracts
8. Use failure taxonomy / rubric / patch addendum for evaluation and fixes
9. Run relevant micro-suites
10. Only then run Manager-style E2E diagnostics
11. Use benchmark / replay for regression and realism

---

## Rules for Future Docs

### Add a new document only when it answers a distinct question
Good reasons:
- new wave deep spec
- new tool contract layer
- new eval suite
- new production readiness concern

Bad reasons:
- repeating a concept already covered
- creating another overview without a new role
- making a large doc before current wave needs it

### Every new doc must declare
- purpose
- non-goals
- upstream docs
- downstream use
- whether coding agent should read it

---

## Current Stop Point

As of 2026-04-24, Wave 1 has enough documents to begin implementation.

Do not add more large planning docs before starting Phase A unless a concrete implementation blocker appears. Thin operating-entry or governance-linking docs are acceptable when they reduce repeated architecture drift and do not duplicate existing owner semantics.

Next recommended action:

- run coding agent from `APP_V2_ENGINEERING_OPERATING_ENTRY.md`, then `V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md`
- ask it to inspect repo and propose Phase A implementation plan
- do not ask it to implement all Wave 1 at once

---

## 歷史

- 2026-04-24: v1 初始版本，建立 V2 文件索引、Wave 1 entrypoint、L0–L6 legacy handling policy
- 2026-04-24: v1.1 補入已定位 L-series 文件的具體保留 / superseded 判斷
