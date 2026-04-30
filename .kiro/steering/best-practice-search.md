---
inclusion: auto
fileMatchPattern: "**/*.py"
---

# Best Practice Search Guidance

Before implementing any code, search for current best practices. This is mandatory for high-impact work.

## When to Search

Search for best practices when working on:

- **Agent runtime** — manager, tools, tool orchestration, structured extraction
- **Retrieval** — RAG, knowledge lookup, context packing
- **Database** — ORM patterns, migrations, query optimization
- **API design** — REST/GraphQL patterns, error handling
- **Testing** — test patterns, mocking, fixtures
- **Security** — authentication, authorization, input validation

## How to Search

1. Use the available web/search tool in the current environment. If `remote_web_search` is unavailable, use the repository-approved browsing/search tool instead.
2. Prefer official or primary sources first, especially vendor docs for agent runtime, retrieval, tool orchestration, structured outputs, database, API, testing, and security work.
3. Look for:
   - Official documentation
   - Well-known library patterns
   - Industry standards
4. Apply what you find to your implementation.
5. If best practice conflicts with existing code, build the strongest reasonable baseline first, then use eval to converge.
6. Record the search in the implementation plan under `best_practice_evidence`, including sources checked, adopted guidance, rejected guidance, conflicts with repo habits, and how the design changed.

## Stop Condition

For high-impact work, missing `best_practice_evidence` is a planning failure. Do not proceed to implementation until current best-practice or official-reference evidence is recorded.

## Why This Matters

- Prevents reinventing the wheel
- Ensures modern, maintainable code
- Reduces technical debt
- Aligns with community standards

## Exception

Small, localized changes (typos, comments, formatting) do not require best practice search.
