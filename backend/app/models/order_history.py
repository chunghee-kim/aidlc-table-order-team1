from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class OrderHistory(Base):
    """Snapshot of a closed session's order (U6). Self-contained; not FK-enforced."""

    __tablename__ = "order_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    session_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    order_number: Mapped[str] = mapped_column(String(20), nullable=False)
    # [{"menu_name": str, "unit_price": int, "quantity": int}]
    items_snapshot: Mapped[list] = mapped_column(JSON, nullable=False)
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    ordered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
