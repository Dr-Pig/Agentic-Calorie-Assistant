# Web Search Authority Decision Note

## Decision Question

Should `web_search_official` remain lower authority than `exact_item_db`?

## Current Conflict

- code now treats `web_search_official` as lower authority than exact/local truth
- at least one canonical spec still describes official web evidence as belonging to the exact-verified tier

This creates `canonical spec drift`: code truth and spec truth no longer match.

## Option A

`web_search_official` stays below `exact_item_db`

Implications:

- `exact_item_db` remains the top exact-resolution authority
- official web evidence may support grounding, but cannot outrank exact/local truth
- current code direction is correct
- canonical specs must be updated to match

## Option B

`web_search_official` is allowed to share the same authority tier as `exact_item_db`

Implications:

- official search results may behave like exact truth in some retrieval paths
- current code direction is wrong or incomplete
- code must be changed back or reworked
- web-search fallback becomes more permissive and riskier for exactness leakage

## Planner Recommendation

Recommend `Option A`.

Reason:

- search results are still retrieval-plus-extraction outputs, not local exact truth
- they are more vulnerable to variant mismatch, serving-size mismatch, and parsing ambiguity
- this matches the repository's broader rule that web-search fallback must not outrank exact/local truth

## Pending Operator Decision

If the operator approves `Option A`:

- update canonical spec truth to match code
- mark the relevant task `source_of_truth_updated: yes`
- update active execution artifacts so `2.1e` can resume

If the operator rejects `Option A`:

- revert or redesign the current code-level authority mapping before continuing `2.1e`
