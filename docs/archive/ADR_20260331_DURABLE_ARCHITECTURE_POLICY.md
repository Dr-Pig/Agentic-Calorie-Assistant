# ADR 2026-03-31: Durable Architecture Policy For Text Meal Canary

## Status

Accepted

## Context

The repo already had a clear LLM-first philosophy:

- prefer stronger prompts and better evidence over thicker control logic
- prefer the smallest path that unlocks LLM capability
- avoid over-engineering

However, this guidance was still too value-shaped.
It did not yet encode hard prohibitions or a mandatory decision order.

That gap allowed local optimization drift:

- search-heavy ideas could be justified because they might help in some cases
- retrieval could expand without first proving durable value
- architecture decisions could optimize around current tool weakness instead of long-term product value

## Decision

We are adopting a durable architecture policy with four hard defaults:

1. raw frontier LLM is the main engine
2. local structured truth is reserved for exact truth, inaccessible official truth, and consistency-critical truth
3. targeted guardrails are reserved for stable failure families
4. search is narrow auxiliary support only, not product core

We are also adopting:

- hard red lines
- a mandatory decision order
- an evaluation gate comparing raw LLM, LLM plus local truth, and LLM plus targeted guardrail

## Consequences

Positive:

- architecture decisions become easier to judge against the north star
- future model improvements are less likely to obsolete the system
- local DB investment is focused on durable product value
- search quality weakness no longer justifies thickening the main path

Trade-offs:

- some seemingly helpful short-term mechanisms will now be rejected
- teams must run clearer evals before adding complexity
- the repo becomes stricter about what kinds of retrieval or search expansion are acceptable

## Why the previous search-heavy direction was a violation

The prior direction violated the intended architecture because:

- it moved search toward the main estimation path
- it increased complexity in response to weak search quality
- it risked building a thicker evidence and control layer around a non-core tool

The problem was not that the north star was missing.
The problem was that the north star was not yet encoded as principles plus prohibitions plus decision order.

## Follow-up

This ADR is implemented by updates to:

- `agent.md`
- `docs/CANARY_NORTH_STAR.md`
- `docs/ARCHITECTURE_CHANGE_CHECKLIST.md`
