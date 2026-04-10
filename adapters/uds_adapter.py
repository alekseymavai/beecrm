"""UDSAdapter — нормализация заказов из UDS (usadbadmitrov.uds.app)."""

from adapters.base import BaseAdapter


class UDSAdapter(BaseAdapter):
    def _extract(self, raw: dict) -> dict:
        return {
            "uds_order_id":   raw.get("uds_order_id") or raw.get("id") or raw.get("orderId"),
            "state":          raw.get("state", ""),
            "customer_name":  raw.get("customer_name", ""),
            "customer_phone": raw.get("customer_phone", ""),
            "total":          raw.get("total") or raw.get("totalPrice", 0),
            "delivery_cost":  raw.get("delivery_cost", 0),
            "items_total":    raw.get("items_total", 0),
            "delivery_name":  raw.get("delivery_name", ""),
            "address":        raw.get("address") or raw.get("deliveryAddress", ""),
            "comment":        raw.get("comment") or raw.get("customerComment", ""),
            "items":          raw.get("items", []),
            "paid":           raw.get("paid", False),
        }
