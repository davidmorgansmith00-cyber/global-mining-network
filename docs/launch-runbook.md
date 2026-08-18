# Launch Runbook

## Timeline
- **T-4h:** Final checklist verification, team briefing
- **T-2h:** Close signups and publish warning banner
- **T-1h:** Pause commerce entrypoints
- **T-0:** Create genesis block, announce hash, restart game services
- **T+5m:** Monitor latency/error rate for critical spikes
- **T+30m:** Declare all-clear if no critical incidents
- **T+2h:** Stabilization review
- **T+24h:** Post-launch review meeting

## Rollback Procedure (1-2h target)
1. Incident commander declares rollback.
2. Publish rollback notice (Discord, in-game, status page).
3. Halt new block acceptance.
4. Restore pre-launch backup.
5. Restart core services.
6. Verify data integrity and chain consistency.
7. Re-open clients after green checks.
