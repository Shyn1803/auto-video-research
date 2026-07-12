# Prompt: Security Review

```
Review this change against .claude/rules/security.md.
Check specifically:
1. Can any user-supplied URL reach an HTTP client without an allowlist/adapter boundary? (SSRF — Render Worker must never fetch external URLs.)
2. Does any log statement risk exposing a raw secret (API key, JWT, Fernet master key)?
3. Does ALLOW_PAID=false actually block a paid provider even when a valid key is present?
4. Is every admin-facing mutation audit-logged?
5. Does asset handling reject unknown-license content?
Report each finding as: concrete exploit scenario, not a generic "could be risky."
```
