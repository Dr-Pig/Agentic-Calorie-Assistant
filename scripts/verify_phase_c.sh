#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PHASE_C_TESTS=(
  "tests/test_environment_verification.py"
  "tests/test_canonical_commit_unit_of_work_adapter.py"
  "tests/test_correction_commit_uow_adapter.py"
  "tests/test_correction_target_reference_state.py"
  "tests/test_no_plan_ledger_policy.py"
  "tests/test_budget_ledger_truth_boundary.py"
  "tests/test_phase_a_current_turn_context.py"
  "tests/test_phase_a_context_direction_lock.py"
  "tests/test_phase_a_manager_payload_wiring.py"
  "tests/test_phase_c_transaction_ports_contract.py"
  "tests/test_phase_c_mutation_projection.py"
  "tests/test_phase_c_same_truth_gate.py"
  "tests/test_phase_a_commit_boundary_preflight.py"
)

GOVERNANCE_COMMANDS=(
  "python scripts/check_layer_integrity.py"
  "python scripts/check_runtime_boundaries.py"
  "python scripts/audit_readiness_claim_integrity.py"
  "python scripts/audit_deterministic_semantic_ownership.py --stage zero-high-risk"
  "python scripts/audit_repo_legacy_surfaces.py"
  "lint-imports --config .importlinter"
  "python scripts/check_markdown_encoding.py --policy-docs --require-bom"
  "git diff --check"
)

run_local() {
  local python_bin="$1"
  local lint_imports_bin="$2"

  "$python_bin" scripts/verify_environment.py
  PYTHONPATH=. "$python_bin" -m pytest "${PHASE_C_TESTS[@]}" -q
  PYTHONPATH=. "$python_bin" scripts/run_wave1_founder_e2e_deterministic_diagnostic.py
  PYTHONPATH=. "$python_bin" scripts/check_layer_integrity.py
  PYTHONPATH=. "$python_bin" scripts/check_runtime_boundaries.py
  PYTHONPATH=. "$python_bin" scripts/audit_readiness_claim_integrity.py
  PYTHONPATH=. "$python_bin" scripts/audit_deterministic_semantic_ownership.py --stage zero-high-risk
  PYTHONPATH=. "$python_bin" scripts/audit_repo_legacy_surfaces.py
  PYTHONPATH=. "$lint_imports_bin" --config .importlinter
  PYTHONPATH=. "$python_bin" scripts/check_markdown_encoding.py --policy-docs --require-bom
  git diff --check
}

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1 && [[ -f "compose.yml" ]]; then
  echo "Using Docker Compose verification runtime."
  docker compose run --rm app python --version
  docker compose run --rm app python -m pytest "${PHASE_C_TESTS[@]}" -q
  docker compose run --rm app python scripts/run_wave1_founder_e2e_deterministic_diagnostic.py
  for command_text in "${GOVERNANCE_COMMANDS[@]}"; do
    docker compose run --rm app ${command_text}
  done
  exit 0
fi

if [[ -x ".venv312/bin/python" && -x ".venv312/bin/lint-imports" ]]; then
  echo "Docker not found. Using .venv312 Python 3.12 fallback."
  run_local ".venv312/bin/python" ".venv312/bin/lint-imports"
  exit 0
fi

if command -v python3.12 >/dev/null 2>&1 && command -v lint-imports >/dev/null 2>&1; then
  echo "Docker and .venv312 not found. Using python3.12 fallback."
  run_local "python3.12" "lint-imports"
  exit 0
fi

cat >&2 <<'EOF'
No authoritative local verification runtime found.

Install Docker, create .venv312 from the repo dependency files, or install
Python 3.12 plus lint-imports on PATH. Python 3.9 is not authoritative for
Phase C active-runtime verification.
EOF
exit 2
