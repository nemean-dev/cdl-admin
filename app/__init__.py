import os
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from config import Config
from app.integrations.storage import StorageService

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Necesitas inciar sesión para acceder a esta página'
mail = Mail()

def storage_service() -> StorageService:
    '''
    Use this to manage storage throughout the app, given that storage will be s3 
    or some other service in deployment and local in development.

    e.g.
    ```
    from app import get_storage

    storage = get_storage()
    storage.upload_json('path/to/file.json', {'key': 'value'})
    ```
    '''
    return StorageService()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)

    # blueprints
    from app.cli import bp as cli_bp
    app.register_blueprint(cli_bp)
    from app.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp)
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)
    from app.shop import bp as shop_bp
    app.register_blueprint(shop_bp)
    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    data_dir = app.config['DATA_DIR']
    os.makedirs(data_dir, exist_ok=True)

    # logging and error emailing
    if not app.debug and not app.testing:
        if app.config['MAIL_SERVER']:
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr='no-reply@' + app.config['MAIL_SERVER'],
                toaddrs=app.config['ADMINS'], 
                subject=f'CDL Dashboard Failure ({app.config['SHOPIFY_STORE'] or 'no store name'})',
                credentials=auth, secure=secure)
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)

        if app.config['LOG_TO_STDOUT']:
            stream_handler = logging.StreamHandler()
            app.logger.addHandler(stream_handler)
        else:
            logs_dir = app.config['LOGS_DIR']
            os.makedirs(logs_dir, exist_ok=True)
            file_handler = RotatingFileHandler(os.path.join(logs_dir, 'cdl-admin.log'),
                                            maxBytes=10240,
                                            backupCount=10)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
            app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info(
            '\n\n----------------------------------- CDL Dashboard Startup -----------------------------------\n\n'
           f' - Store: {app.config["SHOPIFY_STORE"]}\n\n')
    else: 
        app.logger.info(
            '\n\n----------------------------------- CDL Dashboard Startup -----------------------------------\n\n'
           f' - Store: {app.config["SHOPIFY_STORE"]}\n'
            ' - Logging not configured\n'
            ' - Emails on server errors not configured\n')

    
    return app

from app import models