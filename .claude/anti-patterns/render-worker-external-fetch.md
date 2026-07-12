# Anti-pattern: Render Worker Fetching External URLs

**Problem:** the render worker (or any Remotion composition it renders) making an HTTP request to a URL not already resolved into a licensed MinIO asset — e.g., an LLM-suggested image URL passed straight into a component's `src`.

**Symptoms**
- A Scene JSON `media` field containing a raw external URL instead of a MinIO path.
- A Remotion primitive component that accepts and fetches an arbitrary URL prop at render time.
- Asset resolution skipped "just for a quick preview."

**Impact:** SSRF risk (render worker becomes a proxy for attacker-controlled fetches), license risk (asset used without recorded `source_url`/`license`/`attribution_required`), and reproducibility risk (external URL can change or disappear, breaking cache-based re-renders).

**Correct Solution:** SRS FR-20 + glossary.md rule 4 — every asset is resolved (fetched, license-checked, hashed, stored) into MinIO *before* it ever appears in a Scene JSON media field. Render worker only ever reads from MinIO.

**Detection:** grep render-worker and `packages/remotion-templates` code for any `fetch`/`http` call inside a component, and any Scene JSON media field that isn't a `minio://` or resolved storage path.

**How to Avoid:** Security Engineer reviews any change to asset resolution or the Remotion primitives that render media; Scene JSON schema should type media fields as resolved-asset references, not free-form URLs, making the anti-pattern a type error, not just a review catch.
