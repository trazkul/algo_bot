import hashlib
import hmac
import logging
import time
from typing import Any, Dict
from urllib.parse import urlencode

import requests

from bot.exchanges.base import ExchangeBase
from bot.exchanges.registry import register_exchange


class BinanceFuturesClient(ExchangeBase):
    def __init__(self, api_key: str, api_secret: str, testnet: bool) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._testnet = testnet
        self._base_url = "https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"
        self._log = logging.getLogger(self.__class__.__name__)

    def is_testnet(self) -> bool:
        return self._testnet

    def place_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        order_type = payload.get("orderType", "Market")
        mapped = {
            "symbol": payload.get("symbol"),
            "side": str(payload.get("side", "")).upper(),
            "type": "MARKET" if str(order_type).lower() == "market" else str(order_type).upper(),
            "quantity": payload.get("qty"),
        }
        if payload.get("reduceOnly") is True:
            mapped["reduceOnly"] = "true"
        mapped["timestamp"] = int(time.time() * 1000)
        mapped["recvWindow"] = 5000
        return self._post("/fapi/v1/order", mapped)

    def get_last_price(self, symbol: str, category: str) -> str:
        data = self._get("/fapi/v1/ticker/price", {"symbol": symbol})
        price = data.get("price")
        if not price:
            raise ValueError("Missing price in Binance ticker response")
        return str(price)

    def get_available_balance(self, account_type: str, coin: str) -> str:
        data = self._get_signed("/fapi/v2/account", {})
        balances = data.get("assets", [])
        for item in balances:
            if item.get("asset") == coin:
                return str(item.get("availableBalance", "0"))
        return "0"

    def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        return self._get_signed(
            "/fapi/v1/order",
            {"symbol": symbol, "orderId": order_id},
        )

    def get_filled_quote(self, order_status: Dict[str, Any]) -> str:
        return str(order_status.get("cumQuote", "0"))

    def cancel_all_orders(self, symbol: str | None, category: str) -> Dict[str, Any]:
        if symbol:
            return self._delete_signed("/fapi/v1/allOpenOrders", {"symbol": symbol})

        open_orders = self._get_signed("/fapi/v1/openOrders", {})
        if not isinstance(open_orders, list):
            raise ValueError("Unexpected open orders response")
        symbols = sorted({item.get("symbol") for item in open_orders if item.get("symbol")})
        results = {}
        for item_symbol in symbols:
            results[item_symbol] = self._delete_signed(
                "/fapi/v1/allOpenOrders",
                {"symbol": item_symbol},
            )
        return {"symbols": symbols, "results": results}

    def list_open_orders(self, symbol: str | None, category: str) -> list:
        params: Dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol
        return self._get_signed("/fapi/v1/openOrders", params)

    def get_position_size(self, symbol: str, category: str) -> str:
        data = self._get_signed("/fapi/v2/positionRisk", {})
        if not isinstance(data, list):
            return "0"
        for item in data:
            if item.get("symbol") == symbol:
                return str(item.get("positionAmt", "0"))
        return "0"

    def close_position(self, symbol: str, category: str, size: str) -> Dict[str, Any]:
        side = "SELL" if str(size).startswith("-") is False else "BUY"
        qty = str(size).lstrip("-")
        payload = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": qty,
            "reduceOnly": "true",
            "timestamp": int(time.time() * 1000),
            "recvWindow": 5000,
        }
        return self._post("/fapi/v1/order", payload)

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        response = requests.get(url, params=params, timeout=10)
        return self._handle_response(response)

    def _post(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        signed = self._sign_params(params)
        headers = {"X-MBX-APIKEY": self._api_key}
        response = requests.post(url, headers=headers, params=signed, timeout=10)
        return self._handle_response(response)

    def _get_signed(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        signed = self._sign_params(params)
        headers = {"X-MBX-APIKEY": self._api_key}
        response = requests.get(url, headers=headers, params=signed, timeout=10)
        return self._handle_response(response)

    def _delete_signed(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        signed = self._sign_params(params)
        headers = {"X-MBX-APIKEY": self._api_key}
        response = requests.delete(url, headers=headers, params=signed, timeout=10)
        return self._handle_response(response)

    def _sign_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params = dict(params)
        if "timestamp" not in params:
            params["timestamp"] = int(time.time() * 1000)
        if "recvWindow" not in params:
            params["recvWindow"] = 5000
        query = urlencode(params, doseq=True)
        signature = hmac.new(self._api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
        params["signature"] = signature
        return params

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        if not response.ok:
            self._log.error(
                "Binance HTTP error: status=%s body=%s",
                response.status_code,
                response.text,
            )
            response.raise_for_status()
        try:
            data = response.json()
            if isinstance(data, dict) and data.get("code") not in (None, 0, "0"):
                self._log.error("Binance API error: code=%s msg=%s", data.get("code"), data.get("msg"))
            return data
        except ValueError:
            self._log.error("Binance response is not JSON: %s", response.text)
            return {}


def _factory(config):
    if not config.binance_api.key or not config.binance_api.secret:
        raise ValueError("Binance API key/secret are required")
    return BinanceFuturesClient(
        api_key=config.binance_api.key,
        api_secret=config.binance_api.secret,
        testnet=config.bot.testnet,
    )


register_exchange("binance", _factory)
