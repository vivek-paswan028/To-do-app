from __future__ import annotations

from flask import Flask
from sqlalchemy.exc import SQLAlchemyError

from config import Config

from .extensions import db


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    db.init_app(app)

    from .todos.routes import todos_bp

    app.register_blueprint(todos_bp)

    from . import models

    @app.before_request
    def ensure_schema() -> None:
        if app.config.get("_SCHEMA_READY"):
            return
        try:
            db.create_all()
            app.config["_SCHEMA_READY"] = True
        except SQLAlchemyError:
            # Keep import/runtime alive on serverless and surface DB issues per request.
            app.logger.exception("Database schema initialization failed.")

    return app
