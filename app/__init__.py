# __init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
import os
import logging

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
migrate = Migrate()

logging.basicConfig(
    level=logging.DEBUG,  # 設定最低記錄級別為 DEBUG
    format="%(asctime)s - %(levelname)s - %(message)s",  # 設定訊息格式
    handlers=[
        logging.StreamHandler()
    ],  # 默認輸出到控制台，也可以添加其他 handler（例如寫入檔案）
)

logging.basicConfig(
    level=logging.DEBUG,  # 設定最低記錄級別為 DEBUG
    format="%(asctime)s - %(levelname)s - %(message)s",  # 設定訊息格式
    handlers=[
        logging.StreamHandler()
    ],  # 默認輸出到控制台，也可以添加其他 handler（例如寫入檔案）
)


def create_app():
    app = Flask(__name__, static_folder="../static", template_folder="../templates")
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    app.logger.debug("TEST!!!")
    from .models import Movie  # 延遲導入，避免循環依賴

    from .routes import main, auth

    app.register_blueprint(main)
    app.register_blueprint(auth)

    return app
