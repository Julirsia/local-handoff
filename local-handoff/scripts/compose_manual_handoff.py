#!/usr/bin/env python3
"""Compose manual local-agent handoff documents from a compact JSON spec."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_SPEC_KEYS = {
    "acceptance",
    "allowed_paths",
    "allow_paths",
    "anti_patterns",
    "assumptions",
    "boundaries",
    "boundary_examples",
    "constraints",
    "context",
    "conventions",
    "criteria",
    "dependency_policy",
    "execution_plan",
    "files",
    "forbidden_paths",
    "forbid_paths",
    "hidden_public_alignment",
    "in_scope",
    "integration_checks",
    "integration_objective",
    "integration_validation",
    "lanes",
    "manual_checks",
    "name",
    "objective",
    "out_of_scope",
    "out_scope",
    "owner_audit_alignment",
    "owner_audit_notes",
    "phase_decomposition_rationale",
    "project",
    "project_context",
    "public_validation",
    "relevant_files",
    "repo",
    "repo_root",
    "scope",
    "stop_conditions",
    "task_name",
    "validation_commands",
    "worker_capability",
    "worker_steps",
    "working_directory",
}

ALLOWED_LANE_KEYS = ALLOWED_SPEC_KEYS | {"summary"}

COMMON_KEY_TYPOS = {
    "critera": "criteria",
    "criterias": "criteria",
    "boundries": "boundaries",
    "boundarys": "boundaries",
    "validation_command": "validation_commands",
    "relevant_file": "relevant_files",
    "anti_pattern": "anti_patterns",
    "worker_capabilities": "worker_capability",
}

WORKER_CAPABILITIES = {"small", "medium", "large"}

DEFAULT_ANTI_PATTERNS = [
    "Do not invent imports, classes, helper functions, CLI flags, or API names. Verify existing symbols from the provided excerpts or by reading files.",
    "Do not edit tests, fixtures, snapshots, or validation commands merely to hide production failures.",
    "Do not broaden scope, reformat unrelated files, rename public APIs, or change package metadata unless explicitly required.",
    "Do not skip validation or report success without the configured command output or an explicit blocked reason.",
    "Do not continue after a stop condition; report blocked with the exact missing fact, path, or command.",
]


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "manual-handoff"


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def text(value: Any, default: str = "Not specified.") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip() or default
    return str(value)


def bullet(items: Any, default: str = "- Not specified.") -> str:
    values = [text(item) for item in as_list(items) if text(item, "").strip()]
    if not values:
        return default
    return "\n".join(f"- {item}" for item in values)


def numbered(items: Any, default: str = "1. Not specified.") -> str:
    values = [text(item) for item in as_list(items) if text(item, "").strip()]
    if not values:
        return default
    return "\n".join(f"{idx}. {item}" for idx, item in enumerate(values, 1))


def fenced_command(command: Any) -> str:
    if isinstance(command, dict):
        cwd = text(command.get("cwd"), ".")
        cmd = text(command.get("command") or command.get("cmd"))
        proves = text(command.get("proves"), "See acceptance criteria.")
        expected = text(command.get("expected_exit"), "0")
        return (
            f"- Working directory: `{cwd}`\n"
            f"  Expected exit: `{expected}`\n"
            f"  Proves: {proves}\n"
            "  Command:\n\n"
            f"  ```bash\n  {cmd}\n  ```"
        )
    return f"```bash\n{text(command)}\n```"


def validation_block(commands: Any) -> str:
    values = as_list(commands)
    if not values:
        return (
            "FILL_BEFORE_HANDOFF: Replace this with the repo's public "
            "validation command before giving the prompt to a worker."
        )
    return "\n\n".join(fenced_command(command) for command in values)


def language_for_path(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "jsx",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".json": "json",
        ".md": "markdown",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".sh": "bash",
    }.get(suffix, "text")


def code_fence(body: Any, language: str = "text") -> str:
    cleaned = text(body, "").replace("```", "`` `")
    if not cleaned:
        return ""
    return f"```{language}\n{cleaned}\n```"


def render_relevant_files(files: Any) -> str:
    values = as_list(files)
    if not values:
        return "- Not specified."

    lines: list[str] = []
    for item in values:
        if isinstance(item, dict):
            path = text(item.get("path") or item.get("file"), "FILL_BEFORE_HANDOFF: path")
            why = text(item.get("why") or item.get("reason"), "Reason not specified.")
            symbols = bullet(item.get("symbols") or item.get("functions") or item.get("classes"), "- Symbols not specified.")
            edit_allowed = text(item.get("edit_allowed"), "Follow allowed paths.")
            excerpt = text(item.get("excerpt") or item.get("snippet"), "")
            language = text(item.get("language"), language_for_path(path))
            block = [
                f"### `{path}`",
                "",
                f"- Why it matters: {why}",
                f"- Edit permission: {edit_allowed}",
                "- Relevant symbols:",
                symbols,
            ]
            if excerpt:
                block.extend(["", code_fence(excerpt, language)])
            else:
                block.append("- Excerpt: Not embedded. Worker must read this file before editing.")
            lines.append("\n".join(block))
        else:
            lines.append(f"- {text(item)}")
    return "\n\n".join(lines)


def normalized_worker_capability(data: dict[str, Any]) -> str:
    value = text(data.get("worker_capability"), "medium").lower()
    return value if value in WORKER_CAPABILITIES else "medium"


def capability_guidance(capability: str) -> str:
    guidance = {
        "small": [
            "Assume the worker is a weaker local model. Keep to one lane, one phase, and one validation loop at a time.",
            "Prefer exact excerpts, exact file paths, and literal boundary examples over references to broader repo context.",
            "After one scoped repair attempt on the same failing validation, stop and report blocked unless the fix is obvious within allowed paths.",
        ],
        "medium": [
            "Assume the worker can follow a detailed plan but may miss constraints buried in the middle of a long prompt.",
            "Keep critical paths, boundaries, validation, anti-patterns, and stop conditions near the top of the worker prompt.",
            "After up to two scoped repair attempts on the same failing validation, stop and report blocked unless the user adds context.",
        ],
        "large": [
            "Assume the worker can use broader context, but still keep implementation bounded to the stated files and evidence.",
            "Do not remove front-loaded constraints; larger models still need exact acceptance and validation boundaries.",
            "Repair only within scope and report blocked when requirements conflict or validation depends on missing prerequisites.",
        ],
    }
    return bullet(guidance[capability])


def self_repair_loop(capability: str) -> str:
    if capability == "small":
        repair_phrase = "one scoped repair attempt"
    elif capability == "medium":
        repair_phrase = "up to two scoped repair attempts"
    else:
        repair_phrase = "bounded scoped repair attempts"
    return numbered(
        [
            "Make the smallest scoped change needed for the current acceptance criterion or boundary example.",
            "Run the single most relevant configured validation command and capture its exit code and short output summary.",
            f"If validation fails, inspect the failure and make {repair_phrase} only inside allowed paths.",
            "Rerun the same validation after each repair attempt.",
            "If the same failure persists, a prerequisite is missing, or a fix requires forbidden paths or broad refactoring, stop and report `blocked`.",
        ]
    )


def anti_pattern_block(items: Any) -> str:
    values = as_list(items)
    if not values:
        values = DEFAULT_ANTI_PATTERNS
    return bullet(values)


def criteria_rows(criteria: Any) -> tuple[str, str]:
    values = as_list(criteria)
    if not values:
        matrix = (
            "| Requirement | Public validation or manual audit | Required output/effect |\n"
            "| --- | --- | --- |\n"
            "| Not specified | Not specified | Not specified |"
        )
        return "1. Not specified.", matrix

    criteria_lines: list[str] = []
    rows = [
        "| Requirement | Public validation or manual audit | Required output/effect |",
        "| --- | --- | --- |",
    ]
    for idx, item in enumerate(values, 1):
        if isinstance(item, dict):
            req = text(item.get("requirement") or item.get("criterion") or item.get("text"))
            evidence = text(item.get("evidence") or item.get("public_evidence") or item.get("validation"))
            effect = text(item.get("effect") or item.get("expected") or item.get("result"))
        else:
            req = text(item)
            evidence = "Public validation or manual audit must cover this criterion."
            effect = req
        criteria_lines.append(
            f"{idx}. {req}\n"
            f"   - Valid evidence: {evidence}\n"
            f"   - Required output/effect: {effect}\n"
            "   - Invalid substitutes: summaries without executable or manual evidence."
        )
        rows.append(f"| {req.replace('|', '/')} | {evidence.replace('|', '/')} | {effect.replace('|', '/')} |")
    return "\n\n".join(criteria_lines), "\n".join(rows)


def boundary_sections(boundaries: Any) -> tuple[str, str]:
    values = as_list(boundaries)
    if not values:
        boundary = "- Not specified. Add concrete missing/default/unknown/empty/invalid cases before handoff if behavior has boundaries."
        checklist = "- Not specified. Map each boundary example to public validation or manual audit before handoff."
        return boundary, checklist

    boundary_lines: list[str] = []
    checklist_lines: list[str] = []
    for idx, item in enumerate(values, 1):
        if isinstance(item, dict):
            case = text(item.get("case") or item.get("input") or item.get("name"))
            expected = text(item.get("expected") or item.get("output") or item.get("effect"))
            evidence = text(
                item.get("evidence") or item.get("validation") or item.get("manual_audit"),
                "Manual audit if no public command covers it.",
            )
        else:
            case = text(item)
            expected = "Expected result must be made explicit before handoff."
            evidence = "Manual audit if no public command covers it."
        boundary_lines.append(f"- Case: {case}\n  Expected: {expected}")
        checklist_lines.append(f"- Boundary {idx}: {case} -> {evidence}; downstream effect: {expected}")
    return "\n".join(boundary_lines), "\n".join(checklist_lines)


def lint_spec_object(
    data: dict[str, Any],
    *,
    label: str,
    allowed_keys: set[str],
    check_required: bool = True,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    for key in sorted(data):
        if key not in allowed_keys:
            suggestion = f" Did you mean `{COMMON_KEY_TYPOS[key]}`?" if key in COMMON_KEY_TYPOS else ""
            errors.append(
                {
                    "severity": "error",
                    "code": "unknown_spec_key",
                    "path": f"{label}.{key}",
                    "message": f"Unknown spec key `{key}`.{suggestion}",
                }
            )

    capability = data.get("worker_capability")
    if capability is not None and text(capability).lower() not in WORKER_CAPABILITIES:
        errors.append(
            {
                "severity": "error",
                "code": "invalid_worker_capability",
                "path": f"{label}.worker_capability",
                "message": "worker_capability must be one of: small, medium, large.",
            }
        )

    if check_required:
        criteria = as_list(data.get("criteria") or data.get("acceptance"))
        boundaries = as_list(data.get("boundaries") or data.get("boundary_examples"))
        validation = as_list(data.get("validation_commands") or data.get("public_validation"))
        if not criteria:
            warnings.append(
                {
                    "severity": "warning",
                    "code": "missing_spec_criteria",
                    "path": label,
                    "message": "Spec has no acceptance criteria; generated handoff will need manual completion.",
                }
            )
        if not boundaries:
            warnings.append(
                {
                    "severity": "warning",
                    "code": "missing_spec_boundaries",
                    "path": label,
                    "message": "Spec has no boundary examples; weaker workers may infer edge behavior incorrectly.",
                }
            )
        if not validation and not as_list(data.get("manual_checks")):
            warnings.append(
                {
                    "severity": "warning",
                    "code": "missing_spec_validation",
                    "path": label,
                    "message": "Spec has neither validation_commands nor manual_checks.",
                }
            )

    relevant_files = as_list(data.get("relevant_files"))
    excerpt_count = 0
    for idx, item in enumerate(relevant_files, 1):
        if not isinstance(item, dict):
            continue
        item_path = f"{label}.relevant_files[{idx}]"
        if not text(item.get("path") or item.get("file"), ""):
            errors.append(
                {
                    "severity": "error",
                    "code": "missing_relevant_file_path",
                    "path": item_path,
                    "message": "Each relevant_files object must include path.",
                }
            )
        if not text(item.get("why") or item.get("reason"), ""):
            warnings.append(
                {
                    "severity": "warning",
                    "code": "missing_relevant_file_why",
                    "path": item_path,
                    "message": "Each relevant file should say why it matters to the worker.",
                }
            )
        excerpt = text(item.get("excerpt") or item.get("snippet"), "")
        if excerpt:
            excerpt_count += 1
            line_count = len(excerpt.splitlines())
            if line_count > 120:
                warnings.append(
                    {
                        "severity": "warning",
                        "code": "long_relevant_file_excerpt",
                        "path": item_path,
                        "message": f"Embedded excerpt has {line_count} lines; prefer the smallest complete function/type/test signature.",
                    }
                )
    capability_name = normalized_worker_capability(data)
    if capability_name == "small" and excerpt_count > 5:
        warnings.append(
            {
                "severity": "warning",
                "code": "too_many_excerpts_for_small_worker",
                "path": label,
                "message": "small worker capability should usually receive 5 or fewer embedded excerpts per lane.",
            }
        )
    elif excerpt_count > 8:
        warnings.append(
            {
                "severity": "warning",
                "code": "too_many_relevant_file_excerpts",
                "path": label,
                "message": "Many embedded excerpts can dilute attention; split lanes or trim excerpts.",
            }
        )

    anti_patterns = data.get("anti_patterns")
    if anti_patterns is not None and not isinstance(anti_patterns, (str, list)):
        errors.append(
            {
                "severity": "error",
                "code": "invalid_anti_patterns",
                "path": f"{label}.anti_patterns",
                "message": "anti_patterns must be a string or list of strings.",
            }
        )
    return errors, warnings


def lint_spec(spec: dict[str, Any]) -> dict[str, Any]:
    errors, warnings = lint_spec_object(spec, label="$", allowed_keys=ALLOWED_SPEC_KEYS)
    if not text(spec.get("objective"), "") and not as_list(spec.get("lanes")):
        errors.append(
            {
                "severity": "error",
                "code": "missing_spec_objective",
                "path": "$.objective",
                "message": "Spec must include objective unless every lane has its own objective.",
            }
        )
    lanes = as_list(spec.get("lanes"))
    if lanes and not isinstance(spec.get("lanes"), list):
        errors.append(
            {
                "severity": "error",
                "code": "invalid_lanes",
                "path": "$.lanes",
                "message": "lanes must be a list of objects.",
            }
        )
    for idx, lane in enumerate(lanes, 1):
        if not isinstance(lane, dict):
            errors.append(
                {
                    "severity": "error",
                    "code": "invalid_lane",
                    "path": f"$.lanes[{idx}]",
                    "message": "Each lane must be an object.",
                }
            )
            continue
        lane_label_text = f"$.lanes[{idx}]"
        lane_errors, lane_warnings = lint_spec_object(
            lane,
            label=lane_label_text,
            allowed_keys=ALLOWED_LANE_KEYS,
            check_required=False,
        )
        errors.extend(lane_errors)
        warnings.extend(lane_warnings)
        merged = dict(spec)
        merged.update(lane)
        _, merged_required_warnings = lint_spec_object(
            merged,
            label=lane_label_text,
            allowed_keys=ALLOWED_SPEC_KEYS | {"summary"},
            check_required=True,
        )
        warnings.extend(
            item
            for item in merged_required_warnings
            if item["code"] in {"missing_spec_criteria", "missing_spec_boundaries", "missing_spec_validation"}
        )
        if not text(lane.get("objective") or lane.get("summary"), ""):
            warnings.append(
                {
                    "severity": "warning",
                    "code": "missing_lane_objective",
                    "path": f"$.lanes[{idx}]",
                    "message": "Each lane should include objective or summary.",
                }
            )

    return {
        "status": "error" if errors else ("warning" if warnings else "ok"),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "issues": errors + warnings,
    }


def critical_first() -> str:
    return """# Critical Instructions First

