# Manual External-Agent Handoff Contract

## Purpose

This contract makes Codex a document author for manual delegation. The human user will copy, upload, or otherwise provide the generated handoff to a local or external worker. There is no Codex-owned runner, no silent wait, and no Codex final audit loop unless the user separately requests one later.

Optimize for worker correctness, not token minimization. A long but precise handoff is better than a short handoff that forces a weaker local model to infer behavior.

## Compact Spec First

Prefer creating a compact JSON spec and expanding it with `scripts/compose_manual_handoff.py` before manually refining prose. This saves Codex authoring tokens while preserving a detailed worker-facing package.

Common spec fields:

```json
{
  "task_name": "short task name",
  "repo": "/absolute/path/to/repo",
  "objective": "one concrete end state",
  "context": "repo and behavior context",
  "allowed_paths": ["src/example.py"],
  "forbidden_paths": ["pyproject.toml", "*.egg-info/**"],
  "criteria": [
    {
      "requirement": "required behavior",
      "evidence": "public validation or manual audit",
      "effect": "observable output/effect"
    }
  ],
  "boundaries": [
    {
      "case": "invalid or missing input",
      "expected": "expected downstream result",
      "evidence": "public validation or manual audit"
    }
  ],
  "validation_commands": [
    {
      "cwd": "/absolute/path/to/repo",
      "command": "PYTHONPATH=. python3 -S tests/check_behavior.py",
      "expected_exit": 0,
      "proves": "acceptance criteria covered by this command"
    }
  ],
  "worker_steps": [
    "Inspect target files and current behavior.",
    "Implement normalization/defaulting first.",
    "Implement core behavior.",
    "Run configured validation and report evidence."
  ],
  "phase_decomposition_rationale": "why this is split into lanes or safe as one lane",
  "hidden_public_alignment": "owner-only checks absent, or how they are mirrored into public acceptance/manual audit"
}
```

For multi-lane work, add `lanes`. Each lane may override `objective`, `allowed_paths`, `forbidden_paths`, `criteria`, `boundaries`, `validation_commands`, and `worker_steps`. Keep shared repo context at the top level.

The composer writes `compose-metrics.json` with spec word count, generated handoff word count, expansion ratio, lane count, acceptance criterion count, boundary example count, complex logic signals, and generated file list. Use it to notice whether a compact spec is becoming too broad and should be split.

## Output Layout

For a single-lane task, create:

```text
<task-name>-handoff/
  README.md
  00-context.md
  01-task.md
  02-acceptance.md
  03-implementation-plan.md
  04-validation.md
  05-worker-prompt.md
  06-review-checklist.md
  07-handoff-quality-gates.md
  owner-audit-notes.md        # optional; do not pass to worker if it contains withheld checks
  manual-preflight.json       # generated checker report when available
```

For multi-lane work, create:

```text
<task-name>-handoff/
  README.md
  integration-handoff.md
  lanes/
    01-<lane-name>/
      00-context.md
      01-task.md
      02-acceptance.md
      03-implementation-plan.md
      04-validation.md
      05-worker-prompt.md
      06-review-checklist.md
      07-handoff-quality-gates.md
    02-<lane-name>/
      ...
```

Never create runner-only files such as `batch.json`, `run-agent-batch.sh`, `results/`, `worker-runs/`, hidden validation command configs, or external-agent logs.

## README.md

Include:

- Package purpose.
- Which file the user should give to the local worker first, usually `05-worker-prompt.md`.
- Recommended order for manual use.
- Repo path and task date if known.
- Lane order and checkpoint expectations for multi-lane packages.
- A clear note that Codex did not launch any runner or worker.

## 00-context.md

Include the context a weaker local model needs before editing:

- Repo root as an absolute path and a short project description.
- Relevant files, modules, tests, commands, and data flow.
- Current behavior inferred from code.
- Existing conventions to preserve: naming, error handling, state shape, framework style, formatting, dependency policy, testing style.
- Known constraints from the user.
- Assumptions. Separate confirmed facts from assumptions.

Avoid vague statements like "follow best practices" unless they are tied to concrete repo conventions.

## 01-task.md

Include:

- One concrete objective stated as an end state.
- In-scope paths and behaviors.
- Out-of-scope paths and behaviors.
- Allowed file changes and forbidden file changes.
- Dependency policy. For simple Python or JavaScript tasks, explicitly forbid dependency/package scaffolding unless needed.
- Stop conditions: ambiguity, secrets, unsafe commands, missing tools, broad unrelated refactors, or validation commands that cannot run.

For Python stdlib/package-less tasks, prefer instructions like:

```bash
PYTHONPATH=. python3 -S path/to/test_or_script.py
```

For JavaScript/TypeScript, state the repo's actual package manager and module style when known.

## 02-acceptance.md

Acceptance criteria must be numbered and testable.

Each criterion should include:

- Required behavior.
- Valid evidence.
- Invalid substitutes.
- Boundary examples when behavior includes defaults, invalid input, empty state, duplicate data, ordering, persistence, rendering, reports, or action branches.

### Public Evidence Matrix

