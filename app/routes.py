from datetime import datetime, timezone
from flask import render_template, abort, flash, redirect, url_for, request
from flask_login import login_required, current_user
import sqlalchemy as sa
from app import app, db
from app.models import User
from app.forms import UserSettingsForm

@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()

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
    ] #TODO

    return render_template('user.html', user=user, actions=actions)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def user_settings():
    form = UserSettingsForm()

    if form.validate_on_submit():
        current_user.fname = form.fname.data
        current_user.lname = form.lname.data
        db.session.commit()
        flash('Tus cambios se guardaron con éxito.')
        return redirect(url_for('user', id=current_user.id))
    
    elif request.method == 'GET':
        form.fname.data = current_user.fname
        form.lname.data = current_user.lname

    return render_template('user_settings.html', title='Editar Perfil', form=form)

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