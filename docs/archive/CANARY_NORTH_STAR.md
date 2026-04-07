# Canary North Star

## Goal

Build a calorie-estimation system that stays useful as frontier models improve.

This repo is not trying to outsmart a frontier LLM with a thicker and thicker control stack.
It is trying to build a thin, durable system that:

1. lets a strong LLM do what it is already good at
2. adds exact truth where the LLM cannot reliably own the answer
3. adds targeted help for stable failure families

## North star

The main objective is:

- amplify LLM capability
- keep deterministic help narrow and durable
- avoid architecture that becomes obsolete as models get stronger

The system should remain rational 3-5 years from now, not only for the current model generation.

## Durable architecture policy

### 1. Raw frontier LLM is the main engine

By default, the LLM should own:

- general calorie estimation
- common foods
- compositional meal reasoning
- approximate portion reasoning

We do not add retrieval, search, or control logic by default just because they might help in theory.

### 2. Local structured truth exists for durable gaps

Local DB is justified when it solves a problem that remains valuable even if the base model improves:

- exact branded items
- chain and convenience-store items
- inaccessible official nutrition truth
- PDF or hard-to-consume official pages normalized into structured records
- product consistency where the app needs stable, repeatable output

Local DB is not meant to replace the LLM on ordinary food reasoning.

### 3. Targeted guardrails exist for stable failure families

Guardrails are justified when the model shows a repeated, narrow, and durable error pattern.

Examples:

- Japanese ramen or rich-broth ramen underestimation
- ambiguous portion or serving-size cases that should trigger stronger follow-up

Guardrails are not a license to build broad food-specific control logic.

### 4. Search is non-core

Search is not the product core for this app.

Default stance:

- if search quality is weak, do not thicken the main path around it
- use search only as narrow auxiliary support
- do not make search the default estimator or default evidence source

## Hard red lines

These are default prohibitions.

- Do not add search to the default calorie-estimation path.
- Do not add retrieval just because "more evidence might help."
- Do not build deterministic semantic layers that compete with the model on general food understanding.
- Do not add mechanisms whose only purpose is patching a temporary current-model weakness unless they also create durable product value.
- Do not let planner, route, gate, or heuristic complexity exceed the main LLM answer path.

## Decision order

Every architecture proposal must follow this order:

1. Ask whether a raw frontier LLM already does this well enough.
2. If not, classify the gap:
   - exact truth gap
   - systematic failure-family gap
   - product consistency gap
3. Only exact truth, inaccessible official truth, or consistency-critical truth justify local structured data.
4. Only stable, repeated failure families justify targeted guardrails.
5. Search is considered last, and only as narrow support.

If a proposal cannot be defended in this order, it is not aligned with the canary north star.

## Ownership model

### Raw frontier LLM owns

- common meal estimation
- general food understanding
- composition and portion reasoning by default

### Local DB owns

- exact packaged or branded truth
- chain menu truth
- convenience-store truth
- normalized official nutrition pages and PDFs

### Targeted guardrails own

- stable known biases
- stronger follow-up on ambiguity when the model tends to smooth toward an unsafe middle estimate

### Search owns

- optional support for narrow high-value lookup
- never the primary estimator

## Failure family registry

Initial registry:

1. Japanese ramen or rich-broth ramen underestimation
2. Ambiguous portion or serving-size ambiguity that should trigger stronger follow-up
3. Exact chain or packaged item mismatch when structured truth exists

Any new guardrail should map to a concrete failure family, not to a vague hope that "more control" will improve quality.

## Evaluation gate

Any new architecture mechanism must be evaluated against a fixed set that compares:

- `raw frontier LLM`
- `LLM + local truth`
- `LLM + targeted guardrail`

Reject the mechanism if:

- complexity rises without measurable improvement on the target failure family
- it mainly compensates for poor search quality by adding orchestration thickness
- it would likely become obsolete after a strong model upgrade

Re-run the same eval set whenever the base model changes materially.

## Eval set buckets

The canonical eval set should include at least:

- common foods
- exact branded or chain items
- ramen or oily broth foods
- ambiguous portion cases
- Taiwan-local foods where search is historically weak

## Intended route shape

Current route shape:

- `raw input -> Planner LLM -> route executor -> optional retry`

Estimation route:

- Planner output
- risk gate
- main LLM answer pass
- minimal deterministic enrichment
- retry only on quality fail

Search is not part of the default estimation path.

## Search strategy

Search remains non-core unless quality changes materially.

Current guidance:

- prefer exact structured truth over broad search expansion
- prefer failure-family guardrails over search-heavy recovery logic
- if search is explored in the future, begin with a narrow nutrition-source layer rather than a generic search engine

Preferred future path if search becomes worth deeper investment:

1. trusted nutrition-source registry
2. PDF extraction and normalization
3. official menu and nutrition source ingestion
4. only then broader AI-search infrastructure

Current external options for future reference:

- Tavily: cheap baseline, not strong enough to be assumed product core today. Source: [Tavily pricing](https://help.tavily.com/articles/8816424538-pricing)
- Brave Search API: lower-cost general web search candidate. Source: [Brave pricing](https://api-dashboard.search.brave.com/documentation/pricing)
- SerpApi: stronger SERP coverage, higher cost. Source: [SerpApi pricing](https://serpapi.com/pricing)
- Exa: AI-oriented search and page-read model, more research-shaped than estimation-shaped. Source: [Exa docs](https://docs.exa.ai/reference/exa-research)
- Google Custom Search JSON API: legacy path only, not the forward-looking default. Source: [Google overview](https://developers.google.com/custom-search/v1/overview)

## Practical reading of this north star

When deciding whether to build something, ask:

1. Is the raw LLM already good enough here?
2. If not, is the missing value exact truth, a stable failure-family fix, or consistency?
3. Will this still make sense if the base model is much better in 1-3 years?

If the answer is no, do not build it.
