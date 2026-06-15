# Coverage Audit

This file maps the runner-backed batch handoff safeguards to the manual Local Handoff package.

## Fully Carried Over

- Compact spec first, then generated documents.
- Compose metrics for spec words, handoff words, expansion ratio, lane count, criterion count, boundary count, complex logic signals, and generated files.
- Self-contained worker prompt.
- Allowed and forbidden path scope.
- Public Evidence Matrix.
- Boundary Examples as executable product requirements.
- Public Boundary Assertion Checklist.
- Hidden/Public Alignment.
- Phase Decomposition Rationale.
- Worker Step Plan.
- Lane split by domain.
- Phase split by normalization/defaulting, core behavior, and downstream aggregation/rendering/persistence/reporting.
- Checkpoint instruction for sequential lanes.
- Public validation commands with cwd, expected exit, and proof statement.
- Python `PYTHONPATH=. python3 -S ...` guidance.
- JavaScript module-type warning.
- Hidden/owner-only checks cannot be worker acceptance criteria.
- Hidden output-shape overreach warning.
- Runner artifact leakage check.
- Worker prompt front-loading for weaker local models.
- Manual audit packet request: changed files, final diff, validation output, acceptance evidence, boundary evidence, blockers.

## Manual Preflight Signals

The checker implements manual equivalents of benchmark/preflight signals:

- `missing_core_file`
- `missing_public_evidence_matrix`
- `missing_boundary_examples`
- `missing_public_boundary_assertion_checklist`
- `missing_phase_decomposition_rationale`
- `missing_hidden_public_alignment`
- `hidden_success_as_worker_acceptance`
- `hidden_output_shape_overreach`
- `runner_artifact_reference`
- `runner_artifact_present`
- `worker_prompt_not_front_loaded`
- `worker_prompt_missing_allowed_paths`
- `worker_prompt_missing_forbidden_paths`
- `worker_prompt_missing_validation`
- `worker_prompt_missing_stop_conditions`
- `worker_prompt_missing_final_format`
- `validation_command_static_check_failed`
- `python_site_path_isolation_gap`
- `js_module_type`
- `consider_worker_step_plan`
- `consider_lane_split`
- `consider_lane_split_from_metrics`
- `consider_complex_logic_decomposition`
- `requires_phase_split_or_rationale`
- `consider_public_type_boundary_examples`
- `consider_public_dict_field_type_boundaries`
- `consider_public_zero_value_boundaries`
- `consider_public_fractional_money_rounding`
- `consider_public_empty_state_downstream_boundary`
- `consider_public_action_branch_coverage`
- `consider_public_action_report_response_boundary`
- `consider_public_report_record_field_normalization`
- `missing_compose_metrics`
- `invalid_compose_metrics`

## Intentionally Not Carried Over

These runner-only mechanisms are excluded because Local Handoff does not launch or supervise workers:

- `batch.json`
- `run-agent-batch.sh`
- Worker process adapters.
- Silent wait contract.
- Worker raw event logs.
- `results/summary.json`
- `results/audit-digest.json`
- `results/final-diff.patch`
- Runner repair packages.
- Hidden command execution by runner.
- `ccusage` snapshots.
- Benchmark aggregate collectors over completed runs.

Manual equivalents are provided through the worker audit packet and `manual-preflight.json`, but completed-code audit is a separate user-triggered workflow.
