import logging
import time
from decimal import Decimal, InvalidOperation
from typing import Any, Dict

from bot.exchanges.base import ExchangeBase


class VolumeBot:
    def __init__(
        self,
        exchange: ExchangeBase,
        symbol: str,
        category: str,
        order_qty: str,
        interval_sec: int,
        fill_delay_ms: int,
        max_volume_usdt: str,
        account_type: str,
        dry_run: bool,
    ) -> None:
        self._exchange = exchange
        self._symbol = symbol
        self._category = category
        self._order_qty = order_qty
        self._interval_sec = interval_sec
        self._fill_delay_ms = fill_delay_ms
        self._dry_run = dry_run
        self._max_volume_usdt = self._parse_decimal(max_volume_usdt)
        self._account_type = account_type
        self._total_volume_usdt = Decimal("0")
        self._log = logging.getLogger(self.__class__.__name__)

    def run(self) -> None:
        self._log.info("Starting volume bot")
        while True:
            try:
                if self._max_volume_usdt > 0 and self._total_volume_usdt >= self._max_volume_usdt:
                    self._log.info(
                        "Reached max volume in USDT: total=%s limit=%s",
                        self._total_volume_usdt,
                        self._max_volume_usdt,
                    )
                    break

                last_price = self._exchange.get_last_price(self._symbol, self._category)
                available_usdt = self._get_available_usdt()
                required_usdt = self._estimate_required_usdt(last_price)
                if available_usdt < required_usdt:
                    self._log.warning(
                        "Недостаточно USDT для сделки: доступно=%s требуется=%s",
                        available_usdt,
                        required_usdt,
                    )
                    time.sleep(self._interval_sec)
                    continue

                buy_order = self._build_order("Buy")
                sell_order = self._build_order("Sell", reduce_only=True)

                if self._dry_run:
                    self._log.info("DRY RUN buy=%s", buy_order)
                    self._log.info("DRY RUN sell=%s", sell_order)
                    self._log.info("DRY RUN cycle volume USDT=%s", cycle_volume)
                else:
                    self._log.info("Placing BUY order")
                    buy_resp = self._exchange.place_order(buy_order)
                    self._log.info("BUY response: %s", buy_resp)
                    buy_order_id = self._extract_order_id(buy_resp)
                    if not buy_order_id:
                        self._log.warning("BUY failed, skipping SELL")
                        time.sleep(self._interval_sec)
                        continue
                    buy_filled = self._wait_filled(self._symbol, buy_order_id)
                    if not buy_filled:
                        self._log.warning("BUY not filled, skipping SELL")
                        time.sleep(self._interval_sec)
                        continue

                    time.sleep(self._fill_delay_ms / 1000.0)

                    self._log.info("Placing SELL order")
                    sell_resp = self._exchange.place_order(sell_order)
                    self._log.info("SELL response: %s", sell_resp)
                    sell_order_id = self._extract_order_id(sell_resp)
                    if not sell_order_id:
                        self._log.warning("SELL failed, volume not counted")
                        time.sleep(self._interval_sec)
                        continue
                    sell_filled = self._wait_filled(self._symbol, sell_order_id)
                    if not sell_filled:
                        self._log.warning("SELL not filled, volume not counted")
                        time.sleep(self._interval_sec)
                        continue

                cycle_volume = self._extract_filled_volume(buy_filled, sell_filled, last_price)
                self._total_volume_usdt += cycle_volume
                self._log.info("Total volume USDT=%s", self._total_volume_usdt)
            except Exception as exc:
                self._log.exception("Cycle error: %s", exc)

            time.sleep(self._interval_sec)

    def _build_order(self, side: str, reduce_only: bool = False) -> Dict[str, Any]:
        order: Dict[str, Any] = {
            "category": self._category,
            "symbol": self._symbol,
            "side": side,
            "orderType": "Market",
            "qty": self._order_qty,
            "timeInForce": "GTC",
        }
        if reduce_only:
            order["reduceOnly"] = True
        return order

    def _estimate_cycle_volume(self, last_price: str) -> Decimal:
        qty = self._parse_decimal(self._order_qty)
        price = self._parse_decimal(last_price)
        return qty * price * Decimal("2")

    def _estimate_required_usdt(self, last_price: str) -> Decimal:
        qty = self._parse_decimal(self._order_qty)
        price = self._parse_decimal(last_price)
        return qty * price

    def _get_available_usdt(self) -> Decimal:
        balance = self._exchange.get_available_balance(self._account_type, "USDT")
        if balance == "" or balance is None:
            self._log.warning("Баланс USDT не определён, считаю 0")
            return Decimal("0")
        return self._parse_decimal(balance)

    @staticmethod
    def _parse_decimal(value: str) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"Invalid decimal value: {value}") from exc

    @staticmethod
    def _extract_order_id(response: Dict[str, Any]) -> str:
        if "result" in response and isinstance(response["result"], dict):
            order_id = response["result"].get("orderId")
            if order_id:
                return str(order_id)
        if "orderId" in response:
            return str(response["orderId"])
        return ""

    def _wait_filled(self, symbol: str, order_id: str) -> Dict[str, Any] | None:
        attempts = 5
        for _ in range(attempts):
            status = self._exchange.get_order_status(symbol, order_id)
            state = str(status.get("orderStatus") or status.get("status", "")).upper()
            if state in ("FILLED", "PARTIALLY_FILLED"):
                return status
            if state in ("CANCELED", "REJECTED", "EXPIRED"):
                return None
            time.sleep(self._fill_delay_ms / 1000.0)
        return None

    def _extract_filled_volume(
        self,
        buy_status: Dict[str, Any],
        sell_status: Dict[str, Any],
        last_price: str,
    ) -> Decimal:
        buy_quote = self._parse_decimal(self._exchange.get_filled_quote(buy_status))
        sell_quote = self._parse_decimal(self._exchange.get_filled_quote(sell_status))
        if buy_quote > 0 and sell_quote > 0:
            return buy_quote + sell_quote
        return self._estimate_cycle_volume(last_price)
