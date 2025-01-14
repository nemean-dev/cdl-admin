import sqlalchemy as sa
import sqlalchemy.orm as orm
from app import app, db
from app.models import User, AdminAction

@app.shell_context_processor
def make_shell_context():
    return {'sa': sa, 'orm': orm, 'db': db, 'User': User, 'AdminAction': AdminAction}

#TODO remove h1 from base and change h2 in other templates to h1