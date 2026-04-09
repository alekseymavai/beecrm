"""client_service.py — дедупликация клиентов.

find_or_create() — fragile zone HIGH:
  UDS и мессенджер могут быть одним клиентом.
  Поиск: сначала по phone, потом по email.
  Если нашли — обновляем недостающие поля, не создаём дубль.
"""

from integram.client import IntegramClient
from integram.mappers import igm_to_client


async def find_or_create(
    igm: IntegramClient,
    phone: str | None = None,
    email: str | None = None,
    name: str | None = None,
) -> tuple[dict, bool]:
    """Найти клиента по phone или email, иначе создать.

    Returns:
        (client_dict, created) — created=True если новый клиент. client_dict — mapped dict.
    """
    if not phone and not email:
        raise ValueError("Нужен хотя бы phone или email")

    raw = None

    if phone:
        raw = await igm.find_by_field(igm.T_CLIENTS, igm.COL_CLIENT_PHONE, phone)

    if not raw and email:
        raw = await igm.find_by_field(igm.T_CLIENTS, igm.COL_CLIENT_EMAIL, email)

    if raw:
        req = raw.get("requisites") or {}
        new_req: dict = {}
        new_value: str | None = None

        if phone and not req.get(str(igm.COL_CLIENT_PHONE)):
            new_req[str(igm.COL_CLIENT_PHONE)] = phone
        if email and not req.get(str(igm.COL_CLIENT_EMAIL)):
            new_req[str(igm.COL_CLIENT_EMAIL)] = email
        if name and not raw.get("value"):
            new_value = name

        if new_req or new_value is not None:
            raw = await igm.update_object(
                raw["id"],
                value=new_value,
                requisites=new_req or None,
            )
        return igm_to_client(raw), False

    requisites: dict = {}
    if phone:
        requisites[str(igm.COL_CLIENT_PHONE)] = phone
    if email:
        requisites[str(igm.COL_CLIENT_EMAIL)] = email
    raw = await igm.create_object(igm.T_CLIENTS, value=name or "", requisites=requisites)
    return igm_to_client(raw), True


async def get_history(igm: IntegramClient, client_id: int) -> list[dict]:
    """История заказов клиента — серверная фильтрация по client_id."""
    return await igm.list_orders_by_client(client_id)
