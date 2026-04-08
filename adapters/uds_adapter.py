"""UDSAdapter — нормализация заказов из UDS (usadbadmitrov.uds.app)."""

from adapters.base import BaseAdapter


class UDSAdapter(BaseAdapter):
    def _extract(self, raw: dict) -> dict:
        return {
            "uds_order_id": raw.get("id") or raw.get("orderId"),
            "items": raw.get("items", []),
            "total": raw.get("total") or raw.get("totalPrice"),
            "comment": raw.get("comment") or raw.get("customerComment"),
            "address": raw.get("deliveryAddress") or raw.get("address"),
            "paid": raw.get("paid", False),
        }
