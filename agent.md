# Text Meal Canary Agent Notes

## Goal

This repo is an isolated canary for text meal estimation.
The goal is to shape a reasoning path that generalizes, instead of hand-coding many food answers.

## Default design stance

- Prefer prompt design over hard rules.
- Prefer reasoning steps over case lists.
- Prefer minimal guardrails over category-based routing tables.
- Prefer natural user-facing language over expert-system phrasing.

## Core reasoning path

The model should follow this path:

1. Resolve what the meal is.
2. Resolve the meal components.
3. If components are missing, decide whether the missing composition should come from:
   - the user
   - or external evidence
4. Once components are available, estimate component-level macros.
5. Derive total kcal from macros.
6. If macros are usable, answer.
7. If macros are usable but uncertain, answer first and then explain the uncertainty naturally.

Treat composition resolution and macro estimation as separate stages.

## Implementation approach

- Keep the decision path simple and explicit.
- Use prompts to define the reasoning order, the model's responsibility, and the answer style.
- Use code mainly to wire stages together, normalize outputs, and add small defensive guardrails.
- Prefer prompt changes that improve many similar cases at once.
- Prefer natural follow-up wording that directly asks for the missing food information.
- Prefer the smallest prompt and schema that still preserve reasoning quality and observability.
- Avoid over-engineering the control layer around the model when a clearer prompt or a simpler stage boundary can solve the same problem.

## Lightweight guardrails

Use small guardrails only when they clearly prevent bad behavior:

- return a user-facing answer or a concrete follow-up instead of a raw failure
- treat weak external matches as weak evidence, not final truth
- treat private or home-cooked meals as user-known composition first
- ask one follow-up question at a time

Keep guardrails narrow and defensive. Let the prompt remain the main decision engine.

Do not rely on canned default follow-up questions as the main solution.
When clarification is needed, let the model ask a context-aware question that matches the user's actual input.
Do not patch missing follow-up quality by silently injecting a default question from code.

## Prompt philosophy

When adjusting prompts:

- make the reasoning path clearer
- state what the model should do, in order
- make the output responsibility clearer
- remove unnecessary fields before adding new ones
- prefer fewer stronger instructions over many brittle instructions

Prompt updates should mostly do one of these:

- improve component resolution
- improve the choice between user clarification vs external evidence
- improve macro estimation from known components
- improve natural answer style

## User-facing answer style

- Sound like a helpful assistant, not a nutrition report generator.
- If asking, ask concretely for what is missing.
- If answering with uncertainty, answer first, then explain what part may move the numbers.
- If the user does not need to be blocked, keep the flow moving with an estimate plus a natural uncertainty note.

## Evaluation priority

Judge changes by these questions:

1. Did the model resolve components more correctly?
2. Did it choose the right information source when components were missing?
3. Did it derive macro estimates from components instead of skipping straight to calories?
4. Did it answer naturally?
5. Did the change improve the path without adding brittle rules or unnecessary special cases?
