## Required Report

```yaml
track: PLCE
owner_lane: AppShell
slice_class: appshell_contract
pass_type: contract
upstream_runtime_gate: not_applicable
launch_claim_scope: current_shell_candidate_contract
shell_surface_impacted: true
runtime_truth_changed: false
manager_context_packet_changed: false
mutation_changed: false
product_readiness_claimed: false
journeys_touched: A,B,E,J
visible_fact_provenance: read_model,guard,trace
non_claims: not_whole_product_mvp,not_private_self_use_approved,not_live_provider_ready
```

- Keep canonical `track: PLCE`.
- Use `owner_lane` to distinguish `ManagerRuntime`, `AppShell`, or `SharedPLCE`.
- `journeys_touched` and `visible_fact_provenance` are advisory by default, but become required when `pass_type` is `runtime_backed` or `browser_executed`.
- Add `READY_FOR_QUEUE` only after required checks are green and the PR is ready for GitHub Merge Queue.

READY_FOR_QUEUE
