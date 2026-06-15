# Local Handoff

Local Handoff is a reusable agent skill for creating detailed manual handoff packages for local or external coding agents. It stops at documents: no runner launch, no silent worker process, no implementation loop, and no final runner audit.

The goal is to let a stronger frontier agent produce a precise handoff that a local model can execute reliably, including lane splits, boundary examples, validation evidence, and manual preflight checks.

## What It Creates

From a compact JSON spec, the composer expands a manual handoff package:

```text
<task>-handoff/
  README.md
  00-context.md
  01-task.md
  02-acceptance.md
  03-implementation-plan.md
  04-validation.md
  05-worker-prompt.md
  06-review-checklist.md
  07-handoff-quality-gates.md
  compose-metrics.json
  manual-preflight.json
```

For larger work, add `lanes` to the spec. The composer creates per-lane handoffs plus an `integration-handoff.md`.

## Benchmark-Derived Gates

The skill carries the handoff-quality checks learned from external batch benchmark runs:

- Public Evidence Matrix for every product requirement.
- Boundary Examples with concrete expected results.
- Public Boundary Assertion Checklist linking each boundary to public validation or manual audit.
- Worker prompt front-loading for weaker local models.
- Lane splitting by domain or behavior phase.
- Phase Decomposition Rationale for split or intentionally unsplit work.
- Hidden/Public Alignment so owner-only checks do not hide product requirements.
- Checks for action branch coverage, report-field normalization, type boundaries, empty-state downstream effects, zero values, money rounding, response payload freshness, Python site-path isolation, JavaScript module type, and runner artifact leakage.
- Spec lint before composition, so typos such as `critera` fail before creating a polished but incomplete package.
- Embedded relevant code excerpts for target functions, types, helper APIs, and tests when local workers may not explore the repo reliably.
- Worker capability guidance (`small`, `medium`, `large`), explicit anti-patterns, and a bounded self-repair loop.

Runner-only result collection and final audit artifacts are intentionally excluded.

See `docs/coverage-audit.md` for the safeguard-by-safeguard mapping from the runner-backed batch handoff workflow to this manual handoff package.

## Quick Start

```bash
git clone https://github.com/Julirsia/local-handoff.git
cd local-handoff

python3 local-handoff/scripts/compose_manual_handoff.py \
  --spec examples/sample-spec.json \
  --out-dir /tmp/sample-handoff \
  --force

python3 local-handoff/scripts/check_manual_handoff.py \
  --package-dir /tmp/sample-handoff \
  --json-out /tmp/sample-handoff/manual-preflight.json
```

Give `/tmp/sample-handoff/lanes/<lane>/05-worker-prompt.md` or `/tmp/sample-handoff/05-worker-prompt.md` to the local worker.

## Compact Spec Shape

