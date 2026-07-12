# Checklist: Security Review

- [ ] No raw secret (API key, JWT, Fernet master key) logged or committed
- [ ] Render Worker cannot reach an external URL — only resolved MinIO assets
- [ ] `ALLOW_PAID=false` actually blocks paid providers even with a valid key present
- [ ] Every asset has `source_url`, `license`, `attribution_required`, `provider` — unknown license rejected
- [ ] RBAC enforced on the route, not assumed from the UI hiding a button
- [ ] Rate limiting + CORS allowlist in place for any new public endpoint
- [ ] Admin mutation is audit-logged
- [ ] No SSRF surface: user-supplied URL never reaches an unbounded HTTP client
