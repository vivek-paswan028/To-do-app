from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(60), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    todos: Mapped[list["Todo"]] = relationship(
        "Todo", back_populates="category", cascade="all, delete", lazy="selectin"
    )


class Todo(db.Model):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(db.String(160), nullable=False, index=True)
    description: Mapped[str] = mapped_column(db.Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(db.String(20), default="todo", nullable=False, index=True)
    priority: Mapped[str] = mapped_column(
        db.String(20), default="medium", nullable=False, index=True
    )
    due_date: Mapped[date | None] = mapped_column(db.Date, nullable=True, index=True)
    is_pinned: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)

    category_id: Mapped[int | None] = mapped_column(db.ForeignKey("categories.id"), nullable=True)
    category: Mapped[Category | None] = relationship("Category", back_populates="todos")

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_todos_status_priority", "status", "priority"),
        Index("ix_todos_pinned_created", "is_pinned", "created_at"),
    )

    @property
    def is_overdue(self) -> bool:
        return self.due_date is not None and self.due_date < date.today() and self.status != "done"
