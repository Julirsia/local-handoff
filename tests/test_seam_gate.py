#!/usr/bin/env python3
"""Regression test for the cross-lane seam gate.

A multi-lane handoff whose integration handoff has no executable end-to-end gate must be
flagged (`integration_seam_gate_missing`). Providing an executable `integration_e2e` command
(plus a consistency invariant) clears it. Run: python3 tests/test_seam_gate.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "local-handoff" / "scripts"
COMPOSE = SCRIPTS / "compose_manual_handoff.py"
CHECK = SCRIPTS / "check_manual_handoff.py"


def lane(name, root):
    return {
        "name": name,
        "objective": f"{name} lane objective",
        "context": f"{name} lane context",
        "allowed_paths": [f"{root}/main.js"],
        "forbidden_paths": [f"Do not touch the other component's directory in the {name} lane."],
        "criteria": [{"requirement": "does its thing", "evidence": "npm test", "effect": "works"}],
        "boundaries": [{"case": "empty input", "expected": "no crash"}],
        "validation_commands": [
            {"cwd": f"/tmp/repo/{root}", "command": "npm test", "expected_exit": 0, "proves": "lane passes"}
        ],
        "worker_steps": ["implement", "test"],
    }


def base_spec():
    return {
        "task_name": "seam-test",
        "repo": "/tmp/repo",
        "objective": "build a two-component app",
        "context": "server + web",
        "lanes": [lane("api", "server"), lane("web", "web")],
        "integration_objective": "run both together",
        "integration_checks": ["both components start"],
        "integration_validation": [
            {"cwd": "/tmp/repo/server", "command": "npm test", "expected_exit": 0, "proves": "server tests pass"}
        ],
    }


def compose_and_check(spec):
    with tempfile.TemporaryDirectory() as tmp:
        spec_path = Path(tmp) / "spec.json"
        out_dir = Path(tmp) / "pkg"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        subprocess.run(
            [sys.executable, str(COMPOSE), "--spec", str(spec_path), "--out-dir", str(out_dir), "--force"],
            check=True, capture_output=True, text=True,
        )
        proc = subprocess.run(
            [sys.executable, str(CHECK), "--package-dir", str(out_dir)],
            capture_output=True, text=True,
        )
        report = json.loads(proc.stdout)
        codes = {i["code"] for i in report["issues"]}
        integration = (out_dir / "integration-handoff.md").read_text(encoding="utf-8")
        return codes, integration


def main():
    # 1) No executable end-to-end gate -> must be flagged.
    codes, integration = compose_and_check(base_spec())
    assert "integration_seam_gate_missing" in codes, f"expected seam gate warning, got: {sorted(codes)}"
    assert "Executable Integration Gate" in integration, "integration handoff missing the seam gate section"
    assert "Cross-Lane Seam Contract" in integration, "integration handoff missing the seam contract section"

    # 2) Provide an executable end-to-end gate + a consistency invariant -> must clear.
    spec = base_spec()
    spec["integration_e2e"] = [{
        "cwd": "/tmp/repo",
        "command": "node e2e.mjs",
        "expected_exit": 0,
        "proves": "drives the web client's own api module against the running server end to end",
    }]
    spec["seam_invariants"] = [
        "dashboard.upcomingRenewals must match the notifications endpoint's renewals (same value)",
    ]
    codes2, _ = compose_and_check(spec)
    assert "integration_seam_gate_missing" not in codes2, f"gate should clear, got: {sorted(codes2)}"
    assert "consider_seam_consistency_invariant" not in codes2, f"invariant present, should not suggest: {sorted(codes2)}"

    print("PASS: seam gate fires without an executable e2e gate and clears with one.")


if __name__ == "__main__":
    main()
