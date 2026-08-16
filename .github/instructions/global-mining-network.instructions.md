---
applyTo: "**"
---
Use docs/global-mining-network-official-specification.md and docs/game-design-brief-v1.md as canonical design context.

When proposing or implementing changes:
- Preserve one logical global chain.
- Keep server authority over balances, rewards, progression, and block state.
- Use time-based reconstruction (state changes + timestamps + aggregation).
- Avoid per-second per-player update models.
- Avoid real cryptocurrency mechanics or real mining behavior.
- Keep systems modular and data-driven so content can scale without fundamental rewrites.

If a user request contradicts these constraints, explain the conflict and offer the closest compliant option.
