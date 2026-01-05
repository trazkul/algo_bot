from abc import ABC, abstractmethod
from typing import Any, Dict


class ExchangeBase(ABC):
    @abstractmethod
    def place_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def is_testnet(self) -> bool:
        pass

    @abstractmethod
    def get_last_price(self, symbol: str, category: str) -> str:
        pass

    @abstractmethod
    def get_available_balance(self, account_type: str, coin: str) -> str:
        pass

    @abstractmethod
    def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_filled_quote(self, order_status: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    def cancel_all_orders(self, symbol: str | None, category: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def list_open_orders(self, symbol: str | None, category: str) -> Dict[str, Any] | list:
        pass

    @abstractmethod
    def get_position_size(self, symbol: str, category: str) -> str:
        pass

    @abstractmethod
    def close_position(self, symbol: str, category: str, size: str) -> Dict[str, Any]:
        pass