- Work only within the allowed paths listed below.
- Do not edit forbidden paths or broaden scope.
- Implement every numbered acceptance criterion and every boundary example literally.
- Run only the configured validation commands as blocking evidence unless the user adds more.
- Stop and report `blocked` if requirements conflict, required files are missing, validation cannot run, or secrets/unsafe commands are needed.
"""


def render_docs(spec: dict[str, Any], lane: dict[str, Any] | None = None) -> dict[str, str]:
    data = dict(spec)
    if lane:
        data.update(lane)

    repo = text(data.get("repo") or data.get("repo_root") or data.get("working_directory"), "FILL_BEFORE_HANDOFF: repo path")
    objective = text(data.get("objective"))
    context = text(data.get("context") or data.get("project_context"))
    worker_capability = normalized_worker_capability(data)
    worker_guidance = capability_guidance(worker_capability)
    anti_patterns = anti_pattern_block(data.get("anti_patterns"))
    repair_loop = self_repair_loop(worker_capability)
    assumptions = bullet(data.get("assumptions"))
    conventions = bullet(data.get("conventions"))
    in_scope = bullet(data.get("in_scope") or data.get("scope"))
    out_scope = bullet(data.get("out_of_scope") or data.get("out_scope"))
    allowed = bullet(data.get("allowed_paths") or data.get("allow_paths"))
    forbidden = bullet(data.get("forbidden_paths") or data.get("forbid_paths"))
    stop_conditions = bullet(
        data.get("stop_conditions"),
        "- Ambiguous or conflicting requirements.\n"
        "- Missing required files or tools.\n"
        "- Validation commands cannot run.\n"
        "- Required change would touch forbidden paths.\n"
        "- Secrets or unsafe commands are required.",
    )
    implementation_steps = numbered(data.get("worker_steps") or data.get("implementation_plan") or data.get("execution_plan"))
    validation = validation_block(data.get("validation_commands") or data.get("public_validation"))
    manual_checks = bullet(data.get("manual_checks"))
    hidden_public_alignment = text(
        data.get("hidden_public_alignment") or data.get("owner_audit_alignment"),
        "No owner-only checks are configured. If owner-only checks are added later, mirror every product requirement into public acceptance or manual audit.",
    )
    phase_decomposition_rationale = text(
        data.get("phase_decomposition_rationale"),
        "No special single-lane decomposition rationale. Split this work if it spans unrelated roots or multiple behavior phases.",
    )
    criteria_text, evidence_matrix = criteria_rows(data.get("criteria") or data.get("acceptance"))
    boundaries, boundary_checklist = boundary_sections(data.get("boundaries") or data.get("boundary_examples"))
    relevant_files = render_relevant_files(data.get("relevant_files") or data.get("files"))
    dependency_policy = text(
        data.get("dependency_policy"),
        "Do not add dependencies, lockfiles, package metadata, or scaffolding unless the user explicitly permits it.",
    )

    return {
        "00-context.md": f"""# Context

