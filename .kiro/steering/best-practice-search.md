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

1. Use `remote_web_search` to find current best practices
2. Look for:
   - Official documentation
   - Well-known library patterns
   - Industry standards
3. Apply what you find to your implementation
4. If best practice conflicts with existing code, build the strongest reasonable baseline first, then use eval to converge

## Why This Matters

- Prevents reinventing the wheel
- Ensures modern, maintainable code
- Reduces technical debt
- Aligns with community standards

## Exception

Small, localized changes (typos, comments, formatting) do not require best practice search.