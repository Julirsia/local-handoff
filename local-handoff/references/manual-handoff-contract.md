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
  "canonical_task_file": "specs/001-feature/tasks.md",
  "task_ids": ["T001", "T002"],
  "objective": "one concrete end state",
  "context": "repo and behavior context",
  "allowed_paths": ["src/example.py"],
  "forbidden_paths": ["pyproject.toml", "*.egg-info/**"],
  "worker_capability": "small",
  "scope_breadth": "full game with N modes/entities, not a minimal stub",
  "architecture_freedom": "pin behavior + look-and-feel; HOW (file layout, UI technique) is the worker's choice; HTML/CSS for HUD allowed",
  "visual_acceptance": [
    "characters/sprites render at >= 6% of viewport height (legible, not specks)",
    "terrain/background is not a flat single fill: >= 2-color gradient + texture/outline",
    "projectile trail visible >= 0.4s; explosion flash >= 0.3s",
    "stated theme + palette clearly recognizable on a desktop viewport"
  ],
  "reference_assets": ["mockup.png", "comparable product screenshot, or described density"],
  "relevant_files": [
    {
      "path": "src/example.py",
      "why": "contains the target function and existing return shape",
      "symbols": ["repair_target"],
      "edit_allowed": "yes",
      "excerpt": "def repair_target(...):\n    ..."
    }
  ],
  "anti_patterns": [
    "Do not invent imports or helper APIs; verify existing symbols first.",
    "Do not edit tests to hide production failures.",
    "Do not skip validation or report success without command output."
  ],
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

For multi-lane work, add `lanes`. Each lane may override `objective`, `allowed_paths`, `forbidden_paths`, `criteria`, `boundaries`, `validation_commands`, `worker_steps`, `task_ids`, and `depends_on`. Keep shared repo context at the top level.

The composer writes `compose-metrics.json` with spec word count, generated handoff word count, expansion ratio, lane count, acceptance criterion count, boundary example count, complex logic signals, and generated file list. Use it to notice whether a compact spec is becoming too broad and should be split.

The composer lints the compact spec before writing files. Unknown keys are errors because typos such as `critera` silently drop acceptance criteria. Warnings identify missing boundaries, missing validation, oversized excerpts, or too many excerpts for a small worker.

### Relevant Code Excerpts

Use `relevant_files` objects when the worker is a local model that may not explore the repo reliably. Embed only the smallest complete snippets the worker needs:

- Target function or class body.
- Related type/interface/dataclass definition.
- Public test signature or assertion block.
- Existing helper API that must be reused.

Do not paste whole files by default. For `worker_capability: "small"`, keep most lanes to five or fewer excerpts and usually 20-80 lines per excerpt. If more code is needed, split the lane.

### Worker Capability

Set `worker_capability` to one of:

- `small`: 7B-30B local model or weak repo exploration. Split lanes aggressively, front-load constraints, embed exact excerpts, and allow only one repair pass before blocked.
- `medium`: default local coding model. Keep constraints early and provide bounded repair attempts.
- `large`: stronger model. You can rely more on repo exploration, but still keep exact scope, validation, and boundaries.

### Anti-Patterns

Use `anti_patterns` to make behavior-level prohibitions explicit. Prefer concrete negatives over generic warnings:

- Bad: "Be careful."
- Good: "Do not invent imports/classes/helpers; read the target file and reuse existing symbols."
- Bad: "Validate input."
- Good: "For blank owner, output owner='unassigned' and include it in report counts."
- Bad: "Run tests."
- Good: "Run `PYTHONPATH=. python3 -S tests/test_todos.py`; if it cannot run, report blocked with the missing prerequisite."

## Constraint Axis: Tight on WHAT, Loose on HOW

A handoff fails the user even when every test passes if rigor is aimed at the wrong axis. Benchmark case: a tightly-specified artillery game handoff passed all 72 logic tests but shipped a visually poor, feature-minimal result, while the same task built by free-form direct instruction was both richer and better-looking. The diagnosis was not "too strict" — it was strict on the wrong things.

Pin **WHAT** tightly; leave **HOW** free:

- Tight (WHAT): observable behavior, acceptance criteria, boundary results, scope breadth, look-and-feel targets, and validation. These are the product.
- Loose (HOW): file layout, helper structure, internal APIs, and especially UI technique. Do not over-specify exact function signatures or mandate an architecture unless a real integration contract requires it. Over-pinning HOW makes a weak worker produce a literal, minimal, brittle result.

Use the `architecture_freedom` field (rendered into `01-task.md` and `05-worker-prompt.md`) to say this explicitly.

### Testability Must Not Degrade UX Architecture

Keeping logic pure and testable is good — but do not let a testability rule push the *interface* onto a harder, worse-looking path. The benchmark handoff mandated "DOM-free logic, draw the HUD on canvas," which forced the worker to hand-draw HP bars and menus and produced tiny, unreadable UI; the free-form build used HTML/CSS for the HUD and looked far better for less effort.

Rule: isolate correctness-critical logic (ballistics, damage, state transitions) in pure, testable modules — and let the UI be built however looks best, including HTML/CSS for HUD, menus, and overlays. The checker flags `testability_ux_architecture_tradeoff` when a UI-scoped handoff forbids HTML/DOM.

### Scope & Breadth

Weak local models ship the smallest passing version of an under-scoped ask. State the intended breadth explicitly with `scope_breadth`: number of modes/entities/screens/mechanics, content items, and what "complete" means. If the objective implies a rich experience, say so; do not let "minimal clone" be the silent default.

### Visual & UX Quality Is a Quantified, Manual-Audit Product Requirement

Visuals cannot be unit-tested, but "verified by manual audit" is NOT a license for vague adjectives like "themed" or "ink-wash." Encode visual quality as a separate, quantified acceptance checklist (`visual_acceptance`), kept distinct from functional criteria so it is not buried. Use measurable, checkable targets, for example:

- Minimum on-screen element sizes (px or % of viewport) so sprites/text are not specks.
- Grid-to-sprite scale ratios so elements do not shrink to nothing on small viewports.
- Background/surface richness: no flat single fill — require gradient, texture, or detail.
- Animation/feedback durations (e.g., trajectory trail >= 0.4s, explosion flash >= 0.3s).
- Explicit palette usage and a recognizable theme.
- A **reference asset** (`reference_assets`): mockup, comparable-product screenshot, or described density, so the worker has a concrete quality bar.

Remember the executor ceiling: a weak (7B-30B) local model has a low creative/visual ceiling you cannot fully specify away. For visual-heavy deliverables, supply a reference, allow HTML/CSS, and assume a human or stronger-model polish pass — or recommend the user run the visual layer that way.

The checker emits `missing_quantified_visual_acceptance` (warning), `consider_visual_quality_section`, `consider_reference_asset`, and `consider_what_how_balance` when UI/visual scope is detected. Treat the warning as a must-fix for any UI deliverable.

## Output Layout

For a single-lane task, create:

```text
<task-name>-handoff/
  README.md
  manual-handoff-spec.json
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
  manual-handoff-spec.json
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
- Embedded code excerpts for target functions, types, tests, and existing helper APIs when local exploration is weak.
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

Include weak-worker failure modes and the design rules that prevent them:

- Import/API hallucination -> embed exact excerpts and tell the worker to verify existing symbols.
- Scope creep -> repeat allowed and forbidden paths near the top of the prompt.
- Constraint burial -> front-load acceptance boundaries, validation, and stop conditions.
- Validation omission -> require command output or blocked status.
- Step-order drift -> order the plan by normalization/defaulting, core behavior, downstream output, validation.

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
- Relevant code excerpts when provided in the spec.
- Worker capability guidance.
- Allowed paths.
- Forbidden paths.
- Detailed implementation plan.
- Acceptance criteria.
- Boundary examples.
- Validation commands.
- Anti-patterns.
- Self-repair loop: change, validate, repair within scope, rerun, then completed or blocked.
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
Also tell the worker not to invent imports, helpers, or API names. If a needed symbol is not present in the excerpt or target file, it must read the file or report blocked instead of guessing.

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
- Relevant code excerpts exist for weak exploration surfaces, or the handoff says why path-only context is sufficient.
- Anti-patterns and a bounded self-repair loop are present in the worker prompt.
- Worker capability is stated and reflected in lane size, excerpt count, and repair budget.

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

## Canonical Task Ownership

When a design workflow already produced `specs/**/tasks.md` (for example after `speckit-tasks`), that file is the canonical implementation scope. Do not create a parallel task plan that can drift from it.

- Set `canonical_task_file` to the repo-relative or absolute tracker path.
- Assign each unchecked required task ID to exactly one lane with `task_ids`.
- Express lane prerequisites with `depends_on`; order lanes topologically and stop if an upstream lane is blocked.
- The composer rejects unknown IDs, duplicate ownership, lanes without IDs, and any unchecked canonical task left unassigned.
- Each worker prompt must request evidence by assigned task ID. A checked box is reporting state, not proof.
- Workers may update the tracker only when it is explicitly in Allowed Paths and the task's mapped validation passed. Otherwise the human/final reviewer reconciles checkboxes after reviewing evidence.
- The integration handoff must contain a Canonical Task Coverage matrix and treat any unchecked required task as blocking completion.

Always keep the generated `manual-handoff-spec.json` in the package. It is the machine-readable source for lane ownership, dependencies, and executable integration gates. The composer removes `owner_audit_notes` from this worker-visible copy; keep private checks only in `owner-audit-notes.md`.

## Cross-Lane Seam Contracts and Executable Integration Gates

Splitting a producer and its consumer into separate lanes (for example a server API lane and a web client lane) creates a *seam*: a shared interface that neither lane verifies on its own. Benchmark failure: every lane passed in isolation (server unit tests green, client build green) while the running app was broken, because the seam silently diverged — the client called `PATCH /api/items/:id` while the server only implemented `PUT`, so every edit returned 404; and two endpoints anchored "today" differently, so the dashboard's renewal list was always empty while the notifications endpoint was correct. Per-lane green plus a manual-only audit did not catch either, and the manual audit was skipped.

Two requirements close this gap:

1. **Pin the seam once; reference it from both sides.** Put the shared interface in a single contract that the producer lane and the consumer lane both quote verbatim, so neither invents its own variant:
   - HTTP: every route as METHOD + path (e.g. `PUT /api/items/:id`). The consumer excerpt must call the exact same verb and path the producer registers; do not leave the client's verbs as a vague "CRUD" comment.
   - Modules: function name + argument meaning + return shape.
   - Shared semantics: the meaning of any ambiguous value crossing the seam (what `now`/`today` refers to, timezone, currency units, rounding). A single parameter must not silently serve two roles (e.g. "which month to aggregate" and "now for the renewal window").
   Use the spec field `seam_contract` (rendered into the integration handoff). For the function-signature exception to "loose on HOW": a real cross-lane interface contract IS a case where pinning signatures/verbs is correct.

2. **Verify the seam with one EXECUTABLE end-to-end gate, never manual-only.** The integration handoff must include an executable command that drives the consumer against the real producer (for example: boot the server, then exercise it using the client's own API module / a script that uses the client's real HTTP verbs and paths) and asserts the result, including at least one cross-component consistency invariant. Use the spec fields `integration_e2e` (executable command list) and `seam_invariants`. A manual audit may supplement the gate but must not replace it, because per-component unit tests + a build pass independently and a manual gate gets skipped.

Consistency invariants are how you catch *silent* divergence: an empty-but-valid-looking response (`[]`) is a failure only if an invariant says it must be non-empty here, or that two endpoints/functions must return the same underlying value. State at least one.

The checker flags `integration_seam_gate_missing` (warning) when allowed paths span multiple component roots and the integration handoff has no executable end-to-end gate, `consider_integration_gate` (suggestion) for phase-split multi-lane work, and `consider_seam_consistency_invariant` when a cross-component seam states no invariant.

### The gate must be runnable: write the command AND the script

The gate is not documentation — the downstream runner executes it. Provide `integration_e2e` as command objects (cwd/command/expected_exit/proves), and if the seam needs more than one shell line, also deliver the script itself as a file the lanes create or that you include, so the command actually runs. Prefer the consumer's own client over hand-rolled calls, so the gate exercises the real verbs/paths.

Spec fields (server + client example):

```json
"seam_contract": "HTTP routes are the contract: PUT /api/subscriptions/:id and PUT /api/expenses/:id (the client MUST use these exact verbs/paths). The dashboard's renewal window and the notifications endpoint both anchor on the server's current date (today), not the requested month.",
"seam_invariants": [
  "Editing a subscription via the client's update call returns 2xx (not 404) -- proves client verb/path match the server route.",
  "GET /api/dashboard upcomingRenewals == GET /api/notifications renewals for the same user/today."
],
"integration_e2e": [
  {
    "cwd": "/abs/path/to/repo",
    "command": "node e2e/seam.mjs",
    "expected_exit": 0,
    "proves": "Boots the server, signs up, exercises the client's real update verb, and asserts dashboard renewals == notifications renewals."
  }
]
```

Sketch of `e2e/seam.mjs` (the script the command runs; assert invariants, exit non-zero on mismatch):

```js
// 1. boot the producer (server) on a test port, fresh DB
// 2. drive it through the CONSUMER's real interface (import the client's api module, or
//    replicate its exact METHOD+path) -- e.g. signup, create a subscription renewing in 2 days
// 3. assert the seam invariants:
//    - client.subscriptionUpdate(id, {...})  -> response.ok (catches PATCH-vs-PUT 404)
//    - dashboard.upcomingRenewals deep-equals notifications renewals (catches a divergent `today`)
// 4. process.exit(failures ? 1 : 0)
```

### How the runner consumes the gate

A handoff runner reads `integration_e2e` from the spec (place the spec where it is discoverable, e.g. `manual-handoff-spec.json` inside the package or a sibling `<name>-spec.json`) or parses the rendered "Executable Integration Gate" section of `integration-handoff.md`. It then runs the command after all lanes pass:

- gate present and passes -> the seam is verified;
- gate present and fails -> the whole run fails (the seam is genuinely broken);
- gate missing -> the run finishes but is marked seam-UNVERIFIED, not a clean pass (strict mode can hard-fail instead).

So a handoff with no `integration_e2e` is accepted but can never reach a verified-seam result. For any producer/consumer handoff, ship a real gate.

## Manual Preflight

Run the checker before giving the package to the user when files were written:

```bash
python3 /path/to/local-handoff/scripts/check_manual_handoff.py \
  --package-dir /path/to/outputs/task-handoff \
  --json-out /path/to/outputs/task-handoff/manual-preflight.json