## Repo

Absolute path: `{repo}`

## Project Summary

{context}

## Relevant Files, Modules, Tests, and Data Flow

{relevant_files}

## Existing Conventions To Preserve

{conventions}

## Confirmed Constraints

{bullet(data.get("constraints"))}

## Assumptions

{assumptions}
""",
        "01-task.md": f"""# Task

## Objective

{objective}

## In Scope

{in_scope}

## Out of Scope

{out_scope}

## Allowed Paths

{allowed}

## Forbidden Paths

{forbidden}

## Dependency Policy

{dependency_policy}

## Stop Conditions

{stop_conditions}
""",
        "02-acceptance.md": f"""# Acceptance

## Numbered Criteria

{criteria_text}

## Public Evidence Matrix

{evidence_matrix}

## Boundary Examples

{boundaries}

## Public Boundary Assertion Checklist

{boundary_checklist}

## Phase Decomposition Rationale

{phase_decomposition_rationale}
""",
        "03-implementation-plan.md": f"""# Implementation Plan

Follow this order. Do not infer a broader plan from nearby code.

{implementation_steps}

## Worker Capability

Configured worker capability: `{worker_capability}`.

{worker_guidance}

## Weak-Worker Failure Modes To Prevent

- Import/API hallucination: worker invents helpers or symbols instead of reading target files.
- Scope creep: worker edits neighboring files, package metadata, tests, or generated artifacts outside the allowed paths.
- Constraint burial: worker misses forbidden paths, boundary cases, or validation because they appear late in a long prompt.
- Validation omission: worker reports success without running commands or naming why validation is blocked.
- Step-order drift: worker implements downstream reporting before required normalization/defaulting or core state behavior.

