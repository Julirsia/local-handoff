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


def check_package_dir(pkg: Path, label: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for name in CORE_FILES:
        if not (pkg / name).exists():
            issues.append(issue("error", "missing_core_file", f"Missing {name}.", str(pkg / name)))

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
    if "fill_before_handoff" in combined_low:
        issues.append(issue("error", "unfilled_validation_placeholder", "Validation placeholder remains; fill public command or explicit manual audit before handoff.", label))
    if "hidden" in combined_low and has_any(combined, ["hidden validation passes", "hidden command passes", "withheld test passes"]):
        issues.append(issue("error", "hidden_success_as_worker_acceptance", "Do not ask worker to prove hidden/withheld validation success.", label))
    owner_shape_terms = ["data-", "zero-count", "exact html", "exact key", "exact attribute", "ordering"]
    owner_notes_text = read(pkg.parent.parent / "owner-audit-notes.md") + "\n" + read(pkg.parent / "owner-audit-notes.md")
    if owner_notes_text and any(term in owner_notes_text.lower() for term in owner_shape_terms):
        public_text = acceptance.lower() + "\n" + validation.lower()
        if not any(term in public_text for term in owner_shape_terms):
            issues.append(issue("suggestion", "hidden_output_shape_overreach", "Owner-only checks appear to assert output-shape details not named in public acceptance.", label))
    if has_any(combined, ["agent_batch_runner.py", "run-agent-batch.sh", "batch.json", "results/worker-runs"]):
        issues.append(issue("error", "runner_artifact_reference", "Manual handoff must not include runner execution artifacts.", label))
    if "benchmark-derived boundary prompts" not in quality.lower():
        issues.append(issue("warning", "missing_benchmark_quality_gates", "07-handoff-quality-gates.md should include benchmark-derived boundary prompts.", label))

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

    if "worker step" not in plan.lower() and "implementation plan" not in plan.lower():
        issues.append(issue("suggestion", "consider_worker_step_plan", "Add an explicit ordered worker step plan.", label))

    command_text = validation.lower()
    for command in re.findall(r"```(?:bash|sh)?\n(.*?)\n```", validation, flags=re.DOTALL | re.IGNORECASE):
        for line in command.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                shlex.split(line)
            except ValueError as exc:
                issues.append(issue("error", "validation_command_static_check_failed", f"Validation command has shell parse error: {exc}", label))
    if "pythonpath" in command_text and "python3 -s" not in command_text and "python -s" not in command_text:
        issues.append(issue("warning", "python_site_path_isolation_gap", "For stdlib/package-less Python validation, prefer PYTHONPATH=. python3 -S ...", label))
    if ".js" in command_text and "node" in command_text and ".mjs" not in command_text and ".cjs" not in command_text and "type" not in combined_low:
        issues.append(issue("suggestion", "js_module_type", "For Node .js ES module validation, state package module type or prefer .mjs/.cjs checks.", label))

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

    if has_any(domain_text, ["normalize", "default", "coerce", "fallback"]):
        for term in ["numeric", "non-string", "boolean", "scalar", "list", "dict"]:
            if term not in domain_low:
                issues.append(issue("suggestion", "consider_public_type_boundary_examples", f"Normalization/defaulting may need public {term} boundary evidence.", label))
                break
    if has_any(domain_text, ["object", "dict", "map", "record"]) and not has_any(domain_text, ["non-string key", "non-string value", "malformed field"]):
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
