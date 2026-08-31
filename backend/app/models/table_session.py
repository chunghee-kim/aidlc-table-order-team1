from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TableSession(Base):
    """A table's usage session. Invariant (U6, PBT): at most one status='active' per table."""

    __tablename__ = "table_session"
    __table_args__ = (Index("ix_session_table_status", "table_id", "status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("table.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="active", nullable=False)  # active | closed
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    table = relationship("Table", back_populates="sessions")
    orders = relationship("Order", back_populates="session")
