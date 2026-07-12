# Checklist: Architecture Review

- [ ] Split/new-service decision backed by measured need, not speculation
- [ ] New module interface is a Pydantic model (future NATS-extraction compatible)
- [ ] External capability access goes through an adapter, no direct SDK/HTTP call from business logic
- [ ] Layout Engine boundary respected — AI output has no layout/position/font/animation field
- [ ] ADR drafted for any non-trivial structural decision ([templates/adr.md](../templates/adr.md))
- [ ] `docs/ARCHITECTURE.md` §1.1/§11 updated if topology or ADR list changed
