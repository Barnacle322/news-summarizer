import os
from datetime import timedelta

from flask import Flask
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from .extensions import db
from .routes import api
from .utils.scheduler import setup_scheduler


def create_app(database_url="sqlite:///db.sqlite"):
    app = Flask(__name__)

    # Enable CORS for all routes
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("_DATABASE_URL", database_url)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_POOL_SIZE"] = int(os.getenv("SQLALCHEMY_POOL_SIZE", 5))
    app.config["SQLALCHEMY_POOL_RECYCLE"] = int(os.getenv("SQLALCHEMY_POOL_RECYCLE", 1800))
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)
    app.secret_key = os.getenv("SECRET_KEY", "18c2ff95-83a1-4998-8bee-0c6a2170497c")

    if os.getenv("FLASK_ENV") == "testing":
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test_db.sqlite"

    if app.config["DEBUG"] and not app.config["TESTING"]:
        app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False
        app.config["SQLALCHEMY_RECORD_QUERIES"] = True
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
        # app.config["SQLALCHEMY_ECHO"] = True
        # app.config["DEBUG_TB_PROFILER_ENABLED"] = True
        # toolbar.init_app(app)

    else:
        # Reverse proxy support
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    app.register_blueprint(api)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    if not app.config.get("TESTING"):
        setup_scheduler(app)

    return app


application = create_app()
