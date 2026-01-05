import os
import re
from dataclasses import dataclass
from typing import Any, Dict

import yaml

_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


@dataclass(frozen=True)
class BotConfig:
    exchange: str
    symbol: str
    category: str
    account_type: str
    order_qty: str
    interval_sec: int
    recv_window: int
    fill_delay_ms: int
    max_volume_usdt: str
    dry_run: bool
    testnet: bool


@dataclass(frozen=True)
class ApiConfig:
    key: str
    secret: str


@dataclass(frozen=True)
class BinanceApiConfig:
    key: str
    secret: str


@dataclass(frozen=True)
class LoggingConfig:
    level: str
    file: str


@dataclass(frozen=True)
class AppConfig:
    bot: BotConfig
    api: ApiConfig
    binance_api: BinanceApiConfig
    logging: LoggingConfig


def _resolve_env(value: Any) -> Any:
    if isinstance(value, str):
        def replacer(match: re.Match) -> str:
            env_key = match.group(1)
            return os.getenv(env_key, "")

        return _ENV_PATTERN.sub(replacer, value)
    if isinstance(value, dict):
        return {k: _resolve_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env(v) for v in value]
    return value


def load_config(path: str) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw: Dict[str, Any] = yaml.safe_load(f)

    resolved = _resolve_env(raw)

    bot = resolved["bot"]
    api = resolved["api"]
    logging = resolved["logging"]
    binance_api = resolved.get("binance_api", {})

    return AppConfig(
        bot=BotConfig(
            exchange=bot["exchange"],
            symbol=bot["symbol"],
            category=bot["category"],
            account_type=bot["account_type"],
            order_qty=str(bot["order_qty"]),
            interval_sec=int(bot["interval_sec"]),
            recv_window=int(bot["recv_window"]),
            fill_delay_ms=int(bot["fill_delay_ms"]),
            max_volume_usdt=str(bot["max_volume_usdt"]),
            dry_run=bool(bot["dry_run"]),
            testnet=bool(bot["testnet"]),
        ),
        api=ApiConfig(
            key=str(api["key"]),
            secret=str(api["secret"]),
        ),
        binance_api=BinanceApiConfig(
            key=str(binance_api.get("key", "")),
            secret=str(binance_api.get("secret", "")),
        ),
        logging=LoggingConfig(
            level=str(logging["level"]),
            file=str(logging["file"]),
        ),
    )
