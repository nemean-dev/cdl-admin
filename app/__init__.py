from flask import Flask
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

from app.auth import bp as auth_bp
app.register_blueprint(auth_bp)

from app import routes