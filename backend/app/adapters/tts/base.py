"""TTS adapter base contract and provider error type."""

from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Raised when a TTS provider fails externally."""

    def __init__(self, message: str, *, retryable: bool = False, provider: str = "") -> None:
        super().__init__(message)
        self.retryable = retryable
        self.provider = provider


class TTSRequest:
    """Immutable input for a single TTS synthesis call."""
    __slots__ = ("text", "voice_id", "speed")

    def __init__(self, text: str, voice_id: str, speed: float = 1.0) -> None:
        self.text = text
        self.voice_id = voice_id
        self.speed = speed

    def cache_key(self, engine: str) -> str:
        import hashlib
        raw = f"{self.text}\x00{self.voice_id}\x00{self.speed}\x00{engine}"
        return hashlib.sha256(raw.encode()).hexdigest()


class TTSResult:
    """Output of a successful TTS synthesis call."""
    __slots__ = ("audio_bytes", "duration_ms", "word_timestamps", "cache_key")

    def __init__(self, audio_bytes: bytes, duration_ms: int,
                 word_timestamps: list[dict], cache_key: str = "") -> None:
        self.audio_bytes = audio_bytes
        self.duration_ms = duration_ms
        self.word_timestamps = word_timestamps
        self.cache_key = cache_key


class TTSAdapter(ABC):
    """Abstract base for all TTS provider adapters."""
    name: str = ""
    is_paid: bool = False

    @abstractmethod
    async def available(self) -> bool:
        pass

    @abstractmethod
    async def synthesize(self, request: TTSRequest) -> TTSResult:
        pass
