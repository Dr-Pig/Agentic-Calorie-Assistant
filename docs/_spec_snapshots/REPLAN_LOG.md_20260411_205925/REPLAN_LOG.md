# Re-plan Log

> [!NOTE]
> This log records reality deviations and phase corrections. If a replan alters the capability dependency order, the change MUST be propagated to **[`WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)**.

## Purpose

This log records implementation reality shifts that require the next-step plan to be corrected.

It should be appended over time instead of rewritten.

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

- `docs/_spec_snapshots/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md_20260411_170502/`
- `docs/_spec_snapshots/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md_20260411_170502/`
- `docs/_spec_snapshots/WORKFLOW_SLICE_REGISTRY.md_20260411_170502/`

## 2026-04-11 — Current Plan Memory Numbering Alignment

### Trigger

- `CURRENT_EXECUTION_PLAN.md` still labeled memory / retrieval next-work as `2.6`, which drifted from the canonical ordering spec where memory / retrieval is `2.7`

### What Was Clarified

- `Next Workflow Focus` now refers to `2.7 Memory / Retrieval Deepening`
- queued `context-selector` placeholder was renumbered to `2.7a-context-selector`
- the correction is numbering-only and does not imply that a new formal slice registry entry has already been authored

### Why It Matters

- prevents future agents from planning memory work under the calibration number
- keeps active execution wording aligned with canonical ordering truth

### Snapshot Record

- `docs/_spec_snapshots/CURRENT_EXECUTION_PLAN.md_20260411_170939/`

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

- "because role vocabulary exists, each domain should expose matching 4-pass structure"
- "recommendation, calibration proposal, and rescue should inherit intake's expanded pass decomposition as default truth"
- "`L6C` can safely act as both routing spec and pass-count authority"

### Why It Matters

- prevents future agents from pattern-matching 4-pass into domains that should be deterministic-first
- preserves intake's unique boundary-splitting responsibility without turning it into a cross-domain template
- gives future spec edits a canonical place to check pass-count, collapse, and deterministic-first policy before changing runtime flow

### Snapshot Record

- `docs/_spec_snapshots/L6D_LLM_PASS_DESIGN_POLICY_SPEC.md_20260411_200135/`
- `docs/_spec_snapshots/L6C_MODEL_ROUTING_PROVIDER_ABSTRACTION_SPEC.md_20260411_200135/`
- `docs/_spec_snapshots/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md_20260411_200135/`
- `docs/_spec_snapshots/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md_20260411_200136/`
- `docs/_spec_snapshots/L3_3B_CALIBRATION_PROPOSAL_POLICY_RUNTIME_CONTRACT_SPEC.md_20260411_200136/`
- `docs/_spec_snapshots/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md_20260411_200136/`
- `docs/_spec_snapshots/index.md_20260411_200137/`
- `docs/_spec_snapshots/CANONICAL_DOCS_MANIFEST.md_20260411_200137/`

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

- `docs/_spec_snapshots/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md_20260411_203256/`
- `docs/_spec_snapshots/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md_20260411_203256/`
- `docs/_spec_snapshots/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md_20260411_203256/`
- `docs/_spec_snapshots/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md_20260411_203257/`
- `docs/_spec_snapshots/L3_3B_CALIBRATION_PROPOSAL_POLICY_RUNTIME_CONTRACT_SPEC.md_20260411_203257/`
- `docs/_spec_snapshots/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md_20260411_203257/`

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

- `docs/_spec_snapshots/AGENTS.md_20260411_210500/`
- `docs/_spec_snapshots/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md_20260411_210500/`
- `docs/_spec_snapshots/TASK_CHECKIN_PROTOCOL.md_20260411_210500/`
- `docs/_spec_snapshots/REPLAN_LOG.md_20260411_210500/`
- `docs/_spec_snapshots/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md_20260411_204024/`
- `docs/_spec_snapshots/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md_20260411_204024/`
- `docs/_spec_snapshots/REPLAN_LOG.md_20260411_204024/`

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

- `docs/_spec_snapshots/L3M_GUARDRAIL_MATH_SPEC.md_20260411_204538/`
- `docs/_spec_snapshots/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md_20260411_204538/`
- `docs/_spec_snapshots/L6C_MODEL_ROUTING_PROVIDER_ABSTRACTION_SPEC.md_20260411_204538/`
- `docs/_spec_snapshots/index.md_20260411_204538/`

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

- `docs/_spec_snapshots/L3M_GUARDRAIL_MATH_SPEC.md_20260411_205346/`
- `docs/_spec_snapshots/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md_20260411_205346/`
- `docs/_spec_snapshots/L6D_REPO_TECH_STACK_CODE_STYLE_SPEC.md_20260411_205346/`
- `docs/_spec_snapshots/REPLAN_LOG.md_20260411_205346/`

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

- `docs/_spec_snapshots/L6D_LLM_PASS_DESIGN_POLICY_SPEC.md_20260411_205522/`
- `docs/_spec_snapshots/L6D_LLM_PASS_DESIGN_POLICY_SPEC.md_20260411_205646/`
- `docs/_spec_snapshots/REPLAN_LOG.md_20260411_205646/`

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

- `pending: wording-cleanup snapshots for L3.2 / L3.3B / L3.4 / REPLAN_LOG`
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

- `docs/_spec_snapshots/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md_20260411_171519/`

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

- `docs/_spec_snapshots/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md_20260411_183000/`
- `docs/_spec_snapshots/AGENTS.md_20260411_183000/`

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

- `docs/_spec_snapshots/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md_20260411_191500/`
- `docs/_spec_snapshots/AGENTS.md_20260411_191500/`

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

- `docs/_spec_snapshots/BUILD_FILE_PLACEMENT_RULES.md_20260411_193500/`
- `docs/_spec_snapshots/LAYER_DEPENDENCY_RULES.md_20260411_193500/`
- `docs/_spec_snapshots/AGENTS.md_20260411_193500/`

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

- `docs/GITHUB_REPO_GOVERNANCE.md` now records required branch protection and required status check names for platform-side enforcement
- `scripts/check_fat_files.ps1` now distinguishes protected legacy files from freeze-growth architecture risk files and a watchlist
- `pytest.ini`, `tests/conftest.py`, and `.github/workflows/ci.yml` now define a layered `smoke` / `integration` / `e2e` test path
- `.github/dependabot.yml` now governs weekly `pip` and `github-actions` updates
- `app/infrastructure/conversation_state_loader.py` now owns retrieval and sync only, while `app/application/conversation_state_assembler.py` owns `ConversationState` assembly
- `scripts/check_task_checkin_and_handoff.ps1` now requires structured completion fields for `COMPLETED` task artifacts

### Implementation Note

- `app/infrastructure/conversation_state_loader.py` required a delete-and-recreate exception during the split because garbled content blocked safe anchor-based patching; ownership was preserved and re-established immediately on the same path

### Snapshot Record

- `docs/_spec_snapshots/AGENTS.md_20260411_201500/`
- `docs/_spec_snapshots/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md_20260411_201500/`
- `docs/_spec_snapshots/TASK_CHECKIN_PROTOCOL.md_20260411_201500/`
- `docs/_spec_snapshots/REPLAN_LOG.md_20260411_201500/`
- `docs/_spec_snapshots/AGENTS.md_20260411_194024/`
- `docs/_spec_snapshots/GITHUB_REPO_GOVERNANCE.md_20260411_194024/`
- `docs/_spec_snapshots/REPLAN_LOG.md_20260411_194024/`

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

- `docs/_spec_snapshots/REPLAN_LOG.md_20260411_200000/`
- `docs/_spec_snapshots/GITHUB_REPO_GOVERNANCE.md_20260411_200000/`
- `docs/_spec_snapshots/AGENTS.md_20260411_200000/`
- `docs/_spec_snapshots/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md_20260411_200000/`

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

- `docs/_spec_snapshots/FREEZE_GROWTH_EXTRACTION_MAP.md_20260411_201500/`
- `docs/_spec_snapshots/index.md_20260411_201500/`
- `docs/_spec_snapshots/REPLAN_LOG.md_20260411_201500/`

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

- `docs/_spec_snapshots/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md_20260411_203256/`
- `docs/_spec_snapshots/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md_20260411_203256/`
- `docs/_spec_snapshots/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md_20260411_203256/`
- `docs/_spec_snapshots/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md_20260411_203257/`
- `docs/_spec_snapshots/L3_3B_CALIBRATION_PROPOSAL_POLICY_RUNTIME_CONTRACT_SPEC.md_20260411_203257/`
- `docs/_spec_snapshots/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md_20260411_203257/`
