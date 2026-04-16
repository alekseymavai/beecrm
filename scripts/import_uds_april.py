#!/usr/bin/env python3
"""import_uds_april.py — импорт заказов из UDS за апрель в BEECRMTEST."""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Добавляем проект в PATH
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from integram.client import IntegramClient


# ============================================================================
# UDS Admin Client (для goods-orders с полной информацией)
# ============================================================================

class UDSAdminClient:
    """UDS Admin API клиент — получение заказов магазина с полной информацией."""

    BASE_URL = "https://api.uds.app/admin"

    def __init__(self, token: str, company_id: str):
        self.token = token
        self.company_id = company_id
        self.client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            },
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *_):
        if self.client:
            await self.client.aclose()

    async def get_orders_page(self, offset: int = 0, limit: int = 50) -> dict:
        """Получить страницу заказов из goods-orders."""
        if not self.client:
            raise RuntimeError("Client not initialized")

        resp = await self.client.get(
            f"/companies/{self.company_id}/goods-orders",
            params={"max": limit, "offset": offset}
        )
        resp.raise_for_status()
        return resp.json()

    async def get_order_detail(self, order_id: int) -> dict:
        """Получить полные детали заказа."""
        if not self.client:
            raise RuntimeError("Client not initialized")

        resp = await self.client.get(
            f"/companies/{self.company_id}/goods-orders/{order_id}"
        )
        resp.raise_for_status()
        return resp.json()

    async def get_orders_since(self, since: datetime, page_size: int = 50) -> list[dict]:
        """Получить все заказы начиная с даты since."""
        orders: list[dict] = []
        offset = 0
        since_str = since.strftime("%Y-%m-%d")

        while True:
            page = await self.get_orders_page(offset=offset, limit=page_size)
            rows = page if isinstance(page, list) else page.get("rows", page.get("items", []))

            if not rows:
                break

            hit_old = False
            for row in rows:
                # Проверяем дату — обычно в formattedDate
                date_str = row.get("formattedDate", row.get("dateCreated", ""))[:10]
                if date_str < since_str:
                    hit_old = True
                    break
                orders.append(row)

            if hit_old or len(rows) < page_size:
                break

            offset += page_size
            await asyncio.sleep(1)  # Rate limit

        return orders


# ============================================================================
# Mapper: UDS Transaction → BEECRM Order
# ============================================================================

def parse_order_detail(detail: dict) -> dict:
    """Извлечь нужные поля из детального ответа UDS goods-orders."""
    customer = detail.get("customer") or {}
    delivery = detail.get("deliveryData") or {}
    purchase = detail.get("purchase") or {}

    # Дата
    created_at = detail.get("dateCreated", "")
    if not created_at:
        created_at = datetime.now(timezone.utc).isoformat()

    # Контакты клиента
    customer_name = delivery.get("receiverName") or customer.get("displayName") or "Неизвестный клиент"
    customer_phone = delivery.get("receiverPhone") or customer.get("phone") or ""
    customer_email = customer.get("email") or ""

    # Сумма заказа
    amount = float(purchase.get("total") or 0)

    # Комментарий — адрес доставки
    address = delivery.get("address") or ""
    user_comment = delivery.get("userComment") or ""
    comment = f"Адрес: {address}" if address else user_comment

    return {
        "uds_id": detail.get("id", ""),
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "customer_email": customer_email,
        "amount": amount,
        "comment": comment,
        "created_at": created_at,
    }


# ============================================================================
# Integram Integration
# ============================================================================

async def find_or_create_client(
    igm: IntegramClient,
    phone: str,
    email: str,
    name: str,
    notes: str = "",
) -> int:
    """Создать нового клиента в BEECRMTEST (typeId=16)."""

    # Всегда создаём нового клиента (для чистого теста без дедупликации)
    # TODO: в продакшене использовать find_by_field для поиска существующих
    requisites = {
        "22": notes if notes else f"Имя: {name}",  # notes
        "23": phone,  # phone
        "24": email,  # email
    }

    resp = await igm.create_object(
        typeId=16,
        requisites=requisites,
    )
    return resp["id"]


async def create_order(
    igm: IntegramClient,
    client_id: int,
    order_data: dict,
) -> int:
    """Создать заказ в BEECRMTEST (typeId=20)."""

    requisites = {
        "38": order_data["amount"],  # amount
        "39": f"UDS ID: {order_data['uds_id']}\n{order_data['comment']}",  # notes
        "40": order_data["created_at"],  # created_at
        "46": client_id,  # client (ref→Клиенты)
        "47": 48,  # status → "Новый" (id=48)
    }

    resp = await igm.create_object(
        typeId=20,
        requisites=requisites,
    )
    return resp["id"]


# ============================================================================
# Main
# ============================================================================

async def main():
    """Импортировать заказы из UDS goods-orders за апрель в BEECRMTEST."""

    # UDS Admin Token (из BEEBOT)
    uds_admin_token = "MTM3NDM4OTk1MDM1MjowZDBjZDFhNi0wM2RkLTQ5NDUtOTQ3NS00MDFkYzEyMTc4Y2M6"
    uds_company_id = "549756192009"

    # Integram для BEECRMTEST
    igm = IntegramClient(
        login="alekseymavai@gmail.com",
        password="alekseymavai",
        workspace="beecrmtest",
    )

    # Даты за апрель 2026
    since = datetime(2026, 4, 1, tzinfo=timezone.utc)

    print(f"📥 Получаю заказы из UDS goods-orders за апрель 2026...")

    async with UDSAdminClient(uds_admin_token, uds_company_id) as uds:
        # Получаем список заказов за период
        order_summaries = await uds.get_orders_since(since)
        print(f"✅ Получено {len(order_summaries)} заказов из UDS")

        if not order_summaries:
            print("⚠️  Нет заказов за апрель")
            return

        # Импортируем в BEECRMTEST
        created_count = 0
        errors = []

        for i, summary in enumerate(order_summaries, 1):
            try:
                order_id = summary.get("id")

                # Получаем полные детали заказа
                detail = await uds.get_order_detail(order_id)
                order_data = parse_order_detail(detail)


                # Находим или создаём клиента
                client_id = await find_or_create_client(
                    igm,
                    phone=order_data["customer_phone"],
                    email=order_data["customer_email"],
                    name=order_data["customer_name"],
                    notes=f"Источник: UDS",
                )

                # Создаём заказ
                crm_order_id = await create_order(igm, client_id, order_data)
                created_count += 1

                print(f"  [{i}/{len(order_summaries)}] ✅ Заказ {crm_order_id} (UDS #{order_id}, сумма {order_data['amount']}₽)")

            except Exception as e:
                error_msg = f"Заказ {i} (UDS #{order_id}): {str(e)}"
                errors.append(error_msg)
                print(f"  [{i}/{len(order_summaries)}] ❌ {error_msg}")

        # Итоговый отчёт
        print(f"\n{'='*60}")
        print(f"📊 Итог импорта:")
        print(f"  • Всего заказов: {len(order_summaries)}")
        print(f"  • Успешно создано: {created_count}")
        print(f"  • Ошибок: {len(errors)}")

        if errors:
            print(f"\n⚠️  Ошибки:")
            for error in errors:
                print(f"  • {error}")

        print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
