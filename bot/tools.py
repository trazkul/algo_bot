import argparse
import json
import logging

from dotenv import load_dotenv

from bot.config import load_config
from bot.exchanges.bybit import BybitClient
from bot.exchanges.binance import BinanceFuturesClient
from bot.logger import setup_logging


def show_balances() -> None:
    load_dotenv()
    config = load_config("config.yaml")
    setup_logging(config.logging.level, config.logging.file)

    client = BybitClient(
        api_key=config.api.key,
        api_secret=config.api.secret,
        testnet=config.bot.testnet,
        recv_window=config.bot.recv_window,
    )

    data = client.get_wallet_balances(config.bot.account_type)
    logging.getLogger(__name__).info("Wallet balances: %s", json.dumps(data, ensure_ascii=False))


def cancel_all_orders() -> None:
    load_dotenv()
    config = load_config("config.yaml")
    setup_logging(config.logging.level, config.logging.file)

    if config.bot.exchange.lower() == "bybit":
        client = BybitClient(
            api_key=config.api.key,
            api_secret=config.api.secret,
            testnet=config.bot.testnet,
            recv_window=config.bot.recv_window,
        )
    elif config.bot.exchange.lower() == "binance":
        client = BinanceFuturesClient(
            api_key=config.binance_api.key,
            api_secret=config.binance_api.secret,
            testnet=config.bot.testnet,
        )
    else:
        raise ValueError(f"Unsupported exchange: {config.bot.exchange}")

    result = client.cancel_all_orders(config.bot.symbol, config.bot.category)
    logging.getLogger(__name__).info("Cancel all orders result: %s", json.dumps(result, ensure_ascii=False))


def list_open_orders() -> None:
    load_dotenv()
    config = load_config("config.yaml")
    setup_logging(config.logging.level, config.logging.file)

    if config.bot.exchange.lower() == "bybit":
        client = BybitClient(
            api_key=config.api.key,
            api_secret=config.api.secret,
            testnet=config.bot.testnet,
            recv_window=config.bot.recv_window,
        )
    elif config.bot.exchange.lower() == "binance":
        client = BinanceFuturesClient(
            api_key=config.binance_api.key,
            api_secret=config.binance_api.secret,
            testnet=config.bot.testnet,
        )
    else:
        raise ValueError(f"Unsupported exchange: {config.bot.exchange}")

    result = client.list_open_orders(config.bot.symbol, config.bot.category)
    logging.getLogger(__name__).info("Open orders: %s", json.dumps(result, ensure_ascii=False))


def close_position() -> None:
    load_dotenv()
    config = load_config("config.yaml")
    setup_logging(config.logging.level, config.logging.file)

    if config.bot.exchange.lower() == "bybit":
        client = BybitClient(
            api_key=config.api.key,
            api_secret=config.api.secret,
            testnet=config.bot.testnet,
            recv_window=config.bot.recv_window,
        )
    elif config.bot.exchange.lower() == "binance":
        client = BinanceFuturesClient(
            api_key=config.binance_api.key,
            api_secret=config.binance_api.secret,
            testnet=config.bot.testnet,
        )
    else:
        raise ValueError(f"Unsupported exchange: {config.bot.exchange}")

    size = client.get_position_size(config.bot.symbol, config.bot.category)
    if str(size) in ("0", "0.0", "0.00", ""):
        logging.getLogger(__name__).info("No open position for %s", config.bot.symbol)
        return
    result = client.close_position(config.bot.symbol, config.bot.category, size)
    logging.getLogger(__name__).info("Close position result: %s", json.dumps(result, ensure_ascii=False))


def close_all() -> None:
    cancel_all_orders()
    close_position()


def main() -> None:
    parser = argparse.ArgumentParser(description="Bot tools")
    parser.add_argument(
        "command",
        choices=["balances", "cancel-all", "open-orders", "close-position", "close-all"],
        help="balances: show wallet balances (Bybit only), cancel-all: cancel all open orders, open-orders: list open orders, close-position: close position by symbol, close-all: cancel orders and close position",
    )
    args = parser.parse_args()

    if args.command == "balances":
        show_balances()
        return
    if args.command == "cancel-all":
        cancel_all_orders()
        return
    if args.command == "open-orders":
        list_open_orders()
        return
    if args.command == "close-position":
        close_position()
        return
    if args.command == "close-all":
        close_all()


if __name__ == "__main__":
    main()
