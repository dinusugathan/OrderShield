import json
import os
from typing import Dict, Optional, List
from engine.models import OrderRecord

class OrderManagementSystem:
    """
    Mock Stateful Order Management System (OMS) & Logistics Store.
    Maintains real-time order lifecycle transitions (Processing -> Shipped -> Delivered -> Cancelled/Returned).
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.orders: Dict[str, OrderRecord] = {}
        self._load_orders()

    def _load_orders(self):
        with open(self.db_path, "r", encoding="utf-8") as f:
            raw_orders = json.load(f)
            for item in raw_orders:
                rec = OrderRecord(**item)
                self.orders[rec.order_id] = rec

    def get_order(self, order_id: str) -> Optional[OrderRecord]:
        return self.orders.get(order_id.upper().strip())

    def list_orders(self) -> List[OrderRecord]:
        return list(self.orders.values())

    def cancel_order(self, order_id: str) -> bool:
        order = self.get_order(order_id)
        if order and order.status == "PROCESSING":
            order.status = "CANCELLED"
            return True
        return False

    def update_shipping_address(self, order_id: str, new_address: Dict[str, str]) -> bool:
        order = self.get_order(order_id)
        if order and order.status == "PROCESSING":
            order.shipping_address.update(new_address)
            return True
        return False

    def authorize_rma(self, order_id: str, rma_code: str) -> bool:
        order = self.get_order(order_id)
        if order and order.status == "DELIVERED":
            order.return_status = f"RMA_AUTHORIZED ({rma_code})"
            return True
        return False

    def reset_db(self):
        self._load_orders()
