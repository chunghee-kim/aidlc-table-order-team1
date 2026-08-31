"""U6 test support — fresh shared-in-memory SQLite DB + row factories.

Each PBT example calls `new_memory_db()` to get full isolation (Hypothesis does not reset
function-scoped fixtures between examples), pointing app.db.SessionLocal at the fresh DB.
"""
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers all models on Base.metadata)
from app import db as appdb
from app.db import Base
from app.models import Order, OrderItem, Store, Table


def new_memory_db():
    """Create a fresh in-memory DB (single shared connection) and rebind app.db.SessionLocal."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    appdb.engine = engine
    appdb.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return engine


def seed_store(store_id: int = 1):
    db = appdb.SessionLocal()
    try:
        db.add(Store(id=store_id, store_code=f"S{store_id}", name=f"store{store_id}"))
        db.commit()
    finally:
        db.close()


def seed_table(table_id: int, store_id: int = 1, table_number: int | None = None):
    db = appdb.SessionLocal()
    try:
        db.add(
            Table(
                id=table_id,
                store_id=store_id,
                table_number=table_number if table_number is not None else table_id,
                table_password_hash="x",
                is_active=True,
            )
        )
        db.commit()
    finally:
        db.close()


def add_order(session_id: int, table_id: int, order_number: str, items, created_at=None) -> int:
    """items: list[(unit_price, quantity)]. Persists an Order + OrderItems; returns the order total."""
    total = sum(price * qty for price, qty in items)
    db = appdb.SessionLocal()
    try:
        order = Order(
            session_id=session_id,
            table_id=table_id,
            order_number=order_number,
            status="대기중",
            total_amount=total,
            created_at=created_at or datetime.utcnow(),
        )
        order.items = [
            OrderItem(menu_id=1, menu_name="m", unit_price=price, quantity=qty) for price, qty in items
        ]
        db.add(order)
        db.commit()
    finally:
        db.close()
    return total
