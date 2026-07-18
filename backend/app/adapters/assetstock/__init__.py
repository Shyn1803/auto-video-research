"""Stock-asset adapters.

Importing this package registers every concrete provider (decorator
side-effect via ``@register_asset_stock``) -- ``app.api.assets`` imports
this package so the registry is populated before any request reaches the
router. Sibling adapter packages (llm/tts/search/...) don't yet do this
consistently at app-import time; that's a pre-existing gap outside this
task's scope (see 5-3 retrospective) -- fixed here only for asset_stock,
which this task's endpoints require to actually work.
"""

from app.adapters.assetstock import pexels as pexels  # noqa: F401
from app.adapters.assetstock import pixabay as pixabay  # noqa: F401
from app.adapters.assetstock import unsplash as unsplash  # noqa: F401
