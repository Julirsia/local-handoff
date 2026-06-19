---
name: local-handoff
description: Create detailed handoff-only documents and copy-ready prompts for a human to manually give to a local or external coding agent. Use when the current agent must stop after preparing request/specification documents and must not launch a runner, worker process, silent batch, implementation loop, or final artifact audit. Trigger on manual handoff, handoff docs only, local model prompt, no runner, or user will run the worker manually.
---

# Local Handoff

## Core Boundary

Use this skill to author handoff documents only.

The current agent may:

1. Inspect the repo or provided artifacts enough to write an accurate handoff.
2. Create a self-contained document package for a human to pass to a local/external worker.
3. Include a copy-ready worker prompt and a review checklist.

The current agent must not:

- Launch `agent_batch_runner.py`, Pi CLI, a local LLM CLI, or any external worker.
- Wait silently for implementation, read worker logs, or audit final runner artifacts.
- Implement the requested code change unless the user separately asks Codex to do so.
- Shorten the handoff just to reduce tokens. Prefer completeness, explicit examples, and unambiguous instructions.
- Use this skill when the user wants a runner-backed workflow that launches a worker, waits for execution, or audits runner results.

## Required Reference

Before drafting a handoff package, read `references/manual-handoff-contract.md`. It defines the output files, document sections, benchmark-derived evidence rules, boundary examples, lane splitting guidance, quality gates, and manual preflight checklist.

## Workflow

1. Gather task context.
   - Identify repo path, target files/modules, requested behavior, validation commands, constraints, and any user-provided local-model assumptions.
   - Prefer reading existing code, tests, docs, and config over inventing details.
   - If `specs/**/tasks.md` or another canonical task tracker exists (especially after `speckit-tasks`), use it as the source of implementation scope. Record its path and task IDs; do not silently replace it with a new plan.
   - Ask a concise question only when a missing detail would make the handoff unsafe or materially ambiguous.

2. Decide package shape.
   - For a narrow task, create one handoff package.
   - For broad work spanning unrelated roots or multiple behavior phases, split into lane documents plus a final integration/review handoff.
   - For same-file complex logic, split by phase when useful: normalization/defaulting, core algorithm/state transition, then aggregation/rendering/persistence.
   - When a canonical tracker exists, assign every unchecked required task ID to exactly one lane, preserve dependency order, and add a final integration/review handoff. Duplicate, unknown, or unassigned task IDs are composition errors.

3. Create a compact spec first.
   - Prefer writing one JSON spec with `task_name`, `repo`, `objective`, `context`, `allowed_paths`, `forbidden_paths`, `criteria`, `boundaries`, `validation_commands`, `worker_steps`, `worker_capability`, `relevant_files`, `anti_patterns`, optional `canonical_task_file` + `task_ids`, and optional `lanes`.
   - Constrain the right axis: pin **WHAT** (behavior, acceptance, scope breadth, look-and-feel) tightly; leave **HOW** (file layout, helpers, UI technique) free. Avoid needless function-signature or architecture mandates — over-pinning HOW makes a weak worker ship a literal, minimal, brittle result. Use `architecture_freedom` to say this, and never let a testability rule force the UI onto a worse path (allow HTML/CSS for HUD/menus; keep only correctness-critical logic pure/testable).
   - Set `scope_breadth` so the worker builds the full requested experience, not the smallest passing stub.
   - For any UI/visual deliverable, set `visual_acceptance` with quantified, manual-audit targets (minimum element sizes, scale ratios, background richness, animation durations, palette/theme) and `reference_assets` (mockup/screenshot/described density). "Manual audit" is not a license for vague adjectives. See the "Constraint Axis" and "Visual & UX Quality" sections in the contract.
   - Use `lanes` when the local model should execute smaller sequential chunks. Each lane can override objective, paths, criteria, boundaries, validation, worker steps, `task_ids`, and `depends_on`.
   - Use `worker_capability` (`small`, `medium`, `large`) to tune lane size, excerpt count, and repair budget. Default to `medium`; use `small` for 7B-30B local models or weak repo exploration.
   - Add `relevant_files` entries with path, `lines` (line range anchor), why, symbols, edit permission, and short excerpts for target functions, types, tests, or helper APIs when path-only context may make the worker guess. Embedded excerpts are point-in-time snapshots; the composer flags them so the worker reads the live file and treats it as the source of truth.
   - Add `anti_patterns` for action-level failure modes: guessed APIs, scope creep, test masking, skipped validation, and continuing past stop conditions.
   - Put completeness into the spec fields rather than manually drafting all documents from scratch.

4. Compose the package from the spec.
   - Use the bundled composer when possible:

```bash
python3 /path/to/local-handoff/scripts/compose_manual_handoff.py \
  --spec /path/to/manual-handoff-spec.json \
  --out-dir /path/to/outputs/task-handoff \
  --force
```

   - The composer writes the document package plus `compose-metrics.json` with spec size, generated handoff size, expansion ratio, lane count, and generated file list.
   - The composer also copies the spec to `manual-handoff-spec.json`; keep it in the package so downstream runners can discover canonical task ownership and `integration_e2e` without parsing prose.
   - The composer lints the spec before writing. Fix unknown-key errors, especially misspelled fields that would silently drop acceptance criteria or boundaries.
   - If the task needs nuanced prose beyond the generated skeleton, edit the generated files after composition rather than starting from empty documents.

5. Write or refine the handoff package.
   - Default to a user-facing directory under the current workspace, such as `outputs/<task-name>-handoff/`, unless the user requests another path.
   - Include `README.md`, `00-context.md`, `01-task.md`, `02-acceptance.md`, `03-implementation-plan.md`, `04-validation.md`, `05-worker-prompt.md`, `06-review-checklist.md`, and `07-handoff-quality-gates.md`.
   - For multi-lane work, create `lanes/<lane-id>/` with the same core files for each lane and add a top-level integration handoff.
   - Do not create `batch.json`, `run-agent-batch.sh`, runner result folders, hidden runner configs, or worker log directories.

6. Make the worker prompt self-contained and digestible.
   - `05-worker-prompt.md` must be usable even if the local model never opens the other files.
   - Include objective, repo assumptions, allowed paths, forbidden paths, implementation steps, acceptance criteria, boundary examples, validation commands, stop conditions, and required final response format.
   - Include relevant code excerpts, worker capability guidance, explicit anti-patterns, and a bounded self-repair loop when generated by the composer.
   - Put critical constraints near the top: allowed paths, forbidden paths, boundary examples, validation commands, and stop conditions.
   - Keep deeper context in `00-context.md` and related support files when the prompt would become too long for a weaker local model to attend to reliably.
   - Use absolute paths when available, plus repo-relative paths for readability.

7. Preserve validation integrity.
   - Public validation must directly map to acceptance criteria.
   - If the repo root defines a `lint` script, include its real package-manager command in lane or integration validation. The composer rejects a package that omits it.
   - Exit code 0 is not sufficient when output contains a fatal runtime signal such as `EADDRINUSE`, an unhandled rejection, a fatal error, or a timeout. Require an isolated port/process and a rerun against fresh state so a stale service cannot create false-green E2E evidence.
   - Boundary examples are product requirements, not optional hints.
   - If owner-only or hidden checks exist, do not make hidden success a worker acceptance criterion. Put owner-only checks in a clearly labeled file such as `owner-audit-notes.md`, and mirror every product requirement in public acceptance or manual audit items.
   - For producer/consumer multi-lane work (e.g. server + client), pin the shared seam once via `seam_contract` (HTTP method+path, function signatures, shared semantics like the meaning of `now`/`today`) and quote it from both lanes, then give the integration handoff an EXECUTABLE end-to-end gate (`integration_e2e`) plus a consistency invariant (`seam_invariants`) — never a manual-only audit. See "Cross-Lane Seam Contracts and Executable Integration Gates" in the contract. The checker flags `integration_seam_gate_missing` otherwise.
   - The gate is RUN, not read: the handoff runner executes `integration_e2e` after the lanes. Make it actually runnable — deliver the e2e script (a lane creates it, or include it) and prefer driving the consumer's real client so the gate exercises the true verbs/paths. Downstream: gate present+passes = seam verified; present+fails = the run fails; missing = the run finishes but is marked seam-UNVERIFIED (not a clean pass). Place the spec where the runner can find it (`manual-handoff-spec.json` in the package or a sibling `<name>-spec.json`) so `integration_e2e` is picked up, or rely on the rendered "Executable Integration Gate" section.

8. Run manual preflight and self-review before final response.
   - Run the bundled checker when files were written:

```bash
python3 /path/to/local-handoff/scripts/check_manual_handoff.py \
  --package-dir /path/to/outputs/task-handoff \
  --json-out /path/to/outputs/task-handoff/manual-preflight.json
```

   - Fix `error` results before delivering the handoff.
   - Treat `warning` and `suggestion` results as benchmark-derived design feedback, especially boundary coverage and lane split suggestions.
   - Check the package against the quality checklist in `references/manual-handoff-contract.md`.
   - Confirm the Canonical Task Coverage matrix assigns every unchecked required task exactly once and that worker prompts ask for evidence by task ID. A checkbox is reporting state, not proof; do not declare implementation complete from checked boxes alone.
   - Make sure every acceptance criterion has evidence, every important boundary has expected behavior, and validation commands are realistic for the repo.
   - If validation commands cannot be known, write explicit placeholders and tell the user exactly what must be filled before handing the prompt to a worker.

## Final Response

Report the created package path, the manual preflight status, the most important files, and state that no runner or external worker was launched. Keep the summary short; the handoff documents carry the detail.