Create a table mapping every product requirement to public evidence:

```text
| Requirement | Public validation or manual audit | Required output/effect |
| --- | --- | --- |
| ... | ... | ... |
```

Public evidence can be a test command, a smoke command, a diff inspection item, or an explicit manual audit item. Do not cite hidden or owner-only checks as public evidence.

### Boundary Examples

Boundary examples are executable product requirements. Include concrete input and expected output/effect for categories such as:

- Missing, null, blank, unknown, invalid, duplicate, and empty values.
- Numeric/non-string/boolean/scalar/list/dict type coercion when normalization is required.
- Unknown action, update, move, clear/reset, filter, delete/remove, and no-op branches for reducers, handlers, routes, services, and command functions.
- Malformed record fields for reports/summaries, including invalid status, invalid priority/type/severity, blank owner/assignee, missing/null id fallback, and non-dict row fallback when relevant.
- Downstream effects such as totals, summaries, ordering, rendered output, persisted state, or returned payloads.
- Zero values and fractional rounding for money, quantity, rate, discount, tax, and total calculations.

### Public Boundary Assertion Checklist

Map every boundary example to either a public validation command or a manual audit item. If a boundary changes a downstream summary, total, ordering, persistence, or rendered output, the checklist must name that downstream effect.

### Phase Decomposition Rationale

State whether the handoff is split into lanes or intentionally kept as one lane. For an unsplit handoff with multiple phases, explain why one lane is safer and how public validation covers normalization/defaulting, core behavior, and downstream aggregation/rendering/persistence/reporting.

## 03-implementation-plan.md

Write an ordered plan for the local worker. Be explicit enough that the worker does not have to infer phase order from acceptance criteria.

Recommended shape:

1. Read/confirm the files and existing behavior.
2. Implement normalization/defaulting or input validation.
3. Implement core state transition, algorithm, service behavior, or UI behavior.
4. Implement downstream aggregation, rendering, persistence, response payloads, or reporting.
5. Add or update focused tests only where in scope.
6. Run configured validation.
7. Prepare final response with evidence.

For multi-lane packages, each lane should state:

- Prerequisites from previous lanes.
- Exact files it may edit.
- What it must not solve yet.
- Checkpoint instruction before the next lane starts.

## 04-validation.md

Include:

- Public validation commands with working directory.
- Expected exit code.
- What the command proves.
- Manual checks that cannot be automated.
- Known environment prerequisites.
- What to do if validation cannot run.
- Hidden/Public Alignment, even when owner-only checks are absent.

If validation commands are unknown, write placeholders in a way the user can fill:

```text
FILL_BEFORE_HANDOFF: Replace this with the repo's public validation command before giving the prompt to a worker.
```

Do not invent commands that the repo cannot support.

Hidden/Public Alignment must state whether owner-only checks exist. If they do, explain how every product requirement in those checks is represented in public acceptance, public validation, boundary examples, or explicit manual audit items.

## 05-worker-prompt.md

This is the primary deliverable. It must be copy-ready and self-contained.

Self-contained does not mean every detail must be repeated with equal weight. Put the constraints a weaker local model must obey near the top, then keep deeper background in support documents:

- First screen: allowed paths, forbidden paths, core objective, boundary examples, validation commands, and stop conditions.
- Middle: implementation plan and acceptance criteria.
- Later: detailed context and conventions, or point to `00-context.md` when it would dilute attention.

Include:

- Role: the worker owns implementation for the described scope.
- Repo path and working directory.
- Objective.
- Context summary.
- Allowed paths.
- Forbidden paths.
- Detailed implementation plan.
- Acceptance criteria.
- Boundary examples.
- Validation commands.
- Stop conditions.
- Final response format.

Suggested final response format for the worker:

```text
Status: completed | blocked
Changed files:
- ...
Validation:
- <command>: <exit code> (<short output summary>)
Acceptance evidence:
- AC1: ...
- AC2: ...
Notes:
- ...
```

Tell the worker not to broaden scope, not to install dependencies unless explicitly allowed, and not to edit validation to hide failures.

## 06-review-checklist.md

Create a human or second-agent review checklist:

- Did changed files stay within scope?
- Does each acceptance criterion have direct evidence?
- Were boundary examples implemented literally?
- Did validation run from the stated working directory?
- Were tests changed appropriately, without masking production failures?
- Were forbidden files untouched?
- Were dependencies, lockfiles, package metadata, generated files, and formatting churn avoided unless explicitly allowed?
- Are unresolved blockers clearly reported?

Ask the worker to return a manual audit packet:

- Changed files list.
- Final diff or patch.
- Public validation output with exit codes.
- Acceptance evidence by criterion.
- Boundary evidence by example.
- Notes on blockers, assumptions, and commands that could not run.

## 07-handoff-quality-gates.md

Include the benchmark-derived gates that made the runner handoffs reliable:

