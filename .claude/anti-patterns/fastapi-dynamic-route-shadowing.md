# Anti-pattern: A Dynamic Path Segment Registered Before a Literal Sibling Route

**Problem:** registering `GET /resource/{id}` before a literal sibling like `GET /resource/compare` (or `/resource/search`, `/resource/export`, etc.) on the same FastAPI `APIRouter`.

**Symptoms**
- A request to the literal route (`/resource/compare`) 422s instead of hitting its handler, because Starlette matches routes by path *shape* first (any single non-slash segment satisfies `{id}`) — the Python type hint (`id: int`) is only checked *after* the structural match succeeds, so it doesn't help the router "skip" to the next candidate route on a failed conversion.
- Works fine in manual testing if you only ever hit the dynamic route first, or if the two routes happen to be registered in an order that avoids the collision — making this easy to miss until a specific literal path is exercised.

**Impact:** a real endpoint becomes permanently unreachable (returns 422, not 404 — often mistaken for a client bug rather than a routing order bug) as soon as a same-shape dynamic route is added, however innocuous the addition looks.

**Correct Solution:** register every literal-suffix route (`/versions/compare`, `/versions/search`, ...) *before* any dynamic route that shares the same path prefix and segment count (`/versions/{version}`). If both must exist on one router, put a code comment at the dynamic route's definition explaining why the order matters — see `backend/app/api/versions.py`'s `get_version_detail` (task 5-9), which is deliberately declared after `compare_versions` for exactly this reason.

**Detection:** when adding a new `GET .../{param}` route, grep the same router for any literal sibling path with the same segment count and confirm it's registered first. When adding a new literal route, confirm no earlier dynamic route on the same router would match its shape.

**How to Avoid:** default to declaring literal routes before dynamic ones within a router, every time — don't rely on remembering to check case-by-case.