## Anti-Patterns

{anti_patterns}

## Self-Repair Loop

{repair_loop}

## Local Model Guidance

- Keep edits narrow and directly tied to acceptance criteria.
- Implement normalization/defaulting before downstream calculations or rendering.
- Implement core state transitions or algorithms before reports, responses, persistence, or UI output.
- Add or update focused tests only when they are in scope.
- Prepare final evidence after validation runs.
""",
        "04-validation.md": f"""# Validation

## Public Commands

Run from the stated working directory.

{validation}

## Manual Checks

{manual_checks}

## Hidden/Public Alignment

{hidden_public_alignment}

## If Validation Cannot Run

Stop and report `blocked`. Include the command, working directory, error output summary, and what prerequisite is missing.
""",
        "05-worker-prompt.md": f"""{critical_first()}
# Worker Prompt

You are the implementation worker for this manually delegated task. Modify files only within the allowed scope. Do not ask Codex for more context.

## Working Directory

`{repo}`

## Objective

{objective}

## Context Summary

{context}

## Relevant Code Excerpts

{relevant_files}

## Worker Capability

Configured worker capability: `{worker_capability}`.

{worker_guidance}

## Allowed Paths

{allowed}

## Forbidden Paths

{forbidden}

## Implementation Plan

{implementation_steps}