- Public Evidence Matrix covers every product requirement.
- Boundary Examples are executable product requirements.
- Public Boundary Assertion Checklist maps every boundary to public validation or manual audit.
- Worker prompt front-loads allowed paths, forbidden paths, validation, boundaries, and stop conditions.
- Worker Step Plan is ordered by phase.
- Owner-only checks are mirrored into public acceptance or manual audit and are not worker acceptance criteria.
- Lane split/decomposition rationale is explicit when the task stays as one lane despite multiple phases.

Add the boundary prompts that apply:

- Type coercion/defaulting: numeric, non-string, boolean, scalar/list/dict categories.
- Dict/object fields: non-string key, non-string value, malformed field values.
- Action branches: update, move, clear/reset, filter, unknown, no-op, delete/remove.
- Reports/summaries: invalid status, invalid priority/type/severity, blank owner/assignee, missing/null id fallback, non-dict row fallback, downstream counts and visible ids.
- Empty-state downstream output: rendered output, summaries, totals, persisted state, displayed zero-item output.
- Money/quantity/rate: zero values and fractional rounding.
- Service/action responses: which branches include fresh report/summary/metric/count payloads.

## Owner-Only or Hidden Checks

If the user wants to keep checks private from the worker:

- Put them in `owner-audit-notes.md`.
- Mark the file clearly: "Owner-only; do not pass to the worker."
- Do not make hidden-check success an acceptance criterion for the worker.
- Mirror every real product requirement from hidden checks into public acceptance, public validation, boundary examples, or manual audit items.
- Do not include hidden output, exact private test names, private fixtures, or secret data in `05-worker-prompt.md`.

If the user wants the local model to receive everything, skip owner-only notes and include all relevant validation and examples in the worker prompt.

## Lane Splitting

Prefer multiple handoffs when one prompt would force the local model to reason across unrelated domains or too many behavior phases.

Split by domain when work spans unrelated roots, such as backend API, frontend state, persistence, and workflow engines.

Split by behavior phase when a single root combines:

- Normalization/defaulting.
- Core algorithm or state transition.
- Aggregation, rendering, persistence, reporting, or response payloads.

For action/controller work, a single file can still be too broad if it owns load/save, many mutation branches, filtering, and fresh report/summary output. Split storage/defaulting, mutation branch families, and report/filter aggregation when feasible.

For sequential lanes in one repo, tell the user to checkpoint accepted changes before handing off the next dependent lane. Do not run downstream lanes after an upstream lane is blocked.

If a compact spec has many criteria, many boundary examples, multiple unrelated allowed roots, or multiple behavior phases in one lane, split it before composition. Local-model reliability usually improves more from smaller sequential prompts than from one exhaustive prompt.

## Manual Preflight

Run the checker before giving the package to the user when files were written:

```bash
python3 /path/to/local-handoff/scripts/check_manual_handoff.py \
  --package-dir /path/to/outputs/task-handoff \
  --json-out /path/to/outputs/task-handoff/manual-preflight.json
```

Fix `error` results before delivery. Treat warnings and suggestions as handoff design feedback:

- `missing_public_evidence_matrix`, `missing_boundary_examples`, `missing_public_boundary_assertion_checklist`
- `missing_phase_decomposition_rationale`, `missing_hidden_public_alignment`
- `hidden_success_as_worker_acceptance`, `hidden_output_shape_overreach`, `runner_artifact_reference`
- `validation_command_static_check_failed`
- `worker_prompt_not_front_loaded`, missing allowed/forbidden/validation/stop/final-response sections
- `python_site_path_isolation_gap`, `js_module_type`
- `consider_worker_step_plan`, `consider_lane_split`, `consider_complex_logic_decomposition`, `requires_phase_split_or_rationale`
- `consider_public_type_boundary_examples`, `consider_public_dict_field_type_boundaries`
- `consider_public_zero_value_boundaries`, `consider_public_fractional_money_rounding`
- `consider_public_empty_state_downstream_boundary`
- `consider_public_action_branch_coverage`, `consider_public_action_report_response_boundary`
- `consider_public_report_record_field_normalization`

The checker is a local document-quality gate only. It must not launch workers, run validation commands, inspect worker logs, or audit completed implementation.

## Quality Checklist for Codex

Before reporting completion, verify:

- The package contains no runner execution instructions.
- A compact spec was used when the task is not trivial, or the reason for manual drafting is clear.
- `manual-preflight.json` exists when files were written, or the final response says why the checker could not run.
- The worker prompt is self-contained.
- The worker prompt front-loads critical constraints instead of burying them after long context.
- The task objective is concrete.
- Allowed and forbidden paths are explicit.
- Acceptance criteria are numbered and testable.
- Public evidence covers every product requirement.
- Boundary examples include expected results, not just input categories.
- Public boundary checklist maps every boundary to validation or manual audit.
- Benchmark-derived boundary prompts were considered and either included or intentionally ruled out.
- Phase Decomposition Rationale is present and matches the package shape.
- Hidden/Public Alignment is present and does not hide product requirements from public acceptance/manual audit.
- Validation commands include cwd and expected exit behavior.
- Stop conditions are clear.
- Multi-lane dependencies and checkpoint expectations are clear.
- Owner-only material, if any, is clearly separated from worker-visible material.
