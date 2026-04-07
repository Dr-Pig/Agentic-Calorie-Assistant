# Model Allocation

## Current BuilderSpace Allocation

The canonical 4-pass runtime now supports independent BuilderSpace model slots:

- `BUILDERSPACE_TASK_MEAL_LINK_MODEL`
- `BUILDERSPACE_DECISION_MODEL`
- `BUILDERSPACE_NUTRITION_MODEL`
- `BUILDERSPACE_FINAL_RESPONSE_MODEL`

Legacy compatibility keys still exist:

- `BUILDERSPACE_PLANNER_MODEL`
- `BUILDERSPACE_PRIMARY_MODEL`

The new pass-specific keys take precedence.

## Current Recommended Default

Current repo default is:

- `task_meal_link_pass = grok-4-fast`
- `decision_pass = grok-4-fast`
- `nutrition_resolution_pass = grok-4-fast`
- `final_response_pass = grok-4-fast`

## Why

- `task_meal_link_pass` is cheap enough that using the same higher-quality model avoids boundary regressions.
- `decision_pass` and `nutrition_resolution_pass` are the highest-value reasoning stages.
- `final_response_pass` strongly affects perceived assistant quality and should not be downgraded first.

## Stage Mapping

BuilderSpace stage-to-model mapping:

- `task_meal_link_pass` -> task/meal-link model
- `decision_pass` -> decision model
- `nutrition_resolution_pass_initial` -> nutrition model
- `nutrition_resolution_pass_tool_round_2` -> nutrition model
- `final_response_pass` -> final-response model

Legacy stage aliases still map sensibly for compatibility:

- `planner_pass_initial` -> task/meal-link model
- `primary_answer_pass_initial` -> nutrition model
- `primary_answer_pass_tool_round_2` -> nutrition model

## Rule

Do not reduce LLM call count by collapsing pass responsibilities.

If cost tuning is needed, tune model assignment first, not runtime layering.