## Acceptance Criteria

{criteria_text}

## Boundary Examples

{boundaries}

## Validation Commands

{validation}

## Anti-Patterns

{anti_patterns}

## Self-Repair Loop

{repair_loop}

## Stop Conditions

{stop_conditions}

## Final Response Format

```text
Status: completed | blocked
Changed files:
- ...
Validation:
- <command>: <exit code> (<short output summary>)
Acceptance evidence:
- AC1: ...
- AC2: ...
Boundary evidence:
- ...
Notes:
- ...
```
""",
        "06-review-checklist.md": """# Review Checklist

Use this checklist for a human or second-agent read-only audit.

- Changed files stayed within allowed paths.
- Forbidden paths were not edited.
- Every acceptance criterion has direct evidence.
- Every boundary example was implemented literally or is explicitly blocked.
- Public validation ran from the stated working directory.
- Tests were not edited to hide production failures.
- Dependencies, lockfiles, package metadata, generated files, and formatting churn were avoided unless explicitly allowed.
- Final worker response reports unresolved blockers, assumptions, and validation output.

## Audit Packet To Request From Worker

- Final response in the required format.
- Changed file list.
- Final diff or patch.
- Validation command output with exit codes.
- Acceptance evidence by criterion.
- Boundary evidence by case.
""",
        "07-handoff-quality-gates.md": f"""# Handoff Quality Gates

