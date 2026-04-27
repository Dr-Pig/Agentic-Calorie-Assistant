# Wave 1 Architecture Transition Ladder

## Purpose

This document defines the staged migration path from the current Wave 1 B-1 and B-2 build shape toward the long-term clean-architecture target.

It exists to answer one practical question:

`When should the repo add seams, when should it invert dependencies, and when should it avoid premature abstraction?`

This is a transition map. It is not a demand for a big-bang refactor.

## Core Position

Wave 1 should not try to become fully plug-and-play through one large rewrite.

The preferred path is:

- keep current product truth and active build momentum intact
- add seams first where B-1 and B-2 are already active
- move ownership boundaries gradually
- formalize ports only after the active behavior has stabilized enough to justify them

This is a staged strangler-style transition, not an all-at-once purity push.

## Best-Practice Basis

The ladder follows the current direction of these sources:

- [OpenAI Reasoning Best Practices](https://platform.openai.com/docs/guides/reasoning-best-practices)
- [OpenAI Retrieval](https://platform.openai.com/docs/guides/retrieval)
- [OpenAI Web Search](https://platform.openai.com/docs/guides/tools-web-search?api-mode=responses)
- [Thinking in LangGraph](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph)
- [Anthropic Tool Use Best Practices](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/define-tools)
- [Microsoft Learn: Common web application architectures](https://learn.microsoft.com/en-us/dotnet/architecture/modern-web-apps-azure/common-web-application-architectures)
- [AWS Prescriptive Guidance: Strangler fig pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/strangler-fig.html)

The external guidance is broadly consistent:

- dependency inversion is valuable, but business logic should not depend on infrastructure details
- retrieval, tools, and search should be bounded by explicit state and contracts
- modernization should prefer incremental extraction over big-bang rewrites

## Non-Goals

This ladder does not authorize:

- full runtime rewrites during active Wave 1 closure
- global prompt framework redesign before the active contracts stabilize
- large RAG or vector retrieval rollout before retrieval intent and packet contracts are real
- replacing current delivery momentum with architecture cleanup theater

## Current Reality Snapshot

Current active truths:

- B-1 has been pushing runtime, transport, branch classification, and tool-loop closure
- B-2 is defining product-intelligence contracts, retrieval intent, packetization, and evidence posture
- provider and model seams exist, but are still partly B-1-local and partly artifact-driven
- prompt and model choice are not yet fully isolated behind durable formal interfaces
- retrieval and packet layers are specified, but not yet fully runtime-owned

The transition ladder exists because these things should not stay ad hoc forever, but they also should not be ripped apart before the active phase stabilizes.

## North-Star Architecture

The desired end state is:

- product contract is model-agnostic
- runtime orchestration is provider-agnostic
- provider adapters are transport-aware, not product-semantic
- retrieval intent is separate from retrieval execution
- evidence packets are separate from synthesis
- logged or draft mapping is separate from evidence posture
- prompt rendering and model/profile selection are swappable seams
- deterministic layers validate, gate, downgrade, and derive, but do not silently replace semantic LLM judgment

## Stage T1 - Lock Current Invariants

### Goal

Protect product truth and prevent more architecture leakage while B-1 and B-2 are still active.

### Add now

- explicit `logged` vs `draft` external outcome boundary
- explicit internal posture vocabulary discipline
- explicit rule that product semantics cannot leak into provider adapters
- explicit rule that deterministic layers do not overwrite completed semantic outputs
- explicit evaluator focus on long-term architecture direction

### Do not do yet

- full port extraction across the entire runtime
- global prompt abstraction overhaul
- generic model-policy framework for every future phase

### Current examples

- B-1 branch-scoped routing remains allowed as local diagnostic policy
- B-2 contract work remains allowed as doc and synthetic truth work
- exactness vocabulary sync is mandatory before deeper B-2 runtime work

## Stage T2 - Add Active-Path Seams

### Goal

Add seams where the repo is already doing real work, without pretending the whole system is ready for generalized plugin architecture.

### Active seams that should be introduced during B-2 P0

- retrieval intent object
- small anchor lookup seam
- structured DB lookup seam
- packet compression seam
- deterministic hard recheck seam
- packet-based synthesis seam
- final logged or draft mapping seam

### Why these seams now

They directly support active B-2 work and reduce future rewrite cost without demanding full-platform abstraction first.

### Rules

- each seam should have one clearly bounded responsibility
- seams should first appear where there is real test pressure
- seam addition must reduce ownership confusion, not create framework ceremony

## Stage T3 - Formalize Provider, Model, and Prompt Boundaries

### Goal

Move from local B-1 tactical seams to more durable runtime boundaries once the product-intelligence path is stable enough.

### Add later, after B-2 packet and mapping layers are stable

- stronger model/profile selection seam
- prompt rendering seam with explicit ownership
- structured decision transport contract separated from product semantics
- packet-based synthesis interface separated from provider transport details

### Trigger

Start this stage only after:

- B-2 contracts are stable
- B-2 packet and recheck behavior are real, not only draft docs
- B-1 local routes are well-understood enough to migrate deliberately instead of copying them forward blindly

### Why not earlier

Doing this too early risks overfitting abstractions to moving behavior.

## Stage T4 - Expand Retrieval Capability

### Goal

Introduce more capable retrieval only when structured lookup and packet policy have already proven what the system is trying to retrieve and why.

### Candidate upgrades

- selected live search seam
- official/brand source retrieval seam
- larger alias corpora
- hybrid lexical plus semantic candidate generation
- eventual large-DB RAG where justified

### Hard trigger

Do not promote to large retrieval or RAG until the repo can already answer:

- what the retrieval intent object is
- how candidates become packets
- how wrong-item and sibling-variant rejection works
- how logged or draft mapping behaves after synthesis

### Reason

If those questions are still unstable, better retrieval only amplifies confusion.

## Stage T5 - Runtime Durability and More Autonomous Loops

### Goal

Use stronger autonomy, detached workers, and possibly richer ReAct-like loops only after the lower-level ownership splits are trustworthy.

### Candidate upgrades

- fuller detached worker pipeline
- stronger checkpoint and resume machinery
- limited autonomous continuation across multiple approved slices
- richer retrieval or search loops
- later proactive or correction-driven refinement loops

### Not before

- B-2 logged or draft behavior is stable
- packet and recheck seams are trustworthy
- architecture boundaries are trace-visible enough to recover from bad runs

## Dependency Inversion Ladder

The repo should not invert everything at once.

Use this order:

1. invert product semantics away from provider details
2. invert retrieval judgment away from raw source mechanics
3. invert synthesis away from raw tool result shape
4. invert model and prompt selection away from runtime core behavior
5. invert higher-volume retrieval infrastructure only when needed

This order reflects the current risk profile:

- product semantics and ownership mistakes are more dangerous than late infrastructure abstraction

## What Must Stay Coupled For Now

Some coupling is still acceptable during Wave 1:

- B-1-local routing patches with explicit attribution
- active provider-profile artifacts used as temporary diagnostic truth
- B-2 contract drafts tied closely to current Wave 1 phase boundaries

Allowed temporary coupling is acceptable only when:

- it is trace-visible
- it is documented as local debt
- it does not become silent product truth

## What Must Be Decoupled Early

These boundaries should be protected now, even before the full architecture matures:

- product semantics from provider behavior
- external logged or draft state from internal evidence posture
- LLM semantic judgment from deterministic hard gating
- retrieval intent from retrieval implementation
- packet usage class from renderer wording

## Human Review Boundaries

The following moments should default to `human_review_required = true`:

- changing logged or draft semantics
- changing exactness or provisional posture meanings
- changing source priority by case type
- introducing a new DB ownership boundary
- formalizing model or prompt seams in a way that changes runtime ownership
- promoting local B-1 patches into general product architecture

## Recommended Near-Term Sequence

The recommended near-term order is:

1. finish the B-2 contract and terminology bridge
2. lock mismatch and packet oracles
3. add retrieval intent object
4. add small anchor and structured lookup seams
5. add packet compression and hard recheck seam
6. only then consider provider/model/prompt seam formalization

Do not jump straight from draft contracts to a global clean-architecture reorganization.

## Decision Table

| Moment | Preferred move | Avoid |
| --- | --- | --- |
| active B-1 or B-2 blocker | narrow local slice with explicit debt note | broad architecture rewrite |
| repeated ownership confusion | add a seam at the active boundary | invent full platform abstraction immediately |
| stable repeated behavior across slices | formalize interface or port | keep copying branch-local logic forever |
| growing retrieval corpus | reassess hybrid/RAG trigger | premature vector-first retrieval |
| strong artifact-proven local routes | document migration target | silently canonize local patch as permanent truth |

## Relation To Other Wave 1 Docs

This ladder works with:

- [docs/specs/WAVE_1_PHASE_B2_ALIGNMENT_AUDIT.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_ALIGNMENT_AUDIT.md)
- [docs/specs/WAVE_1_PHASE_B2_PRODUCT_INTELLIGENCE_ARCHITECTURE_DRAFT.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_PRODUCT_INTELLIGENCE_ARCHITECTURE_DRAFT.md)
- [docs/specs/WAVE_1_PHASE_B2_P0_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_P0_EXECUTION_PLAN.md)
- [docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md)

Read them together as:

- B-2 architecture truth
- B-2 build order
- B-2 current alignment state
- overnight execution governance
- long-term migration order

## Current Recommendation

Wave 1 should continue with transition-first architecture work.

That means:

- no big-bang refactor now
- add real seams where B-2 is already active
- keep B-1 local routes explicitly local until migration timing is justified
- formalize stronger dependency inversion only after the active contracts stabilize

This is the safest way to improve architecture without sacrificing delivery momentum.
