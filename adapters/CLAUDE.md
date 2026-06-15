# Local Handoff

When asked to create a manual handoff for a local or external coding agent, use the `local-handoff/` skill in this repository.

Read:

- `local-handoff/SKILL.md`
- `local-handoff/references/manual-handoff-contract.md`

Prepare documents only. Do not launch a local model, runner, implementation loop, or final runner audit. Prefer compact spec first, then compose the document package with `local-handoff/scripts/compose_manual_handoff.py`. Run `local-handoff/scripts/check_manual_handoff.py` before reporting completion.