```json
{
  "task_name": "short task name",
  "repo": "/absolute/path/to/repo",
  "objective": "one concrete end state",
  "context": "repo and behavior context",
  "allowed_paths": ["src/example.py"],
  "forbidden_paths": ["pyproject.toml", "*.egg-info/**"],
  "worker_capability": "small",
  "scope_breadth": "full requested experience, not a minimal stub; list the required screens, mechanics, modes, and content counts",
  "architecture_freedom": "pin WHAT tightly, but leave HOW flexible; allow HTML/CSS for UI/HUD unless an integration contract forbids it",
  "visual_acceptance": [
    "primary interactive controls are at least 40px tall on desktop and mobile",
    "key rendered entities are at least 6% of viewport height or otherwise clearly legible",
    "main feedback animations remain visible for at least 300ms"
  ],
  "reference_assets": [
    "mockup.png, screenshot link, comparable product reference, or described density"
  ],
  "relevant_files": [
    {
      "path": "src/example.py",
      "why": "contains the target behavior",
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

Add `lanes` for sequential smaller handoffs. Each lane may override objective, allowed paths, forbidden paths, criteria, boundaries, validation commands, and worker steps.

Use `relevant_files` selectively. Excerpts cost frontier tokens during handoff creation, but they usually save more total work when a local worker would otherwise hallucinate APIs, miss existing return shapes, or repeatedly fail validation. For `worker_capability: "small"`, keep most lanes to five or fewer excerpts and split the task when more code context is required.

For UI, game, or visual-heavy work, prefer a product brief style for the first implementation pass:

- Tighten **WHAT**: required screens, mechanics, content breadth, visual density, interaction feedback, and manual acceptance.
- Loosen **HOW**: do not force file layout, helper APIs, or canvas-only UI unless a real integration contract requires it.
- Allow HTML/CSS for HUDs, menus, overlays, cards, sliders, logs, and setup screens. Keep only correctness-critical logic pure/testable.
- Add quantified `visual_acceptance` and at least one `reference_assets` entry so "manual audit" does not collapse into vague adjectives.
- Use `examples/game-ui-spec.json` as the starting point for a playable prototype handoff.

## Install for Codex

Codex can use this as a skill folder or as project instructions.

```bash
mkdir -p ~/.codex/skills
cp -R local-handoff ~/.codex/skills/local-handoff
```

Then ask Codex:

```text
Use $local-handoff to create a manual handoff package for this task.
```

For project-level always-on guidance, copy `adapters/AGENTS.md` into a repository root. Codex reads `AGENTS.md` instruction files from global and project scopes according to OpenAI's Codex documentation: https://developers.openai.com/codex/guides/agents-md

## Install for Claude

Claude Code supports skills as folders containing `SKILL.md`.

```bash
mkdir -p ~/.claude/skills
cp -R local-handoff ~/.claude/skills/local-handoff
```

Invoke it with:

```text
/local-handoff Create a manual handoff package for this task.
```

Claude Code documents that skill command names come from the skill directory under `~/.claude/skills/` or `.claude/skills/`: https://code.claude.com/docs/en/skills

For Claude.ai custom skills, zip the `local-handoff/` folder and upload it through Customize > Skills > Create skill > Upload a skill. Anthropic's help center documents the ZIP upload flow: https://support.claude.com/en/articles/12512180-use-skills-in-claude

## Install for OpenCode

OpenCode supports `SKILL.md` skills and searches several project/global locations.

Project install:

```bash
mkdir -p .opencode/skills
cp -R local-handoff .opencode/skills/local-handoff
```

Global install:

```bash
mkdir -p ~/.config/opencode/skills
cp -R local-handoff ~/.config/opencode/skills/local-handoff
```

OpenCode also recognizes `.claude/skills/` and `.agents/skills/` compatibility paths. Its skill discovery locations are documented here: https://opencode.ai/docs/skills/

For always-on project instructions, copy `adapters/AGENTS.md` into the repository root. OpenCode documents `AGENTS.md` rules here: https://opencode.ai/docs/rules/

## Use with Pi or Other Local CLIs

If the worker tool does not have a native skill system, use the generated handoff directly:

1. Run the composer and checker from this repository.
2. Give the worker `05-worker-prompt.md`.
3. Give support files only when the worker needs more context.
4. Ask the worker to return the audit packet described in `06-review-checklist.md`.

You can also paste `adapters/AGENTS.md` into the tool's system prompt or project instructions if it supports persistent instructions.

## Install for GitHub Copilot

Copilot supports repository custom instructions through `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`, and `AGENTS.md`.

Project-wide install:

```bash
mkdir -p .github
cp adapters/copilot-instructions.md .github/copilot-instructions.md
cp adapters/AGENTS.md AGENTS.md
```

GitHub's Copilot documentation describes repository custom instructions and `AGENTS.md` support here: https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions

VS Code also documents `.github/copilot-instructions.md`, `AGENTS.md`, and Claude-compatible instruction files: https://code.visualstudio.com/docs/agent-customization/custom-instructions

## Repository Layout

```text
local-handoff/
  SKILL.md
  agents/openai.yaml
  references/manual-handoff-contract.md
  scripts/compose_manual_handoff.py
  scripts/check_manual_handoff.py
adapters/
  AGENTS.md
  CLAUDE.md
  copilot-instructions.md
examples/
  sample-spec.json
```

## Validation

Run:

```bash
python3 -m py_compile local-handoff/scripts/*.py
python3 local-handoff/scripts/compose_manual_handoff.py \
  --spec examples/sample-spec.json \
  --out-dir /tmp/local-handoff-smoke \
  --force
python3 local-handoff/scripts/check_manual_handoff.py \
  --package-dir /tmp/local-handoff-smoke \
  --json-out /tmp/local-handoff-smoke/manual-preflight.json
```

The checker may return suggestions for intentionally incomplete sample specs. Errors should be fixed before giving a handoff to a worker.
