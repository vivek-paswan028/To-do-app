from __future__ import annotations

from flask import Flask
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from config import Config

from .extensions import db, login_manager


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "error"
    login_manager.login_message = "Please log in to access your workspace."

    from .auth.routes import auth_bp
    from .todos.routes import todos_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(todos_bp)

    from .models import User

    def apply_runtime_schema_patches() -> None:
        inspector = inspect(db.engine)
        table_names = set(inspector.get_table_names())

        if "todos" in table_names:
            todo_cols = {col["name"] for col in inspector.get_columns("todos")}
            if "user_id" not in todo_cols:
                db.session.execute(text("ALTER TABLE todos ADD COLUMN user_id INTEGER"))

        if "categories" in table_names:
            category_cols = {col["name"] for col in inspector.get_columns("categories")}
            if "user_id" not in category_cols:
                db.session.execute(text("ALTER TABLE categories ADD COLUMN user_id INTEGER"))

        db.session.commit()

    @app.before_request
    def ensure_schema() -> None:
        if app.config.get("_SCHEMA_READY"):
            return
        try:
            db.create_all()
            apply_runtime_schema_patches()
            app.config["_SCHEMA_READY"] = True
        except SQLAlchemyError:
            # Keep import/runtime alive on serverless and surface DB issues per request.
            app.logger.exception("Database schema initialization failed.")

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return db.session.get(User, int(user_id))

    return app
