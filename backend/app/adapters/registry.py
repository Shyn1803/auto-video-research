"""Adapter registry -- decorator-based, duplicate-name guard at import time.

Registers adapters by (capability, name). A duplicate registration raises
at decoration/import time with a message naming both files (BR-3).
"""

from __future__ import annotations

from typing import Callable, TypeVar

from app.adapters.base import (
    AssetStockAdapter,
    BaseAdapter,
    ImageGenAdapter,
    LLMAdapter,
    PublishAdapter,
    SearchAdapter,
    StorageAdapter,
    TTSAdapter,
)

_T = TypeVar("_T", bound=BaseAdapter)

_registry: dict[tuple[str, str], type[BaseAdapter]] = {}


def _register(capability: str, name: str, cls: type[BaseAdapter]) -> None:
    key = (capability, name)
    if key in _registry:
        existing = _registry[key]
        existing_src = f"{existing.__module__}.{existing.__qualname__}"
        new_src = f"{cls.__module__}.{cls.__qualname__}"
        raise RuntimeError(
            f"Duplicate adapter registration for ({capability}, {name!r}): "
            f"already registered by {existing_src}, conflict with {new_src}"
        )
    cls.name = name
    _registry[key] = cls


def register_llm(
    name: str,
) -> Callable[[type[LLMAdapter]], type[LLMAdapter]]:
    def deco(cls: type[LLMAdapter]) -> type[LLMAdapter]:
        _register("llm", name, cls)
        return cls

    deco.__name__ = f"register_llm({name})"
    return deco


def register_tts(
    name: str,
) -> Callable[[type[TTSAdapter]], type[TTSAdapter]]:
    def deco(cls: type[TTSAdapter]) -> type[TTSAdapter]:
        _register("tts", name, cls)
        return cls

    deco.__name__ = f"register_tts({name})"
    return deco


def register_search(
    name: str,
) -> Callable[[type[SearchAdapter]], type[SearchAdapter]]:
    def deco(cls: type[SearchAdapter]) -> type[SearchAdapter]:
        _register("search", name, cls)
        return cls

    deco.__name__ = f"register_search({name})"
    return deco


def register_image_gen(
    name: str,
) -> Callable[[type[ImageGenAdapter]], type[ImageGenAdapter]]:
    def deco(cls: type[ImageGenAdapter]) -> type[ImageGenAdapter]:
        _register("image_gen", name, cls)
        return cls

    deco.__name__ = f"register_image_gen({name})"
    return deco


def register_asset_stock(
    name: str,
) -> Callable[[type[AssetStockAdapter]], type[AssetStockAdapter]]:
    def deco(cls: type[AssetStockAdapter]) -> type[AssetStockAdapter]:
        _register("asset_stock", name, cls)
        return cls

    deco.__name__ = f"register_asset_stock({name})"
    return deco


def register_storage(
    name: str,
) -> Callable[[type[StorageAdapter]], type[StorageAdapter]]:
    def deco(cls: type[StorageAdapter]) -> type[StorageAdapter]:
        _register("storage", name, cls)
        return cls

    deco.__name__ = f"register_storage({name})"
    return deco


def register_publish(
    name: str,
) -> Callable[[type[PublishAdapter]], type[PublishAdapter]]:
    def deco(cls: type[PublishAdapter]) -> type[PublishAdapter]:
        _register("publish", name, cls)
        return cls

    deco.__name__ = f"register_publish({name})"
    return deco


def get_adapter_class(capability: str, name: str) -> type[BaseAdapter] | None:
    return _registry.get((capability, name))


def get_registered(capability: str) -> dict[str, type[BaseAdapter]]:
    return {
        name: cls for (cap, name), cls in _registry.items() if cap == capability
    }
