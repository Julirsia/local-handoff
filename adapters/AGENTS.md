# Local Handoff Instructions

Use this when the user asks for a manual handoff, local model prompt, handoff docs only, no-runner delegation, or a request package for another coding agent.

Do only document preparation. Do not launch worker CLIs, batch runners, silent implementation loops, or final runner audits.

Workflow:

1. Read `local-handoff/SKILL.md`.
2. Read `local-handoff/references/manual-handoff-contract.md`.
3. Inspect the target repo enough to write accurate context, allowed paths, forbidden paths, validation commands, acceptance criteria, boundary examples, and lane splits.
4. Write a compact JSON spec first.
5. Run `local-handoff/scripts/compose_manual_handoff.py` to generate the handoff package when possible.
6. Run `local-handoff/scripts/check_manual_handoff.py` and save `manual-preflight.json`.
7. Fix checker errors. Treat warnings and suggestions as design feedback.
8. Return the package path, manual preflight status, and the primary worker prompt path.

The worker prompt must be self-contained and front-load allowed paths, forbidden paths, validation commands, boundary examples, and stop conditions.
