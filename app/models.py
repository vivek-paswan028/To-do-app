from __future__ import annotations

from datetime import date, datetime

from flask_login import UserMixin
from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(db.String(50), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(db.String(120), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(db.String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    todos: Mapped[list["Todo"]] = relationship("Todo", back_populates="owner", lazy="selectin")
    categories: Mapped[list["Category"]] = relationship(
        "Category", back_populates="owner", lazy="selectin"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(60), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    user_id: Mapped[int | None] = mapped_column(db.ForeignKey("users.id"), nullable=True, index=True)

    todos: Mapped[list["Todo"]] = relationship(
        "Todo", back_populates="category", cascade="all, delete", lazy="selectin"
    )
    owner: Mapped[User | None] = relationship("User", back_populates="categories")


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
    user_id: Mapped[int | None] = mapped_column(db.ForeignKey("users.id"), nullable=True, index=True)

    category_id: Mapped[int | None] = mapped_column(db.ForeignKey("categories.id"), nullable=True)
    category: Mapped[Category | None] = relationship("Category", back_populates="todos")
    owner: Mapped[User | None] = relationship("User", back_populates="todos")

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
