import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from bot.exchanges.base import ExchangeBase
from bot.exchanges.registry import register_exchange


class BybitClient(ExchangeBase):
    def __init__(self, api_key: str, api_secret: str, testnet: bool, recv_window: int) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._testnet = testnet
        self._recv_window = recv_window
        self._base_url = "https://api-testnet.bybit.com" if testnet else "https://api.bybit.com"
        self._log = logging.getLogger(self.__class__.__name__)

    def is_testnet(self) -> bool:
        return self._testnet

    def place_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/v5/order/create", payload)

    def get_last_price(self, symbol: str, category: str) -> str:
        data = self._get("/v5/market/tickers", {"category": category, "symbol": symbol})
        items = data.get("result", {}).get("list", [])
        if not items:
            raise ValueError("Empty ticker response")
        last_price = items[0].get("lastPrice")
        if not last_price:
            raise ValueError("Missing lastPrice in ticker response")
        return str(last_price)

    def get_available_balance(self, account_type: str, coin: str) -> str:
        data = self._get_private(
            "/v5/account/wallet-balance",
            {"accountType": account_type, "coin": coin},
        )
        balances = data.get("result", {}).get("list", [])
        if not balances:
            raise ValueError("Empty wallet balance response")
        coins = balances[0].get("coin", [])
        for item in coins:
            if item.get("coin") == coin:
                value = item.get("availableToWithdraw")
                if value not in (None, ""):
                    return str(value)
                wallet_value = item.get("walletBalance")
                if wallet_value not in (None, ""):
                    return str(wallet_value)
                equity_value = item.get("equity")
                if equity_value not in (None, ""):
                    return str(equity_value)
                return "0"
        raise ValueError(f"Balance not found for coin: {coin}")

    def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        data = self._get_private(
            "/v5/order/realtime",
            {"category": "linear", "symbol": symbol, "orderId": order_id},
        )
        items = data.get("result", {}).get("list", [])
        if not items:
            raise ValueError("Empty order status response")
        return items[0]

    def get_filled_quote(self, order_status: Dict[str, Any]) -> str:
        return str(order_status.get("cumExecValue", "0"))

    def cancel_all_orders(self, symbol: str | None, category: str) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"category": category}
        if symbol:
            payload["symbol"] = symbol
        return self._post("/v5/order/cancel-all", payload)

    def list_open_orders(self, symbol: str | None, category: str) -> Dict[str, Any]:
        params: Dict[str, Any] = {"category": category}
        if symbol:
            params["symbol"] = symbol
        return self._get_private("/v5/order/realtime", params)

    def get_position_size(self, symbol: str, category: str) -> str:
        data = self._get_private(
            "/v5/position/list",
            {"category": category, "symbol": symbol},
        )
        items = data.get("result", {}).get("list", [])
        if not items:
            return "0"
        size = items[0].get("size", "0")
        return str(size)

    def close_position(self, symbol: str, category: str, size: str) -> Dict[str, Any]:
        return self._post(
            "/v5/order/create",
            {
                "category": category,
                "symbol": symbol,
                "side": "Sell",
                "orderType": "Market",
                "qty": size,
                "reduceOnly": True,
            },
        )

    def get_wallet_balances(self, account_type: str) -> Dict[str, Any]:
        return self._get_private(
            "/v5/account/wallet-balance",
            {"accountType": account_type},
        )

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        timestamp = str(int(time.time() * 1000))
        body = json.dumps(payload, separators=(",", ":"))
        signature = self._sign(timestamp, body)

        headers = self._headers(signature, timestamp)

        response = requests.post(url, headers=headers, data=body, timeout=10)
        return self._handle_response(response)

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        response = requests.get(url, params=params, timeout=10)
        return self._handle_response(response)

    def _get_private(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        timestamp = str(int(time.time() * 1000))
        query = urlencode(params)
        signature = self._sign(timestamp, query)
        headers = self._headers(signature, timestamp)

        response = requests.get(url, headers=headers, params=params, timeout=10)
        return self._handle_response(response)

    def _headers(self, signature: str, timestamp: str) -> Dict[str, str]:
        return {
            "X-BAPI-API-KEY": self._api_key,
            "X-BAPI-SIGN": signature,
            "X-BAPI-SIGN-TYPE": "2",
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": str(self._recv_window),
            "Content-Type": "application/json",
        }

    def _sign(self, timestamp: str, body: str) -> str:
        payload = f"{timestamp}{self._api_key}{self._recv_window}{body}"
        return hmac.new(
            self._api_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        if not response.ok:
            self._log.error(
                "Bybit HTTP error: status=%s body=%s",
                response.status_code,
                response.text,
            )
            response.raise_for_status()

        data = self._safe_json(response)
        ret_code = data.get("retCode")
        ret_msg = data.get("retMsg")
        if ret_code not in (0, "0", None) and ret_msg:
            self._log.error("Bybit API error: retCode=%s retMsg=%s", ret_code, ret_msg)
        return data

    def _safe_json(self, response: requests.Response) -> Dict[str, Any]:
        try:
            return response.json()
        except ValueError:
            self._log.error("Bybit response is not JSON: %s", response.text)
            return {}


def _factory(config):
    if not config.api.key or not config.api.secret:
        raise ValueError("API key/secret are required")
    return BybitClient(
        api_key=config.api.key,
        api_secret=config.api.secret,
        testnet=config.bot.testnet,
        recv_window=config.bot.recv_window,
    )


register_exchange("bybit", _factory)
