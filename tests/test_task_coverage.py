#!/usr/bin/env python3
"""Regression tests for canonical task coverage and root lint enforcement."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "local-handoff" / "scripts" / "compose_manual_handoff.py"
CHECK = ROOT / "local-handoff" / "scripts" / "check_manual_handoff.py"


def lane(name, task_id, depends_on=None):
    return {
        "name": name,
        "objective": f"Implement {task_id}",
        "task_ids": [task_id],
        "depends_on": depends_on or [],
        "allowed_paths": ["src/app.js"],
        "forbidden_paths": ["package-lock.json"],
        "criteria": [{"requirement": f"{task_id} works", "evidence": "npm test", "effect": "observable result"}],
        "boundaries": [{"case": "empty input", "expected": "returns an empty result", "evidence": "npm test"}],
        "validation_commands": [{"cwd": "REPO", "command": "npm test", "expected_exit": 0, "proves": task_id}],
        "worker_steps": ["inspect", "implement", "validate"],
    }


def spec(repo):
    first = lane("foundation", "T001")
    second = lane("integration", "T002", ["01-foundation"])
    for item in (first, second):
        item["validation_commands"][0]["cwd"] = str(repo)
    return {
        "task_name": "task-coverage-test",
        "repo": str(repo),
        "objective": "Implement every unchecked canonical task",
        "context": "Small JS fixture",
        "canonical_task_file": "specs/feature/tasks.md",
        "lanes": [first, second],
        "integration_e2e": [{"cwd": str(repo), "command": "npm test", "expected_exit": 0, "proves": "cross-lane behavior"}],
        "integration_validation": [{"cwd": str(repo), "command": "npm run lint", "expected_exit": 0, "proves": "root lint"}],
        "seam_contract": "Both lanes share src/app.js exports.",
        "seam_invariants": ["The integrated result must equal the tested result."],
    }


def run_compose(data, root):
    root.mkdir(parents=True, exist_ok=True)
    spec_path = root / "input-spec.json"
    out = root / "out"
    spec_path.write_text(json.dumps(data), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(COMPOSE), "--spec", str(spec_path), "--out-dir", str(out), "--force"],
        capture_output=True,
        text=True,
    )
    return proc, out


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "repo"
        (repo / "specs" / "feature").mkdir(parents=True)
        (repo / "specs" / "feature" / "tasks.md").write_text("- [ ] T001 Foundation\n- [ ] T002 Integration\n", encoding="utf-8")
        (repo / "package.json").write_text(json.dumps({"scripts": {"test": "node test.js", "lint": "eslint ."}}), encoding="utf-8")

        valid = spec(repo)
        valid["owner_audit_notes"] = "private audit detail"
        proc, out = run_compose(valid, root)
        assert proc.returncode == 0, proc.stderr
        assert (out / "manual-handoff-spec.json").is_file(), "runner-discoverable spec was not copied"
        machine_spec = json.loads((out / "manual-handoff-spec.json").read_text(encoding="utf-8"))
        assert "owner_audit_notes" not in machine_spec, "owner-only notes leaked into worker-visible machine spec"
        integration = (out / "integration-handoff.md").read_text(encoding="utf-8")
        assert "Canonical Task Coverage" in integration
        assert "T001" in integration and "T002" in integration
        prompt = (out / "lanes" / "01-foundation" / "05-worker-prompt.md").read_text(encoding="utf-8")
        assert "T001" in prompt and "reporting state, not proof" in prompt
        check = subprocess.run([sys.executable, str(CHECK), "--package-dir", str(out)], capture_output=True, text=True)
        assert check.returncode == 0, check.stdout

        missing = spec(repo)
        missing["lanes"] = missing["lanes"][:1]
        proc_missing, _ = run_compose(missing, root / "missing")
        assert proc_missing.returncode == 2
        assert "unassigned_required_tasks" in proc_missing.stderr

        duplicate = spec(repo)
        duplicate["lanes"][1]["task_ids"] = ["T001", "T002"]
        proc_duplicate, _ = run_compose(duplicate, root / "duplicate")
        assert proc_duplicate.returncode == 2
        assert "duplicate_task_assignment" in proc_duplicate.stderr

        no_lint = spec(repo)
        no_lint["integration_validation"] = []
        proc_lint, _ = run_compose(no_lint, root / "no-lint")
        assert proc_lint.returncode == 2
        assert "root_lint_validation_missing" in proc_lint.stderr

    print("PASS: canonical tasks are covered exactly once, root lint is required, and the spec is copied.")


if __name__ == "__main__":
    main()
