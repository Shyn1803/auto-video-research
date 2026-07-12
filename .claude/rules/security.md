# Rule: Security

See [agents/security-engineer.md](../agents/security-engineer.md) for the review role; this is the enforceable rule set.

- JWT access token 15 min, refresh 7 days with rotation. RBAC middleware on every route, not opt-in.
- API keys encrypted at rest with Fernet; master key from env, KMS when on cloud. Never store a plaintext key anywhere, including logs or DB dumps used for debugging.
- `ALLOW_PAID=false` must be a hard gate — a paid provider with a valid key still must not activate unless this flag is explicitly true.
- Render Worker never fetches an external URL — only resolved, licensed assets already in MinIO (glossary.md rule 4). Any code path where a render job could reach an attacker-controlled URL is an SSRF bug.
- Every asset requires `source_url`, `license`, `attribution_required`, `provider` — reject anything with unknown license (SRS FR-20).
- Rate limiting by user + IP; CORS allowlist, not wildcard.
- Admin actions (permission changes, key management, prompt edits) are audit-logged — no silent admin mutation.
