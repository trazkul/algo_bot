import importlib
import logging
import pkgutil
import sys

from dotenv import load_dotenv

from bot.config import load_config
from bot.core import VolumeBot
from bot.exchanges import get_exchange
from bot.logger import setup_logging


def _load_exchanges() -> None:
    import bot.exchanges as exchanges_pkg

    for module in pkgutil.iter_modules(exchanges_pkg.__path__, exchanges_pkg.__name__ + "."):
        importlib.import_module(module.name)


def _build_exchange(config):
    _load_exchanges()
    factory = get_exchange(config.bot.exchange)
    return factory(config)


def main() -> int:
    load_dotenv()
    config = load_config("config.yaml")
    setup_logging(config.logging.level, config.logging.file)

    logging.getLogger(__name__).info(
        "Loaded config for exchange=%s symbol=%s testnet=%s",
        config.bot.exchange,
        config.bot.symbol,
        config.bot.testnet,
    )

    exchange = _build_exchange(config)

    bot = VolumeBot(
        exchange=exchange,
        symbol=config.bot.symbol,
        category=config.bot.category,
        order_qty=config.bot.order_qty,
        interval_sec=config.bot.interval_sec,
        fill_delay_ms=config.bot.fill_delay_ms,
        max_volume_usdt=config.bot.max_volume_usdt,
        account_type=config.bot.account_type,
        dry_run=config.bot.dry_run,
    )
    bot.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
