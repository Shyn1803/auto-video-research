# Prompt: API Design

```
Design this endpoint against docs/specs/api-spec.md conventions (error format, SSE usage, standard flow shape).
Confirm:
- Request/response types will be Pydantic-first, so frontend can generate types via make gen-api-client — never design a shape the generator can't produce cleanly.
- No business logic in the router — it calls a service.
- If this is a contract change (new/changed field), it needs a semver note and docs/specs/api-spec.md update in the same PR.
Produce: endpoint signature, request/response schema, error cases, and the story ID it serves.
```
