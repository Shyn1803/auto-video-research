"""Storage adapters.

Importing this package registers ``minio`` (decorator side-effect) so the
registry is populated before a request reaches the assets router -- see
app/adapters/assetstock/__init__.py for the same pattern/rationale.
"""

from app.adapters.storage import minio as minio  # noqa: F401
