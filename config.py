from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _database_uri() -> str:
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Some platforms still provide postgres://, but SQLAlchemy expects postgresql://
        if db_url.startswith("postgres://"):
            return db_url.replace("postgres://", "postgresql://", 1)
        return db_url

    if os.getenv("VERCEL"):
        # Vercel filesystem is read-only except /tmp
        return "sqlite:////tmp/todo_advanced.db"

    instance_dir = BASE_DIR / "instance"
    instance_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{instance_dir / 'todo_advanced.db'}"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
