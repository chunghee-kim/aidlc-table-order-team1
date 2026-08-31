from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Table(Base):
    __tablename__ = "table"
    __table_args__ = (UniqueConstraint("store_id", "table_number", name="uq_table_store_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("store.id"), index=True, nullable=False)
    table_number: Mapped[int] = mapped_column(Integer, nullable=False)
    table_password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    store = relationship("Store", back_populates="tables")
    sessions = relationship("TableSession", back_populates="table")
