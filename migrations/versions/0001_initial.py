"""0001_initial — создание таблиц clients, orders, order_events

Revision ID: 0001
Revises:
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Единственный источник лимита — импортируется из settings
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from settings import MAX_PAYLOAD_BYTES


def upgrade() -> None:
    # ── clients ─────────────────────────────────────────────────────────────
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("phone", "email", name="uq_client_phone_email"),
    )
    op.create_index("ix_clients_phone", "clients", ["phone"])
    op.create_index("ix_clients_email", "clients", ["email"])

    # ── enum types ───────────────────────────────────────────────────────────
    ordersource = postgresql.ENUM("UDS", "MESSENGER", "TABLE", name="ordersource", create_type=True)
    orderstatus = postgresql.ENUM(
        "NEW", "CONFIRMED", "IN_PROGRESS", "DONE", "CANCELLED",
        name="orderstatus", create_type=True,
    )
    ordersource.create(op.get_bind(), checkfirst=True)
    orderstatus.create(op.get_bind(), checkfirst=True)

    # ── orders ───────────────────────────────────────────────────────────────
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("clients.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source", sa.Enum("UDS", "MESSENGER", "TABLE", name="ordersource"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("NEW", "CONFIRMED", "IN_PROGRESS", "DONE", "CANCELLED", name="orderstatus"),
            nullable=False,
            server_default="NEW",
        ),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Security: ограничиваем размер payload на уровне БД
        sa.CheckConstraint(
            f"octet_length(payload::text) <= {MAX_PAYLOAD_BYTES}",
            name="ck_orders_payload_size",
        ),
    )
    op.create_index("ix_orders_client_id", "orders", ["client_id"])

    # ── order_events (append-only) ───────────────────────────────────────────
    op.create_table(
        "order_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "order_id",
            sa.Integer(),
            sa.ForeignKey("orders.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("actor", sa.String(255), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_order_events_order_id", "order_events", ["order_id"])


def downgrade() -> None:
    op.drop_table("order_events")
    op.drop_index("ix_orders_client_id", "orders")
    op.drop_table("orders")

    bind = op.get_bind()
    postgresql.ENUM(name="orderstatus").drop(bind, checkfirst=True)
    postgresql.ENUM(name="ordersource").drop(bind, checkfirst=True)

    op.drop_index("ix_clients_email", "clients")
    op.drop_index("ix_clients_phone", "clients")
    op.drop_table("clients")
