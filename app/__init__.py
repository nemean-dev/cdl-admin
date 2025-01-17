from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'auth.login'
login.login_message = 'Necesitas inciar sesión para acceder a esta página'

from app.auth import bp as auth_bp
app.register_blueprint(auth_bp)

from app.shop import bp as shop_bp
app.register_blueprint(shop_bp)

from app import routes, models