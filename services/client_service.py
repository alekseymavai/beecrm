"""client_service.py — дедупликация клиентов.

find_or_create() — fragile zone HIGH:
  UDS и мессенджер могут быть одним клиентом.
  Поиск: сначала по phone, потом по email.
  Если нашли — обновляем недостающие поля, не создаём дубль.
"""

from integram.client import IntegramClient


async def find_or_create(
    igm: IntegramClient,
    phone: str | None = None,
    email: str | None = None,
    name: str | None = None,
) -> tuple[dict, bool]:
    """Найти клиента по phone или email, иначе создать.

    Returns:
        (client_dict, created) — created=True если новый клиент
    """
    if not phone and not email:
        raise ValueError("Нужен хотя бы phone или email")

    client = None

    if phone:
        client = await igm.find_by_field(igm.T_CLIENTS, igm.COL_CLIENT_PHONE, phone)

    if not client and email:
        client = await igm.find_by_field(igm.T_CLIENTS, igm.COL_CLIENT_EMAIL, email)

    if client:
        updates: dict = {}
        if phone and not client.get("phone"):
            updates["phone"] = phone
        if email and not client.get("email"):
            updates["email"] = email
        if name and not client.get("name"):
            updates["name"] = name
        if updates:
            client = await igm.update_object(igm.T_CLIENTS, client["id"], updates)
        return client, False

    fields: dict = {}
    if phone:
        fields["phone"] = phone
    if email:
        fields["email"] = email
    if name:
        fields["name"] = name
    client = await igm.create_object(igm.T_CLIENTS, fields)
    return client, True


async def get_history(igm: IntegramClient, client_id: int) -> list[dict]:
    """История заказов клиента."""
    orders = await igm.list_objects(igm.T_ORDERS, limit=100)
    result = []
    for order in orders:
        ref = order.get("client")
        cid = ref["id"] if isinstance(ref, dict) else ref
        if cid == client_id:
            result.append(order)
    return result
