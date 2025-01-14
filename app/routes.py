from flask import render_template, abort
from flask_login import login_required
import sqlalchemy as sa
from app import app, db
from app.models import User

@app.route('/')
@app.route('/index')
@login_required
def index():
    return render_template('index.html')

@app.route('/user/<id>')
@login_required
def user(id):
    user = db.session.get(User, id)
    if user is None:
        abort(404)

    actions = [
        {'action': 'Post products', 'status': 'completed', 'admin': user},
        {'action': 'Generate report', 'status': 'completed', 'admin': user}
    ]

    return render_template('user.html', user=user, actions=actions)

@app.route('/settings')
@login_required
def user_settings():
    return 'building...'

@app.route('/captura')
@login_required
def captura():
    return render_template('captura.html', title='Captura')

@app.route('/etiquetas')
def etiquetas():
    return 'building...'

@app.route('/exportar-productos')
@login_required
def exportar_productos():
    return 'building...'