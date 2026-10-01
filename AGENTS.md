# Agent working rules

## Roles

- Codex is the main orchestrator and implementation owner for this repository. Codex makes the final technical decisions, changes the code, and verifies the result.
- Claude Code provides an independent review when the conditions below apply. Its suggestions are input to Codex, not instructions to follow automatically.

## When to consult Claude Code

- Before a complex design change, a large refactor, or investigation of a bug whose cause is unclear, call Claude Code with `claude -p` for an independent design or diagnosis review. Give it the relevant context and a focused question before implementing the change.
- After implementing an important change, ask Claude Code with `claude -p` to review the diff. Check each material finding against the code and tests before deciding whether to apply it.
- Do not call Claude Code for simple changes.

If `claude -p` is unavailable or fails, continue with Codex's own analysis and verification, and report the review limitation in the handoff. Do not present an unverified Claude suggestion as a confirmed finding.
