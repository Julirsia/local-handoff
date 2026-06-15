# Local Handoff Instructions

When the user asks for a manual local-agent handoff, create a handoff package rather than implementing the requested code change.

Use `local-handoff/SKILL.md` and `local-handoff/references/manual-handoff-contract.md` as the source of truth. Create a compact JSON spec, run the composer if available, run the checker, and provide the user with the generated package path and worker prompt.

Do not launch local model workers, batch runners, silent implementation loops, or final runner audits.

Required package qualities:

- Public Evidence Matrix maps every product requirement.
- Boundary Examples include concrete expected results.
- Public Boundary Assertion Checklist maps each boundary to validation or manual audit.
- Worker prompt front-loads allowed paths, forbidden paths, validation commands, boundary examples, and stop conditions.
- Broad work is split into lanes by domain or behavior phase.
- Hidden or owner-only checks do not become worker acceptance criteria.
