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
    return render_template('dashboard/index.html')

@bp.route('/action-log')
@login_required
def action_log():
    actions = db.session.scalars(sa.select(AdminAction)).all()
    return render_template('dashboard/action_log.html', actions=actions) #TODO add pagination here and in the user profiles

@bp.route('/user/<id>')
@login_required
def user(id):
    user = db.session.get(User, id)
    if user is None:
        abort(404)

    actions = db.session.scalars(sa.select(AdminAction).where(AdminAction.admin == user))

    return render_template('dashboard/user.html', user=user, actions=actions)

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

    return render_template('dashboard/user_settings.html', title='Editar Perfil', form=form)

@bp.route('/loading')
def loading():
    """
    Loading page that sends a request to process_view and redirects to final_view once the process is finished
    """
    process_description = request.args.get('process_name') or ''
    process_view = request.args.get('process_view') or 'dashboard.wait'
    final_view = request.args.get('final_view') or 'dashboard.index'
    return render_template('loading.html', process= url_for(process_view, seconds=30),
                           final_url= url_for(final_view),
                           process_description= process_description)

@bp.route('/wait', defaults={'seconds': 7})
@bp.route('/wait/<seconds>')
def wait(seconds):
    try:
        time = int(seconds)
    except ValueError:
        time = 10
    sleep(time)
    return(f'Hope you had a nice {time}-second rest.')
