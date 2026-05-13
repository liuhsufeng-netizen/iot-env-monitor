from flask import Flask

from app.api.routes import api_bp
from app.config import CONFIG_MAP
from app.controllers.dashboard_controller import dashboard_bp
from app.extensions import db, socketio


def create_app(config_name: str = "development") -> Flask:
    app = Flask(__name__)
    app.config.from_object(CONFIG_MAP[config_name])

    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")

    app.register_blueprint(api_bp)
    app.register_blueprint(dashboard_bp)

    return app