These gates preserve the benchmark-derived handoff checks without launching a runner.

## Required Gates

- Public Evidence Matrix covers every product requirement.
- Boundary Examples include concrete expected results, not categories only.
- Public Boundary Assertion Checklist maps every boundary to public validation or manual audit.
- Worker prompt is self-contained and front-loads allowed paths, forbidden paths, validation, boundaries, and stop conditions.
- Worker Step Plan is ordered by phase: normalization/defaulting, core behavior, downstream aggregation/rendering/persistence/reporting, validation.
- Hidden or owner-only checks, if any, are not worker acceptance criteria and are mirrored into public acceptance or manual audit.
- Hidden/Public Alignment states whether owner-only checks exist and how their product requirements are represented publicly.
- Phase Decomposition Rationale explains why work is split into lanes or why a single lane is acceptable.

## Benchmark-Derived Boundary Prompts

- Type boundaries: numeric, non-string, boolean, scalar/list/dict categories when normalization/defaulting is in scope.
- Dict/object boundaries: non-string keys, non-string values, malformed fields when object normalization is in scope.
- Action branches: update, move, clear/reset, filter, unknown, no-op, delete/remove when those branches are named.
- Report/summary boundaries: invalid status, invalid priority/type/severity, blank owner/assignee, missing/null id fallback, malformed/non-dict row fallback, and downstream count/visible-id effects.
- Empty-state downstream effects: rendered output, summaries, totals, persisted state, displayed zero-item output.
- Money/quantity boundaries: zero values and fractional rounding for amount, quantity, total, discount, tax, percent, rate, basis points, and line items.
- Response payload boundaries: state which handler/service/action responses include fresh report, summary, metrics, or count payloads.

