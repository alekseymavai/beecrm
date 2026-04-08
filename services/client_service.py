"""client_service.py — дедупликация клиентов.

find_or_create() — fragile zone HIGH:
  UDS и мессенджер могут быть одним клиентом.
  Поиск: сначала по phone, потом по email.
  Если нашли — обновляем недостающие поля, не создаём дубль.
"""

from sqlalchemy.orm import Session

from models.client import Client


def find_or_create(
    db: Session,
    phone: str | None = None,
    email: str | None = None,
    name: str | None = None,
) -> tuple[Client, bool]:
    """Найти клиента по phone или email, иначе создать.

    Returns:
        (client, created) — created=True если новый клиент
    """
    if not phone and not email:
        raise ValueError("Нужен хотя бы phone или email")

    client = None

    # Ищем по phone (приоритет — phone уникальнее email)
    if phone:
        client = db.query(Client).filter(Client.phone == phone).first()

    # Ищем по email если по phone не нашли
    if not client and email:
        client = db.query(Client).filter(Client.email == email).first()

    if client:
        # Дополняем недостающие поля
        if phone and not client.phone:
            client.phone = phone
        if email and not client.email:
            client.email = email
        if name and not client.name:
            client.name = name
        return client, False

    # Создаём нового
    client = Client(phone=phone, email=email, name=name)
    db.add(client)
    db.flush()
    return client, True


def get_history(db: Session, client_id: int) -> list:
    """История заказов клиента."""
    from models.order import Order
    return (
        db.query(Order)
        .filter(Order.client_id == client_id)
        .order_by(Order.created_at.desc())
        .all()
    )
