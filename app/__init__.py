from __future__ import annotations

from flask import Flask

from config import Config

from .extensions import db


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    db.init_app(app)

    from .todos.routes import todos_bp

    app.register_blueprint(todos_bp)

    with app.app_context():
        from . import models

        db.create_all()

    return app
