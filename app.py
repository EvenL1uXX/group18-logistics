"""Flask application entry point for the Group 18 Logistics Management System.

Run with:  python app.py
or:        flask --app app run
"""

import os

from flask import Flask, g, redirect, url_for, session

from config import Config
from data.db import Database


def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder="presentation/templates",
        static_folder="presentation/static",
    )
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    # make sure instance/ exists before SQLite tries to create the file
    db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if db_uri.startswith("sqlite:///"):
        db_path = db_uri.replace("sqlite:///", "", 1)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    app.config["DB"] = Database(db_uri)
    app.config["DB"].init_schema()

    # import here to avoid circular imports
    from presentation.auth import auth_bp
    from presentation.orders import orders_bp
    from presentation.inventory import inventory_bp
    from presentation.shipments import shipments_bp
    from presentation.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(shipments_bp)
    app.register_blueprint(reports_bp)

    @app.before_request
    def open_session() -> None:
        g.db = app.config["DB"].session()

    @app.teardown_request
    def close_session(exc=None) -> None:
        app.config["DB"].remove()

    @app.route("/")
    def index():
        role = session.get("role")
        if role == "Admin":
            return redirect(url_for("orders.list_orders"))
        if role == "Driver":
            return redirect(url_for("shipments.list_shipments"))
        return redirect(url_for("orders.list_orders"))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
