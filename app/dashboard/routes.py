from datetime import datetime, timezone
from flask import render_template, abort, flash, redirect, url_for, request
from flask_login import login_required, current_user
import sqlalchemy as sa
from app import db
from app.dashboard import bp
from app.models import User, AdminAction
from app.dashboard.forms import UserSettingsForm

from time import sleep

@bp.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    return render_template('index.html')

@bp.route('/action-log')
@login_required
def action_log():
    actions = db.session.scalars(sa.select(AdminAction)).all()
    return render_template('action_log.html', actions=actions) #TODO add pagination here and in the user profiles

@bp.route('/user/<id>')
@login_required
def user(id):
    user = db.session.get(User, id)
    if user is None:
        abort(404)

    actions = db.session.scalars(sa.select(AdminAction).where(AdminAction.admin == user))

    return render_template('user.html', user=user, actions=actions)

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def user_settings():
    form = UserSettingsForm()

    if form.validate_on_submit():
        current_user.fname = form.fname.data
        current_user.lname = form.lname.data
        db.session.commit()
        flash('Tus cambios se guardaron con éxito.')
        return redirect(url_for('dashboard.user', id=current_user.id))
    
    elif request.method == 'GET':
        form.fname.data = current_user.fname
        form.lname.data = current_user.lname

    return render_template('user_settings.html', title='Editar Perfil', form=form)

@bp.route('/loading')
def loading():
    return render_template('loading.html', process= url_for( 'dashboard.wait', seconds=30),
                           final_url= url_for('dashboard.index'),
                           process_name= 'this is a test...')

@bp.route('/wait/<seconds>')
def wait(seconds):
    try:
        time = int(seconds)
    except ValueError as e:
        flash('You did not enter a valid time, therefore you had to wait 10 seconds.')
        time = 9
    sleep(time)
    return(f'Hope you had a nice {time}-second rest.')