## Decomposition Gates

- Split by domain when allowed paths span unrelated roots.
- Split by phase when one lane combines normalization/defaulting, core algorithm/state transition, and aggregation/rendering/persistence/reporting.
- For action/controller work, split storage/defaulting, mutation branch families, and report/filter aggregation when feasible.
- For final wrapper/report lanes, state which upstream lanes are already accepted and how validation covers fresh downstream output.

## Weak-Worker Guardrails

- Embed the smallest complete code excerpts for target functions, type definitions, and relevant tests when the worker may not explore the repo well.
- State worker capability as small, medium, or large and split lanes more aggressively for small workers.
- Keep anti-patterns explicit: no guessed APIs, no scope broadening, no test-masking edits, no skipped validation.
- Require the worker to use the self-repair loop before reporting completed or blocked.
""",
    }


def lane_label(lane: dict[str, Any], idx: int) -> str:
    return f"{idx:02d}-{slugify(text(lane.get('name') or lane.get('task_name') or f'lane-{idx}'))}"


def render_readme(spec: dict[str, Any], lanes: list[dict[str, Any]]) -> str:
    task_name = text(spec.get("task_name") or spec.get("name") or spec.get("project"), "Manual handoff")
    repo = text(spec.get("repo") or spec.get("repo_root") or spec.get("working_directory"), "FILL_BEFORE_HANDOFF: repo path")
    lane_lines = ""
    if lanes:
        lane_lines = "\n## Lane Order\n\n" + bullet(
            [f"{lane_label(lane, idx)}: {text(lane.get('objective') or lane.get('summary'))}" for idx, lane in enumerate(lanes, 1)]
        )
        lane_lines += "\n\nCheckpoint accepted changes before handing off each dependent next lane.\n"
    return f"""# {task_name} Manual Handoff

This package is for manual delegation to a local or external coding agent. Codex prepared documents only. No runner, worker process, silent wait, or final runner audit was launched.

## Repo

`{repo}`

## Start Here

Give the worker `05-worker-prompt.md` first for a single-lane handoff. For multi-lane work, give the worker each lane's `05-worker-prompt.md` in lane order.

## Recommended Manual Flow

1. Read this README.
2. Give the relevant `05-worker-prompt.md` to the worker.
3. After the worker finishes, collect changed files, diff, validation output, and final response.
4. Use `06-review-checklist.md` for read-only review.
{lane_lines}
"""


def render_integration(spec: dict[str, Any], lanes: list[dict[str, Any]]) -> str:
    return f"""# Integration Handoff

Use this after upstream lanes are accepted and checkpointed.

## Objective

{text(spec.get("integration_objective") or spec.get("objective"))}

## Lane Dependencies

{bullet([f"{lane_label(lane, idx)}: {text(lane.get('objective') or lane.get('summary'))}" for idx, lane in enumerate(lanes, 1)])}

## Integration Checks

{bullet(spec.get("integration_checks") or spec.get("manual_checks"))}

## Validation

