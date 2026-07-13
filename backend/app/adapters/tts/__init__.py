"""Text-to-speech adapters."""

_registry: dict[str, type] = {}


def register_tts(name: str):
    def decorator(cls: type) -> type:
        _registry[name] = cls
        return cls
    return decorator


def get_tts_adapter(name: str) -> type:
    try:
        return _registry[name]
    except KeyError:
        raise KeyError(
            f"No TTS adapter registered for '{name}'. "
            f"Available: {list(_registry)}"
        ) from None
