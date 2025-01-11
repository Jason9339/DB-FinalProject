from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
import logging
import os

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
migrate = Migrate()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ],
)

def create_app():
    app = Flask(__name__, static_folder="../static", template_folder="../templates")
    app.config.from_object(Config)

    # File upload configurations
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'images')
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Log the upload folder path for debugging
    app.logger.debug(f"Upload folder path: {app.config['UPLOAD_FOLDER']}")

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    app.logger.debug("Application initialized!")

    from .models import Movie  # 延遲導入，避免循環依賴
    from .routes import main, auth

    app.register_blueprint(main)
    app.register_blueprint(auth)

    with app.app_context():
        # Log some debug information about the app
        app.logger.debug(f"Static folder: {app.static_folder}")
        app.logger.debug(f"Template folder: {app.template_folder}")
        
        # Ensure all required directories exist
        static_dir = os.path.dirname(app.config['UPLOAD_FOLDER'])
        if not os.path.exists(static_dir):
            os.makedirs(static_dir)
            app.logger.debug(f"Created static directory: {static_dir}")
            
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
            app.logger.debug(f"Created upload directory: {app.config['UPLOAD_FOLDER']}")

    return app