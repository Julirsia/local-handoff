#!/usr/bin/env python3
"""Check manual handoff documents for benchmark-derived quality gates."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any


CORE_FILES = [
    "00-context.md",
    "01-task.md",
    "02-acceptance.md",
    "03-implementation-plan.md",
    "04-validation.md",
    "05-worker-prompt.md",
    "06-review-checklist.md",
    "07-handoff-quality-gates.md",
]

VAGUE_ACCEPTANCE_TERMS = {
    "deterministic": "give an exact tie-break example",
    "validate": "list invalid inputs and expected errors/status",
    "validation": "list invalid inputs and expected errors/status",
    "sort": "state ascending/descending and tie-breaks",
    "sorted": "state ascending/descending and tie-breaks",
    "merge": "state overlap/touching/equality behavior",
    "failure": "state failure API/result behavior",
    "retry": "state attempt-count semantics",
    "cache": "state cache hit/miss behavior",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_-]+", text.lower()))


def issue(severity: str, code: str, message: str, path: str | None = None) -> dict[str, str]:
    item = {"severity": severity, "code": code, "message": message}
    if path:
        item["path"] = path
    return item


def has_any(text: str, terms: list[str]) -> bool:
    low = text.lower()
    return any(term in low for term in terms)


def markdown_section_text(markdown: str, heading: str) -> str:
    match = re.search(
        rf"(?ims)^#+\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^#+\s+|\Z)",
        markdown,
    )
    return match.group(1).strip() if match else ""


def validation_commands(validation: str) -> list[str]:
    commands: list[str] = []
    for block in re.findall(r"```(?:bash|sh)?\n(.*?)\n```", validation, flags=re.DOTALL | re.IGNORECASE):
        for line in block.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                commands.append(line)
    return commands


def command_looks_python(command: str) -> bool:
    return bool(re.search(r"(^|[;&|()\s])(python3?|pytest)\b", command))


def python_script_import_path_gap(command: str) -> bool:
    if "PYTHONPATH=." in command or "PYTHONPATH=$PWD" in command or "PYTHONPATH=$(pwd)" in command:
        return False
    if re.search(r"(^|[;&|()\s])python3?\s+-m\b", command):
        return False
    return bool(re.search(r"(^|[;&|()\s])python3?\s+(?!-c\b)(?!-m\b)\S+\.py\b", command))


def missing_public_dict_field_type_boundary(text: str) -> bool:
    lowered = text.lower()
    field_map_signal = re.search(
        r"\b(fields?|field map|field mapping)\b.{0,80}\b(dict(?:ionary)?|object|map)\b"
        r"|\b(dict(?:ionary)?|object|map)\b.{0,80}\b(fields?|field map|field mapping)\b",
        lowered,
    )
    field_key_contract_signal = re.search(
        r"\bfield\s+keys?\b|\bkeys?\b.{0,40}\bfields?\b|\bfields?\b.{0,40}\bkeys?\b",
        lowered,
    )
    field_value_contract_signal = re.search(
        r"\bfield\s+values?\b|\bvalues?\b.{0,40}\bfields?\b|\bfields?\b.{0,40}\bvalues?\b",
        lowered,
    )
    if not (field_map_signal and field_key_contract_signal and field_value_contract_signal):
        return False
    key_type_signal = re.search(
        r"\b(non[- ]?string|numeric|number|integer|float|boolean|bool)\s+(?:field\s+)?keys?\b|\b(?:field\s+)?keys?\s+(?:are\s+)?(?:coerc\w*|converted|type[- ]?checked)",
        lowered,
    )
    value_type_signal = re.search(
        r"\b(non[- ]?string|numeric|number|integer|float|boolean|bool)\s+(?:field\s+)?values?\b|\b(?:field\s+)?values?\s+(?:are\s+)?(?:coerc\w*|converted|stored as strings?|type[- ]?checked)",
        lowered,
    )
    return key_type_signal is None or value_type_signal is None


def section_has_value(markdown: str, heading: str) -> bool:
    section = markdown_section_text(markdown, heading).lower()
    return bool(section and "not specified" not in section and "fill_before_handoff" not in section)


def prompt_code_excerpt_section(prompt: str) -> str:
    match = re.search(
        r"(?is)^##\s+Relevant Code Excerpts\s*$([\s\S]*?)(?=^##\s+Worker Capability\s*$|^##\s+Allowed Paths\s*$|\Z)",
        prompt,
        flags=re.MULTILINE,
    )
    return match.group(1).strip() if match else ""


def check_package_dir(pkg: Path, label: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for name in CORE_FILES:
        body = read(pkg / name)
        if not body.strip():
            issues.append(issue("error", "missing_handoff_file", f"Required handoff file is empty or missing: {name}.", str(pkg / name)))
        if re.search(r"\b(?:TODO|TBD)\b|Replace this|FILL_BEFORE_HANDOFF", body):
            issues.append(issue("error", "placeholder_left", "Handoff still contains placeholder text.", str(pkg / name)))

    acceptance = read(pkg / "02-acceptance.md")
    context = read(pkg / "00-context.md")
    task = read(pkg / "01-task.md")
    plan = read(pkg / "03-implementation-plan.md")
    validation = read(pkg / "04-validation.md")
    prompt = read(pkg / "05-worker-prompt.md")
    review = read(pkg / "06-review-checklist.md")
    quality = read(pkg / "07-handoff-quality-gates.md")
    combined = "\n".join([acceptance, plan, validation, prompt, review])
    combined_low = combined.lower()
    domain_text = "\n".join([context, task, acceptance, validation])
    domain_low = domain_text.lower()

    if "public evidence matrix" not in acceptance.lower():
        issues.append(issue("error", "missing_public_evidence_matrix", "Acceptance must include Public Evidence Matrix.", label))
    public_evidence_matrix = markdown_section_text(acceptance, "Public Evidence Matrix")
    if re.search(r"\b(hidden|withheld)\b", public_evidence_matrix.lower()):
        issues.append(issue("error", "hidden_evidence_in_public_matrix", "Public Evidence Matrix must cite public validation or manual audit only, not hidden/withheld checks.", label))
    if "boundary examples" not in acceptance.lower():
        issues.append(issue("error", "missing_boundary_examples", "Acceptance must include Boundary Examples.", label))
    if "public boundary assertion checklist" not in acceptance.lower():
        issues.append(issue("error", "missing_public_boundary_assertion_checklist", "Acceptance must map every boundary to public validation or manual audit.", label))
    if "phase decomposition rationale" not in acceptance.lower():
        issues.append(issue("warning", "missing_phase_decomposition_rationale", "Acceptance should include Phase Decomposition Rationale for split/unsplit work.", label))
    if "hidden/public alignment" not in validation.lower():
        issues.append(issue("warning", "missing_hidden_public_alignment", "Validation should include Hidden/Public Alignment, even when owner-only checks are absent.", label))
    if "not specified" in acceptance.lower():
        issues.append(issue("warning", "unspecified_acceptance_content", "Acceptance still contains 'Not specified' placeholder text.", label))
    if not section_has_value(task, "Allowed Paths"):
        issues.append(issue("warning", "missing_allow_paths", "Allowed paths are missing or unspecified; scope control is weaker.", label))
    if not section_has_value(task, "Forbidden Paths"):
        issues.append(issue("warning", "missing_forbid_paths", "Forbidden paths are missing or unspecified.", label))
    if "fill_before_handoff" in combined_low:
        issues.append(issue("error", "unfilled_validation_placeholder", "Validation placeholder remains; fill public command or explicit manual audit before handoff.", label))
    commands = validation_commands(validation)
    if not commands and not has_any(validation, ["manual audit", "manual check", "manual verification"]):
        issues.append(issue("error", "missing_public_validation", "Add a public validation command or explicit manual audit item.", label))
    if "hidden" in combined_low and has_any(combined, ["hidden validation passes", "hidden command passes", "withheld test passes"]):
        issues.append(issue("error", "hidden_success_as_worker_acceptance", "Do not ask worker to prove hidden/withheld validation success.", label))
    for line in re.findall(r"(?m)^\s*(?:\d+\.|-)\s+(.+)$", acceptance):
        lowered_line = line.lower()
        if re.search(r"\b(hidden|withheld)\b", lowered_line) and re.search(r"\b(pass|passes|validation|audit|test|command|verify|verified)\b", lowered_line):
            issues.append(issue("error", "hidden_runner_evidence_in_acceptance", "Do not make hidden/audit command success a worker acceptance criterion.", label))
            break
    owner_shape_terms = ["data-", "zero-count", "exact html", "exact key", "exact attribute", "ordering"]
    owner_notes_text = read(pkg.parent.parent / "owner-audit-notes.md") + "\n" + read(pkg.parent / "owner-audit-notes.md")
    if owner_notes_text and any(term in owner_notes_text.lower() for term in owner_shape_terms):
        public_text = acceptance.lower() + "\n" + validation.lower()
        if not any(term in public_text for term in owner_shape_terms):
            issues.append(issue("suggestion", "hidden_output_shape_overreach", "Owner-only checks appear to assert output-shape details not named in public acceptance.", label))
    if has_any(combined, ["agent_batch_runner.py", "run-agent-batch.sh", "batch.json", "results/worker-runs"]):
        issues.append(issue("error", "runner_artifact_reference", "Manual handoff must not include runner execution artifacts.", label))
    if re.search(r"\bhandoff/[0-9a-z_-]+\.md\b", prompt.lower()) and not all(term in prompt.lower() for term in ["objective", "acceptance criteria", "validation commands"]):
        issues.append(issue("error", "package_relative_handoff_refs", "Worker prompt refers to repo-relative handoff files without being self-contained.", label))
    if "benchmark-derived boundary prompts" not in quality.lower():
        issues.append(issue("warning", "missing_benchmark_quality_gates", "07-handoff-quality-gates.md should include benchmark-derived boundary prompts.", label))
    if "weak-worker guardrails" not in quality.lower() and "weak-worker failure modes" not in quality.lower():
        issues.append(issue("warning", "missing_weak_worker_failure_modes", "Quality gates should name weak-worker failure modes and guardrails.", label))

    prompt_head = "\n".join(prompt.splitlines()[:20]).lower()
    if "critical instructions first" not in prompt_head:
        issues.append(issue("warning", "worker_prompt_not_front_loaded", "Worker prompt should front-load critical constraints for weaker local models.", label))
    for term, code in [
        ("allowed paths", "worker_prompt_missing_allowed_paths"),
        ("forbidden paths", "worker_prompt_missing_forbidden_paths"),
        ("validation", "worker_prompt_missing_validation"),
        ("stop conditions", "worker_prompt_missing_stop_conditions"),
        ("final response format", "worker_prompt_missing_final_format"),
    ]:
        if term not in prompt.lower():
            issues.append(issue("error", code, f"Worker prompt missing {term}.", label))
    for term, code, message in [
        ("relevant code excerpts", "worker_prompt_missing_code_excerpts", "Worker prompt should include embedded code excerpts or an explicit excerpt/read-before-edit section."),
        ("anti-patterns", "worker_prompt_missing_anti_patterns", "Worker prompt should include action-level anti-patterns for weaker local models."),
        ("self-repair loop", "worker_prompt_missing_self_repair_loop", "Worker prompt should include a bounded change/validate/repair/blocked loop."),
        ("worker capability", "worker_prompt_missing_worker_capability", "Worker prompt should state target worker capability: small, medium, or large."),
    ]:
        if term not in prompt.lower():
            issues.append(issue("warning", code, message, label))
    if "relevant code excerpts" in prompt.lower() and "```" not in prompt_code_excerpt_section(prompt) and section_has_value(task, "Allowed Paths"):
        issues.append(issue("suggestion", "missing_embedded_code_excerpt_blocks", "Relevant Code Excerpts section has no fenced excerpts; embed target functions/types/tests when local exploration is weak.", label))
    if "do not invent" not in prompt.lower() and "verify existing" not in prompt.lower():
        issues.append(issue("warning", "missing_no_api_guessing_antipattern", "Anti-patterns should explicitly forbid guessed imports/APIs/symbols.", label))
    if "tests" in combined_low and "hide production failures" not in prompt.lower() and "mask" not in prompt.lower():
        issues.append(issue("warning", "missing_no_test_masking_antipattern", "Anti-patterns should forbid changing tests merely to hide production failures.", label))
    if "blocked" not in markdown_section_text(prompt, "Self-Repair Loop").lower():
        issues.append(issue("warning", "self_repair_loop_missing_blocked_exit", "Self-Repair Loop should tell the worker when to stop and report blocked.", label))

    if "worker step" not in plan.lower() and "implementation plan" not in plan.lower():
        issues.append(issue("suggestion", "consider_worker_step_plan", "Add an explicit ordered worker step plan.", label))

    command_text = validation.lower()
    for line in commands:
        try:
            shlex.split(line)
        except ValueError as exc:
            issues.append(issue("error", "validation_command_static_check_failed", f"Validation command has shell parse error: {exc}", label))
    if any(python_script_import_path_gap(command) for command in commands):
        issues.append(issue("warning", "python_import_path_gap", "Python script validation may omit repo root from sys.path; prefer PYTHONPATH=. python3 ... or python3 -m ...", label))
    if "pythonpath" in command_text and "python3 -s" not in command_text and "python -s" not in command_text:
        issues.append(issue("warning", "python_site_path_isolation_gap", "For stdlib/package-less Python validation, prefer PYTHONPATH=. python3 -S ...", label))
    forbidden_section = markdown_section_text(task, "Forbidden Paths")
    if any(command_looks_python(command) for command in commands):
        missing_forbids = [
            pattern
            for pattern in ["pyproject.toml", "*.egg-info/**"]
            if pattern not in forbidden_section
        ]
        if missing_forbids:
            issues.append(issue("warning", "python_packaging_scope_gap", "Python validation is configured but package metadata is not explicitly forbidden: " + ", ".join(missing_forbids), label))
    if ".js" in command_text and "node" in command_text and ".mjs" not in command_text and ".cjs" not in command_text and "type" not in combined_low:
        issues.append(issue("suggestion", "js_module_type", "For Node .js ES module validation, state package module type or prefer .mjs/.cjs checks.", label))
    for term, fix in VAGUE_ACCEPTANCE_TERMS.items():
        if re.search(rf"\b{re.escape(term)}\w*\b", domain_low):
            if not re.search(r"\b(example|e\.g\.|such as|expected|assert|raises|throws|400|error)\b", domain_low):
                issues.append(issue("warning", "vague_acceptance_without_example", f"Term '{term}' appears without a concrete example; {fix}.", label))
                break
    hidden_alignment = markdown_section_text(validation, "Hidden/Public Alignment").lower()
    no_owner_only_signal = "no owner-only checks" in hidden_alignment or "owner-only checks are absent" in hidden_alignment
    owner_or_hidden_signal = bool(owner_notes_text.strip()) or (
        not no_owner_only_signal and has_any(validation, ["owner-only", "hidden", "withheld"])
    )
    if owner_or_hidden_signal and not has_any(validation, ["public validation", "public evidence", "manual audit", "boundary examples"]):
        issues.append(issue("warning", "hidden_without_comparable_public", "Owner-only/hidden checks exist but public validation may not exercise comparable behavior.", label))
    if owner_or_hidden_signal:
        alignment_ok = (
            "generalization" in hidden_alignment
            and has_any(hidden_alignment, ["public", "manual audit", "acceptance"])
            and has_any(hidden_alignment, ["not worker", "not a worker", "not acceptance", "not asked"])
        )
        if not alignment_ok:
            issues.append(issue("suggestion", "hidden_contract_check", "Hidden/Public Alignment should say owner-only checks are generalization-only and represented by public acceptance/manual audit.", label))

    termset = words(domain_text)
    allowed_roots = re.findall(r"^- ([A-Za-z0-9_./-]+)", read(pkg / "01-task.md"), flags=re.MULTILINE)
    distinct_roots = {p.split("/")[0] for p in allowed_roots if "/" in p}
    criterion_count = len(re.findall(r"(?m)^\d+\.", acceptance))
    boundary_count = len(re.findall(r"(?im)^- case:", acceptance))

    complex_terms = {
        "normalize", "normalization", "default", "algorithm", "calculate", "rounding",
        "persist", "storage", "render", "report", "summary", "response", "mutation",
        "handler", "service", "route", "controller", "filter", "aggregate",
    }
    if criterion_count >= 5 and boundary_count >= 5 and len(termset & complex_terms) >= 3:
        issues.append(issue("suggestion", "consider_complex_logic_decomposition", "Many criteria/boundaries with multiple behavior phases; consider lane or phase split.", label))
    if criterion_count >= 8 and "phase decomposition rationale" not in acceptance.lower():
        issues.append(issue("error", "requires_phase_split_or_rationale", "Large single handoff needs lane/phase split or explicit Phase Decomposition Rationale.", label))
    if len(distinct_roots) >= 3:
        issues.append(issue("warning", "consider_lane_split", "Allowed paths span several roots; consider domain/lane split.", label))
    if criterion_count >= 5 and len(distinct_roots) >= 2:
        issues.append(issue("error", "requires_lane_split", "Large handoff spanning multiple roots should be split into lane handoffs plus integration review.", label))
    if criterion_count >= 8 and len(termset & complex_terms) >= 5 and "phase decomposition rationale" not in acceptance.lower():
        issues.append(issue("error", "requires_phase_split", "Complex single-lane handoff needs phase split or explicit Phase Decomposition Rationale.", label))

    if has_any(domain_text, ["normalize", "default", "coerce", "fallback"]):
        for term in ["numeric", "non-string", "boolean", "scalar", "list", "dict"]:
            if term not in domain_low:
                issues.append(issue("suggestion", "consider_public_type_boundary_examples", f"Normalization/defaulting may need public {term} boundary evidence.", label))
                break
    if missing_public_dict_field_type_boundary(domain_text):
        issues.append(issue("suggestion", "consider_public_dict_field_type_boundaries", "Dict/object normalization should name malformed key/value field boundaries when relevant.", label))
    has_zero_boundary = "zero" in domain_low or re.search(r"\b0\b", domain_text) is not None
    if has_any(domain_text, ["amount", "quantity", "total", "balance", "line item"]) and not has_zero_boundary:
        issues.append(issue("suggestion", "consider_public_zero_value_boundaries", "Amount/quantity/total behavior should include zero-value boundaries when relevant.", label))
    if has_any(domain_text, ["discount", "tax", "percent", "rate", "cent", "money"]) and not has_any(domain_text, ["fractional", "round"]):
        issues.append(issue("suggestion", "consider_public_fractional_money_rounding", "Money/rate behavior should include fractional rounding boundaries when relevant.", label))
    if has_any(domain_text, ["clear", "reset", "delete", "remove"]) and has_any(domain_text, ["render", "summary", "persist", "display", "report"]) and not has_any(acceptance, ["empty", "zero", "visible"]):
        issues.append(issue("suggestion", "consider_public_empty_state_downstream_boundary", "Clear/reset/remove behavior should assert downstream empty-state output.", label))
    if has_any(domain_text, ["action", "reducer", "handler", "service", "command", "route", "endpoint", "mutation"]):
        branches = ["update", "move", "clear", "reset", "filter", "unknown"]
        mentioned = [branch for branch in branches if branch in domain_low]
        evidenced = [branch for branch in branches if branch in acceptance.lower()]
        if len(mentioned) >= 3 and len(evidenced) < len(mentioned):
            issues.append(issue("suggestion", "consider_public_action_branch_coverage", "Public evidence/checklist should assert every named action branch result.", label))
    if has_any(domain_text, ["report", "summary", "aggregate", "count", "visible id"]) and has_any(domain_text, ["status", "priority", "severity", "owner", "assignee", "id"]):
        needed = ["invalid status", "invalid priority", "blank owner", "missing", "non-dict"]
        if not any(term in domain_low for term in needed):
            issues.append(issue("suggestion", "consider_public_report_record_field_normalization", "Report/summary normalization should assert malformed fields and row shape in downstream output.", label))
    if has_any(domain_text, ["response", "payload"]) and has_any(domain_text, ["report", "summary", "metrics", "count"]) and has_any(domain_text, ["action", "handler", "route", "service"]):
        if not has_any(acceptance, ["fresh report", "fresh summary", "response includes", "payload includes"]):
            issues.append(issue("suggestion", "consider_public_action_report_response_boundary", "Action/service response should state which branches return fresh report/summary payloads.", label))

    # ── Visual / UX scope gates ─────────────────────────────────────
    # A handoff with rendered-UI scope must constrain WHAT (look-and-feel) tightly
    # while leaving HOW (architecture, UI technique) free, and must give the worker a
    # quantified visual bar instead of adjectives. Conservative detection: one strong
    # signal, or two weaker UI signals.
    strong_visual = ["canvas", "sprite", "spritesheet", "animation", "animate", "viewport", "svg", "shader", "pixel art"]
    weak_visual = ["html", "css", "render", " ui ", "ux", "frontend", "front-end", "screen", "layout",
                   "theme", "draw", "visual", "palette", "color", "colour", "dom", "button", "menu", "hud", "game"]
    # Detect from author-provided signal only (project summary, paths, criteria), NOT from
    # composer boilerplate, so non-visual handoffs are not mis-flagged by injected sections.
    detect_text = " " + " ".join([
        markdown_section_text(context, "Project Summary"),
        markdown_section_text(task, "Allowed Paths"),
        markdown_section_text(task, "Forbidden Paths"),
        markdown_section_text(acceptance, "Numbered Criteria"),
    ]).lower() + " "
    strong_hits = [t for t in strong_visual if t in detect_text]
    weak_hits = [t for t in weak_visual if t in detect_text]
    visual_scope = bool(strong_hits) or len(weak_hits) >= 2
    if visual_scope:
        visual_section = markdown_section_text(acceptance, "Visual & UX Quality")
        if not visual_section:
            issues.append(issue("suggestion", "consider_visual_quality_section",
                "UI/visual scope detected; add a separate Visual & UX Quality acceptance checklist so visuals are not buried under functional criteria.", label))
        # Quantified targets are checked inside the visual section only, so a stray "%"
        # or number elsewhere in context does not mask a vague visual spec.
        quantified_markers = ["minimum", "at least", "no smaller", "ratio", "% of", "duration", "fps", "frames"]
        has_quantified = bool(re.search(r"\d+\s?(px|pt|rem|em|%|ms|s|fps|vh|vw)\b", visual_section.lower())) or has_any(visual_section, quantified_markers)
        if not has_quantified:
            issues.append(issue("warning", "missing_quantified_visual_acceptance",
                "UI/visual scope detected but the Visual & UX Quality acceptance has no quantified targets (sizes in px/%, scale ratios, animation durations). Add measurable, manual-audit visual criteria; adjectives like 'themed' are not enough.", label))
        reference_terms = ["mockup", "screenshot", ".png", ".jpg", ".jpeg", ".svg", "reference image",
                           "comparable product", "described density", "reference design", "wireframe", "figma"]
        if not has_any(combined, reference_terms):
            issues.append(issue("suggestion", "consider_reference_asset",
                "UI/visual scope detected; supply a reference (mockup/screenshot/described density) so the worker has a concrete quality bar.", label))
        if "implementation freedom" not in (task + prompt).lower() and "what vs how" not in (task + prompt).lower():
            issues.append(issue("suggestion", "consider_what_how_balance",
                "State an Implementation Freedom (WHAT vs HOW) note: pin behavior/look-and-feel, leave architecture and UI technique free.", label))
        # Testability rule must not force UI onto a harder, worse-looking path.
        ui_words = has_any(combined, ["hud", "interface", " ui ", "menu", "overlay", "control panel"])
        forces_hard_ui = has_any(combined, ["dom-free", "no dom", "canvas-only", "must not use html",
                                            "do not use html", "without html", "draw the hud", "draw hp", "render the hud on"])
        if ui_words and forces_hard_ui:
            issues.append(issue("warning", "testability_ux_architecture_tradeoff",
                "A constraint forbids HTML/DOM for UI (likely for testability) while UI/HUD is in scope. Keep purity for correctness-critical logic only; allow HTML/CSS for HUD/menus/overlays so testability does not force a worse-looking UI.", label))

    return issues


def package_dirs(root: Path) -> list[tuple[str, Path]]:
    lanes = root / "lanes"
    if lanes.exists():
        return [(path.name, path) for path in sorted(lanes.iterdir()) if path.is_dir()]
    return [(root.name, root)]


def check(root: Path) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    if not root.exists():
        issues.append(issue("error", "missing_package_dir", "Package directory does not exist.", str(root)))
        return {"status": "error", "issues": issues}

    for forbidden in ["batch.json", "run-agent-batch.sh", "results", "worker-runs"]:
        if (root / forbidden).exists():
            issues.append(issue("error", "runner_artifact_present", f"Manual package contains runner artifact {forbidden}.", str(root / forbidden)))

    if not (root / "README.md").exists():
        issues.append(issue("warning", "missing_readme", "Manual package should include README.md.", str(root / "README.md")))
    if (root / "compose-metrics.json").exists():
        try:
            metrics = json.loads(read(root / "compose-metrics.json"))
            if metrics.get("lane_count", 1) == 1 and metrics.get("handoff_words", 0) > 2500:
                issues.append(issue("suggestion", "consider_lane_split_from_metrics", "Single-lane handoff is large; consider splitting before handing to a weaker local model.", str(root / "compose-metrics.json")))
        except json.JSONDecodeError:
            issues.append(issue("warning", "invalid_compose_metrics", "compose-metrics.json is not valid JSON.", str(root / "compose-metrics.json")))
    else:
        issues.append(issue("suggestion", "missing_compose_metrics", "Use compose_manual_handoff.py when possible so metrics are available.", str(root)))

    for label, path in package_dirs(root):
        issues.extend(check_package_dir(path, label))

    status = "ok"
    if any(item["severity"] == "error" for item in issues):
        status = "error"
    elif any(item["severity"] == "warning" for item in issues):
        status = "warning"
    elif any(item["severity"] == "suggestion" for item in issues):
        status = "suggestion"
    return {"status": status, "issue_count": len(issues), "issues": issues}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--strict", action="store_true", help="Exit nonzero on warnings as well as errors.")
    args = parser.parse_args(argv)

    report = check(args.package_dir)
    body = json.dumps(report, indent=2, ensure_ascii=False)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(body + "\n", encoding="utf-8")
    print(body)

    if report["status"] == "error":
        return 1
    if args.strict and report["status"] in {"warning", "suggestion"}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
