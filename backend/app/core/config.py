"""Typed application settings loaded from the environment.

Config precedence: env > api_keys DB table (Admin UI, FR-15) > default.
Adapters receive ProviderSettings via constructor; never os.environ directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Maps (capability, provider) -> env-var for the API key.
# Empty string = free/local provider (no key needed).
# DB lookup (task 3-4) plugs into ProviderSettings.resolve without touching
# adapter code.
_ENV_MAP: dict[tuple[str, str], str] = {
    ("llm", "ollama"): "OLLAMA_API_KEY",
    ("llm", "gemini"): "GEMINI_API_KEY",
    ("llm", "groq"): "GROQ_API_KEY",
    ("llm", "openrouter_free"): "OPENROUTER_API_KEY",
    ("llm", "openrouter_paid"): "OPENROUTER_API_KEY",
    ("llm", "mistral"): "MISTRAL_API_KEY",
    ("llm", "bge_m3_local"): "",
    ("tts", "edge_tts"): "",
    ("tts", "local_tts"): "TTS_LOCAL_MODEL",
    ("tts", "fpt"): "FPT_API_KEY",
    ("tts", "google_tts"): "GOOGLE_TTS_CREDENTIALS",
    ("tts", "zalo"): "ZALO_API_KEY",
    ("tts", "elevenlabs"): "ELEVENLABS_API_KEY",
    ("search", "searxng"): "SEARXNG_URL",
    ("search", "tavily"): "TAVILY_API_KEY",
    ("search", "brave"): "BRAVE_API_KEY",
    ("search", "serpapi"): "SERPAPI_KEY",
    ("image_gen", "local_sd"): "SD_URL",
    ("image_gen", "gemini_image"): "GEMINI_API_KEY",
    ("asset_stock", "pexels"): "PEXELS_API_KEY",
    ("asset_stock", "pixabay"): "PIXABAY_API_KEY",
    ("asset_stock", "unsplash"): "UNSPLASH_ACCESS_KEY",
    ("storage", "minio"): "MINIO_ACCESS_KEY",
    ("storage", "s3"): "AWS_ACCESS_KEY_ID",
    ("publish", "download"): "",
    ("publish", "youtube"): "YOUTUBE_CLIENT_ID",
    ("publish", "tiktok"): "TIKTOK_CLIENT_KEY",
    ("publish", "facebook"): "FACEBOOK_APP_ID",
    ("publish", "linkedin"): "LINKEDIN_CLIENT_ID",
}


@dataclass(frozen=True)
class ProviderSettings:
    """Config for a single adapter invocation.

    Adapters receive this via constructor; must NOT call os.environ directly.
    """

    provider_name: str = ""
    api_key: str = ""
    base_url: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    def with_api_key(self, key: str) -> "ProviderSettings":
        new = object.__new__(ProviderSettings)
        object.__setattr__(new, "provider_name", self.provider_name)
        object.__setattr__(new, "api_key", key)
        object.__setattr__(new, "base_url", self.base_url)
        object.__setattr__(new, "extra", dict(self.extra))
        return new

    @staticmethod
    def resolve(
        capability: str,
        provider_name: str,
        *,
        env: dict[str, str] | None = None,
        db_session: object = None,  # noqa: D401 -- future task 3-4
    ) -> "ProviderSettings":
        """Resolve settings: env -> DB -> default."""
        watch = env if env is not None else os.environ
        api_key = ""
        env_var = _ENV_MAP.get((capability, provider_name), "")
        if env_var:
            api_key = watch.get(env_var, "")
        _ = db_session  # api_keys table stub for task 3-4
        base_url = watch.get(f"{capability.upper()}_URL", "")
        return ProviderSettings(
            provider_name=provider_name, api_key=api_key, base_url=base_url
        )


class Settings(BaseSettings):
    """All configurable knobs for the API process.

    Defaults match docs/CONFIGURATION.md sections 1-11.
    """

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    # Core
    app_env: str = "development"
    app_version: str = "0.1.0"
    database_url: str = "postgresql://app:app@localhost:5432/app"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Cost gate
    allow_paid: bool = False
    daily_cost_cap_usd: float = 0.0

    # Provider chains (per docs/CONFIGURATION.md sections 3-8)
    llm_chain_cheap: str = "ollama,gemini,openrouter_free"
    llm_chain_strong: str = "gemini,groq,openrouter_free,openrouter_paid"
    embedding_chain: str = "bge_m3_local,gemini_embedding"
    tts_chain: str = "edge_tts,local_tts,fpt"
    search_chain: str = "searxng,tavily,brave,serpapi"
    image_gen_chain: str = "local_sd,gemini_image"
    asset_chain: str = "pexels,pixabay,unsplash"
    storage_provider: str = "minio"
    publish_platforms: str = "download"

    # LLM model selection
    ollama_url: str = "http://ollama:11434"
    ollama_model_cheap: str = "qwen2.5:14b-instruct"
    ollama_model_strong: str = "qwen2.5:32b-instruct"
    gemini_model: str = "gemini-flash-latest"
    groq_model: str = ""
    openrouter_paid_model: str = ""
    embedding_device: str = "cpu"

    # TTS
    tts_voice_female: str = "vi-VN-HoaiMyNeural"
    tts_voice_male: str = "vi-VN-NamMinhNeural"
    tts_local_model: str = ""

    # Subtitle alignment
    subtitle_aligner: str = "faster_whisper"
    whisper_model: str = "phowhisper-small"

    # Search
    searxng_url: str = ""

    # Crawl
    crawl_engine: str = "trafilatura"
    crawl_respect_robots: bool = True
    crawl_cache_ttl_days: int = 30

    # Ranking (Task 4-4, "Decisions already locked" defaults)
    ranking_weight_recency: float = 0.3
    ranking_weight_relevance: float = 0.3
    ranking_weight_trust: float = 0.25
    ranking_weight_confirm: float = 0.15
    similarity_threshold: float = 0.92
    max_sources_per_project: int = 20

    # Image / asset
    sd_url: str = ""
    sd_model: str = "flux1-schnell"
    gemini_image_model: str = "gemini-2.0-flash-exp-image-generation"
    pexels_api_key: str = ""
    pixabay_api_key: str = ""
    unsplash_access_key: str = ""

    # Storage
    minio_url: str = "http://minio:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    s3_bucket: str = "avr-uploads"
    aws_region: str = "us-east-1"

    # Publish
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    facebook_app_id: str = ""
    facebook_app_secret: str = ""
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    publish_ai_disclosure: bool = True

    # Notification / Monitoring
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    smtp_url: str = ""
    sentry_dsn: str = ""
    langfuse_host: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    # Auth bootstrap
    admin_email: str = "admin@example.com"
    admin_password: str = "changeme"

    def provider_settings(
        self,
        capability: str,
        provider_name: str,
    ) -> "ProviderSettings":
        """Resolve ProviderSettings for one provider from current env."""
        return ProviderSettings.resolve(
            capability, provider_name, env=self.model_dump()
        )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings instance."""
    return Settings()
