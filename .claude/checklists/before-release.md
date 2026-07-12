# Checklist: Before Release

- [ ] Fresh clone + `.env.example` (0 API keys) produces a working video end-to-end (local-first promise)
- [ ] `ALLOW_PAID=false` and `MODE1_AUTOPUBLISH=off` are the shipped defaults
- [ ] Provider failover verified under a simulated failure for ≥1 capability
- [ ] Security review complete (see [security-review.md](security-review.md))
- [ ] Cost cap (`DAILY_COST_CAP`) actually pauses the pipeline when breached
- [ ] Backup/restore path verified (PostgreSQL dump+WAL, MinIO versioning) if this release touches storage
- [ ] `docs/plan.md` milestone status updated
- [ ] Release notes written ([templates/release-note.md](../templates/release-note.md))
- [ ] Rollback plan exists for this release
