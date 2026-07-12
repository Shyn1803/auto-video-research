# Workflow: Architecture Change

**Inputs:** a proposed structural change (service split, new external dependency, contract redesign, Layout Engine pipeline change).

**Steps**
1. Architect agent reviews against `docs/ARCHITECTURE.md` and the "tách theo đo đạc" principle — is there a measured need, or is this speculative?
2. Draft an ADR using [templates/adr.md](../templates/adr.md): Context, Decision, Alternatives, Tradeoffs, Consequences, Future Considerations.
3. If it changes a contract (schema/API/event/DB/env), plan the semver/migration path per dev-guide.md §5.
4. Present to the user (Product Owner) for sign-off — architectural decisions in this project are explicitly PO-owned (see "PO 2026-07-11" precedent).
5. On approval: implement, update `docs/ARCHITECTURE.md` §1.1/§11 (component diagram / ADR table) and the matching `docs/specs/*` file, save the ADR in [decisions/](../decisions/).

**Quality Gates:** ADR written before implementation starts; user sign-off obtained; docs updated same-PR as the code.

**Outputs:** ADR file, updated ARCHITECTURE.md, implementation PR(s).

**Success Criteria:** future readers can find why the decision was made without digging through chat history.
