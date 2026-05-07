## Required Report

```yaml
track: fill_me
owner_lane: none
slice_class: governance
pass_type: contract
upstream_runtime_gate: not_applicable
launch_claim_scope: none
shell_surface_impacted: false
runtime_truth_changed: false
manager_context_packet_changed: false
mutation_changed: false
product_readiness_claimed: false
journeys_touched:
visible_fact_provenance:
non_claims: not_whole_product_mvp,not_private_self_use_approved,not_live_provider_ready
```

- Use canonical `track: CurrentShell` for current-shell work.
- Use `track: FoodDB` or `track: MergeGovernance` for those independent tracks.
- Use `owner_lane` only for `CurrentShell` work to distinguish `ManagerRuntime`, `AppShell`, or `SharedCurrentShell`; otherwise leave `owner_lane: none`.
- `journeys_touched` and `visible_fact_provenance` are advisory during the initial CurrentShell cutover and become stricter only when later gates require them.
- Add `READY_FOR_QUEUE` only after required checks are green and the PR is ready for GitHub Merge Queue.
