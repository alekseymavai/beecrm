"""
OrderEvent — append-only лог переходов FSM.
UPDATE и DELETE запрещены на уровне сервиса (в будущем — PostgreSQL RULE).
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db import Base
from models.order import OrderStatus


class OrderEvent(Base):
    __tablename__ = "order_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    from_status: Mapped[OrderStatus | None] = mapped_column(
        String(32), nullable=True  # NULL = событие создания заказа
    )
    to_status: Mapped[OrderStatus] = mapped_column(String(32), nullable=False)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
