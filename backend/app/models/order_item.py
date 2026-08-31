from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class OrderItem(Base):
    __tablename__ = "order_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("order.id"), index=True, nullable=False)
    menu_id: Mapped[int] = mapped_column(ForeignKey("menu.id"), nullable=False)
    menu_name: Mapped[str] = mapped_column(String(100), nullable=False)  # snapshot
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)  # snapshot
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # >= 1

    order = relationship("Order", back_populates="items")