{validation_block(spec.get("integration_validation") or spec.get("validation_commands") or spec.get("public_validation"))}
"""


def write_file(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.rstrip() + "\n", encoding="utf-8")


def count_words(path: Path) -> int:
    return len(re.findall(r"\S+", path.read_text(encoding="utf-8")))


def compose(spec: dict[str, Any], out_dir: Path, force: bool, spec_lint: dict[str, Any] | None = None) -> None:
    if out_dir.exists() and not force:
        raise SystemExit(f"Output directory already exists: {out_dir}. Use --force to overwrite generated files.")
    out_dir.mkdir(parents=True, exist_ok=True)

    lanes = [lane for lane in as_list(spec.get("lanes")) if isinstance(lane, dict)]
    write_file(out_dir / "README.md", render_readme(spec, lanes))

    written: list[Path] = [out_dir / "README.md"]
    if lanes:
        write_file(out_dir / "integration-handoff.md", render_integration(spec, lanes))
        written.append(out_dir / "integration-handoff.md")
        for idx, lane in enumerate(lanes, 1):
            lane_dir = out_dir / "lanes" / lane_label(lane, idx)
            for name, body in render_docs(spec, lane).items():
                write_file(lane_dir / name, body)
                written.append(lane_dir / name)
    else:
        for name, body in render_docs(spec).items():
            write_file(out_dir / name, body)
            written.append(out_dir / name)

    owner_notes = text(spec.get("owner_audit_notes"), "")
    if owner_notes:
        write_file(out_dir / "owner-audit-notes.md", "# Owner-Only Audit Notes\n\nOwner-only; do not pass to the worker.\n\n" + owner_notes)
        written.append(out_dir / "owner-audit-notes.md")

    spec_words = len(re.findall(r"\S+", json.dumps(spec, ensure_ascii=False)))
    handoff_words = sum(count_words(path) for path in written)
    all_criteria = as_list(spec.get("criteria") or spec.get("acceptance"))
    all_boundaries = as_list(spec.get("boundaries") or spec.get("boundary_examples"))
    for lane in lanes:
        all_criteria.extend(as_list(lane.get("criteria") or lane.get("acceptance")))
        all_boundaries.extend(as_list(lane.get("boundaries") or lane.get("boundary_examples")))
    complex_terms = [
        "normalize", "default", "algorithm", "calculate", "round", "persist", "storage",
        "render", "report", "summary", "response", "mutation", "handler", "service",
        "route", "controller", "filter", "aggregate",
    ]
    spec_text = json.dumps(spec, ensure_ascii=False).lower()
    metrics = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "out_dir": str(out_dir),
        "multi_lane": bool(lanes),
        "lane_count": len(lanes) if lanes else 1,
        "spec_words": spec_words,
        "handoff_words": handoff_words,
        "expansion_ratio": round(handoff_words / spec_words, 3) if spec_words else None,
        "acceptance_criterion_count": len(all_criteria),
        "boundary_example_count": len(all_boundaries),
        "complex_logic_signals": [term for term in complex_terms if term in spec_text],
        "spec_lint": spec_lint or lint_spec(spec),
        "files": [str(path.relative_to(out_dir)) for path in written],
    }
    write_file(out_dir / "compose-metrics.json", json.dumps(metrics, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path, help="Compact JSON handoff spec.")
    parser.add_argument("--out-dir", required=True, type=Path, help="Output handoff package directory.")
    parser.add_argument("--force", action="store_true", help="Overwrite generated files in the output directory.")
    args = parser.parse_args(argv)

    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to read spec: {exc}", file=sys.stderr)
        return 2
    if not isinstance(spec, dict):
        print("Spec root must be a JSON object.", file=sys.stderr)
        return 2

    spec_lint = lint_spec(spec)
    if spec_lint["issues"]:
        print(json.dumps(spec_lint, indent=2, ensure_ascii=False), file=sys.stderr)
    if spec_lint["status"] == "error":
        return 2

    compose(spec, args.out_dir, args.force, spec_lint)
    print(f"Wrote manual handoff package: {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
