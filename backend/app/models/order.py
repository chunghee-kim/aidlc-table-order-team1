from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Order(Base):
    __tablename__ = "order"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("table_session.id"), index=True, nullable=False)
    table_id: Mapped[int] = mapped_column(ForeignKey("table.id"), index=True, nullable=False)
    order_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # YYYYMMDD-###
    status: Mapped[str] = mapped_column(String(10), default="대기중", nullable=False)  # 대기중|준비중|완료
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False)  # = Σ(unit_price × quantity)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("TableSession", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