```

Fix `error` results before delivery. Treat warnings and suggestions as handoff design feedback:

- `canonical_task_file_missing`, `canonical_task_file_empty`, `lane_missing_task_ids`
- `duplicate_task_assignment`, `unknown_task_assignment`, `unassigned_required_tasks`
- `root_lint_validation_missing`, `missing_machine_readable_spec`, `missing_false_green_runtime_guard`
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
- A repo root `lint` script is included in public validation when present.
- Fatal runtime output such as `EADDRINUSE`, unhandled rejection, fatal error, or timeout fails validation even if exit code is 0; E2E uses an isolated fresh process/state.
- Stop conditions are clear.
- Multi-lane dependencies and checkpoint expectations are clear.
- If a canonical task tracker exists, every unchecked required task is assigned exactly once, task evidence is reported by ID, and the integration handoff blocks on unchecked required tasks.
- Owner-only material, if any, is clearly separated from worker-visible material.
- Constraints are tight on WHAT (behavior, look-and-feel, acceptance) and loose on HOW (architecture, file layout, UI technique); no needless function-signature or architecture mandates.
- No testability rule forces the UI onto a worse path; HTML/CSS for HUD/menus/overlays is allowed while correctness-critical logic stays pure/testable.
- Scope & Breadth states the full intended experience so a weak worker does not ship a minimal stub.
- For any UI scope: a separate Visual & UX Quality checklist with quantified, manual-audit targets and a reference asset is present (not just adjectives).
- For producer/consumer multi-lane work: the shared seam (HTTP method+path, function signature, shared semantics) is pinned once and quoted by both lanes, and the integration handoff has an executable end-to-end gate plus at least one consistency invariant — not a manual-only audit.
