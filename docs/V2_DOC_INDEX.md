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

### Wave 1 唯一入口

所有 V2 Wave 1 implementation 工作，都應從以下文件開始：

`docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md`

不要直接從以下文件開始 implementation：

- Bundle 1 cases
- Bundle 2 cases
- benchmark files
- replay packs
- old L0–L6 docs
- whole-product capability lattice

原因：
- Bundle / benchmark 是 acceptance 或 regression，不是 build order
- whole-product lattice 是 product capability map，不是施工指令
- bootstrap 會引導 coding agent 依正確順序閱讀必要文件

---

## Current Active V2 Files

## 1. Execution / Build Planning

| File | Status | Purpose | Coding Agent Use |
|---|---|---|---|
| `docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md` | Active entrypoint | Wave 1 coding agent 唯一入口 | Start here |
| `docs/specs/V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md` | Active overview | manager/workflow/tool stance, wave plan, test layering | Required via bootstrap |
| `docs/specs/V2_WAVE_1_DEEP_CAPABILITY_SPEC.md` | Active Wave 1 spec | Wave 1 closure, state transitions, guards, harness | Required via bootstrap |
| `docs/specs/V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md` | Active implementation contract | 最小 structured outputs / tool contracts / guard outputs | Required via bootstrap |

---

## 2. Whole-Product Foundation

| File | Status | Purpose | Coding Agent Use |
|---|---|---|---|
| `docs/specs/V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md` | Active foundation | Whole-product capability map | Reference, not entrypoint |
| `docs/quality/V2_FAILURE_TAXONOMY.md` | Active foundation | Failure family vocabulary | Required for fixes |
| `docs/quality/V2_GRADING_RUBRIC.md` | Active foundation | Pass/fail, soft-pass, quality grading | Required for eval interpretation |
| `docs/quality/V2_FOUNDATION_DOCS_EXECUTION_PATCH.md` | Active patch addendum | Evidence-path / fake-pass / Tavily patch queue | Required until merged into foundation docs |

---

## 3. Wave 1 Eval / Micro-Suite Layer

| File | Status | Purpose | Coding Agent Use |
|---|---|---|---|
| `docs/quality/V2_WAVE_1_CAPABILITY_MICRO_SUITES.md` | Active eval design | Wave 1 system-capability micro-suite design | Required via bootstrap |
| `docs/quality/V2_WAVE_1_MICRO_SUITE_CASES.md` | Active eval cases | First MVP micro-suite cases | Required via bootstrap |
| `docs/quality/V2_EVAL_BUNDLE_1_CASES.md` | Active acceptance gate | Bundle 1 product journey acceptance | Use after micro-suite progress |
| `docs/quality/V2_EVAL_BUNDLE_2_CASES.md` | Active acceptance gate | Bundle 2 intake-depth acceptance | Use after micro-suite progress |

---

## 4. Existing Benchmark / Replay Assets

| Asset | Status | Purpose | Coding Agent Use |
|---|---|---|---|
| benchmark v1 | Active regression/reference | Realism / edge regression | Use after bundle readiness |
| benchmark v2 | Active regression/reference | Expanded realism / edge regression | Use after bundle readiness |
| turn2 hybrid replay | Active replay/regression | Multi-turn / same-meal / correction realism | Use after bundle readiness |

These should not be used as implementation order.
They should be remapped to Wave 1 micro-suites and used as regression / anti-overfit gates.

---

## L0–L6 Legacy Handling Policy

### Current finding

GitHub search did not find explicit files named `L0_`, `L1_`, `L2_`, `L3_`, `L4_`, `L5_`, or `L6_` in the indexed repository.

Therefore, this document does **not** directly archive or delete any L0–L6 files.

### Decision rule

If L0–L6 files exist locally or under different filenames, apply the following classification:

## Keep as Active Canonical
Keep a legacy file active only if it contains canonical truth not yet represented in V2 docs.

Examples:
- product object semantics not covered elsewhere
- architecture constraints still binding
- database truth still current

Required action:
- Add a top notice: `ACTIVE CANONICAL REFERENCE — still required by V2 docs`
- Add a link to the relevant V2 doc that depends on it

---

## Keep as Reference Only
Use this for files that remain useful background but should not drive implementation.

Examples:
- old product exploration
- old bundle concepts
- previous eval ideas
- discarded workflow notes that still explain rationale

Required action:
- Add a top notice: `REFERENCE ONLY — do not use as implementation entrypoint`
- Link to `docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md`

---

## Mark as Superseded
Use this for files whose responsibilities are now covered by V2 docs.

Examples:
- old current-wave build plans
- old intake eval plans replaced by Wave 1 micro-suites
- old capability maps replaced by `V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md`

Required action:
- Add a top notice: `SUPERSEDED — replaced by [new V2 file]`
- Do not delete immediately
- Optionally move later to `docs/archive/`

---

## Archive
Archive only when:

- file is clearly superseded
- no canonical truth remains
- coding agent could be confused by it
- user / maintainer has reviewed it

Suggested archive path:

`docs/archive/legacy/`

Do not archive files blindly based on name alone.

---

## Suggested L0–L6 Review Table

When the actual files are identified, classify them with this table:

| Legacy File | Current Status | New Role | Replacement / Reference | Action |
|---|---|---|---|---|
| L0 | unknown | likely active/reference if product objects remain canonical | TBD | inspect before moving |
| L1 | unknown | TBD | TBD | inspect before moving |
| L2 | unknown | TBD | TBD | inspect before moving |
| L3 | unknown | TBD | TBD | inspect before moving |
| L4 | unknown | TBD | TBD | inspect before moving |
| L5 | unknown | TBD | TBD | inspect before moving |
| L6 | unknown | TBD | TBD | inspect before moving |

---

## Current Recommended Canonical Flow

For Wave 1:

1. Start with `V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md`
2. Read execution overview
3. Read Wave 1 deep spec
4. Read micro-suite design
5. Read micro-suite cases
6. Read minimal implementation contracts
7. Use failure taxonomy / rubric / patch addendum for evaluation and fixes
8. Run relevant micro-suites
9. Only then run Bundle 1 / Bundle 2 acceptance cases
10. Use benchmark / replay for regression and realism

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

Do not add more large planning docs before starting Phase A unless a concrete implementation blocker appears.

Next recommended action:

- run coding agent from `V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md`
- ask it to inspect repo and propose Phase A implementation plan
- do not ask it to implement all Wave 1 at once

---

## 歷史

- 2026-04-24: v1 初始版本，建立 V2 文件索引、Wave 1 entrypoint、L0–L6 legacy handling policy
