# Coverage Audit

This file maps the runner-backed batch handoff safeguards to the manual Local Handoff package.

## Fully Carried Over

- Compact spec first, then generated documents.
- Spec lint before composition, including unknown-key detection for acceptance/boundary typos.
- Compose metrics for spec words, handoff words, expansion ratio, lane count, criterion count, boundary count, complex logic signals, and generated files.
- Self-contained worker prompt.
- Embedded relevant code excerpts for target functions, types, helper APIs, and tests when local exploration is weak.
- Worker capability knob for small, medium, and large local models.
- Explicit anti-patterns against guessed APIs, scope creep, test masking, skipped validation, and continuing past blockers.
- Bounded self-repair loop: change, validate, scoped repair, rerun, completed or blocked.
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
- Canonical task tracker coverage with exactly-once lane ownership, dependency ordering, and task-ID evidence.
- Worker-visible `manual-handoff-spec.json` for runner discovery, with owner-only notes removed.
- Public validation commands with cwd, expected exit, and proof statement.
- Root lint command enforcement when the repo defines one.
- False-green runtime guard for fatal output such as `EADDRINUSE` despite exit code 0.
- Python `PYTHONPATH=. python3 -S ...` guidance.
- JavaScript module-type warning.
- Hidden/owner-only checks cannot be worker acceptance criteria.
- Hidden output-shape overreach warning.
- Runner artifact leakage check.
- Worker prompt front-loading for weaker local models.
- Manual audit packet request: changed files, final diff, validation output, acceptance evidence, boundary evidence, blockers.

## Manual Preflight Signals

The checker implements manual equivalents of benchmark/preflight signals:

- `missing_handoff_file`
- `missing_package_dir`
- `missing_readme`
- `placeholder_left`
- `unfilled_validation_placeholder`
- `package_relative_handoff_refs`
- `missing_public_evidence_matrix`
- `missing_boundary_examples`
- `missing_public_boundary_assertion_checklist`
- `missing_phase_decomposition_rationale`
- `missing_hidden_public_alignment`
- `unspecified_acceptance_content`
- `missing_public_validation`
- `missing_allow_paths`
- `missing_forbid_paths`
- `hidden_success_as_worker_acceptance`
- `hidden_runner_evidence_in_acceptance`
- `hidden_evidence_in_public_matrix`
- `hidden_without_comparable_public`
- `hidden_contract_check`
- `hidden_output_shape_overreach`
- `runner_artifact_reference`
- `runner_artifact_present`
- `missing_benchmark_quality_gates`
- `missing_weak_worker_failure_modes`
- `worker_prompt_not_front_loaded`
- `worker_prompt_missing_allowed_paths`
- `worker_prompt_missing_forbidden_paths`
- `worker_prompt_missing_validation`
- `worker_prompt_missing_stop_conditions`
- `worker_prompt_missing_final_format`
- `worker_prompt_missing_code_excerpts`
- `worker_prompt_missing_anti_patterns`
- `worker_prompt_missing_self_repair_loop`
- `worker_prompt_missing_worker_capability`
- `missing_embedded_code_excerpt_blocks`
- `missing_no_api_guessing_antipattern`
- `missing_no_test_masking_antipattern`
- `self_repair_loop_missing_blocked_exit`
- `validation_command_static_check_failed`
- `python_import_path_gap`
- `python_packaging_scope_gap`
- `python_site_path_isolation_gap`
- `js_module_type`
- `vague_acceptance_without_example`
- `consider_worker_step_plan`
- `consider_lane_split`
- `consider_lane_split_from_metrics`
- `consider_complex_logic_decomposition`
- `requires_phase_split_or_rationale`
- `requires_lane_split`
- `requires_phase_split`
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
- `canonical_task_file_missing`
- `canonical_task_file_empty`
- `lane_missing_task_ids`
- `invalid_lane_dependency`
- `duplicate_task_assignment`
- `unknown_task_assignment`
- `unassigned_required_tasks`
- `root_lint_validation_missing`
- `missing_machine_readable_spec`
- `invalid_machine_readable_spec`
- `missing_canonical_task_coverage`
- `missing_false_green_runtime_guard`

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
- `invalid_review_policy`
- `review_policy_skip_without_hidden_validation`
- `worker_process_failure_advisory`

Manual equivalents are provided through the worker audit packet and `manual-preflight.json`, but completed-code audit is a separate user-triggered workflow.
