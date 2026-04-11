# GitHub Repo Governance

## Purpose

This document records the GitHub platform settings that must be enabled outside the repository so repo-level checks actually gate merges.

Repo files can define workflows and scripts, but they cannot enforce branch protection by themselves.

## Required Branch Protection

Apply these settings to the default protected branch, expected to be `main`:

- require a pull request before merging
- require approval reviews before merging
- require conversation resolution before merging
- disallow merges that bypass required status checks
- disallow direct pushes except for approved administrators if your org policy requires it

## Required Status Checks

The following check names must be required:

- `layer-integrity`
- `smoke-tests`
- `integration-tests`

If workflow job names change, this document must be updated in the same governance change.

## Platform-Level Hygiene

Enable or confirm:

- Dependabot version updates
- Dependabot updates for GitHub Actions
- pull request review workflow for repo changes that affect governance or CI

## Repo Relationship

This document complements:

- [`AGENTS.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md)
- [`docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md)
- [`docs/TASK_CHECKIN_PROTOCOL.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/TASK_CHECKIN_PROTOCOL.md)

It does not replace repo-local gates; it ensures they become merge requirements instead of advisory automation.
