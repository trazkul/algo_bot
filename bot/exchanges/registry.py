from typing import Callable, Dict

from bot.exchanges.base import ExchangeBase

_FACTORIES: Dict[str, Callable[..., ExchangeBase]] = {}


def register_exchange(name: str, factory: Callable[..., ExchangeBase]) -> None:
    _FACTORIES[name.lower()] = factory


def get_exchange(name: str) -> Callable[..., ExchangeBase]:
    key = name.lower()
    if key not in _FACTORIES:
        raise ValueError(f"Unsupported exchange: {name}")
    return _FACTORIES[key]
