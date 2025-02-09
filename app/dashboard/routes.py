from datetime import datetime, timezone
from flask import render_template, abort, flash, redirect, url_for, request, current_app
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

@bp.route("/health")
def health():
    return "OK", 200

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    return render_template('dashboard/index.html')

@bp.route('/action-log')
@login_required
def action_log():
    page = request.args.get('page', 1, int)
    query = sa.select(AdminAction).order_by(AdminAction.timestamp.desc())
    actions = db.paginate(query, page=page, error_out=False, 
                          per_page=current_app.config['ADMIN_ACTIONS_PER_PAGE'])
    
    pagination = {
        'page': page,
        'next_url': url_for('dashboard.action_log',
                            page=actions.next_num) if actions.has_next else None,
        'prev_url': url_for('dashboard.action_log', 
                            page=actions.prev_num) if actions.has_prev else None,
    }

    return render_template('dashboard/action_log.html', actions=actions.items, 
                           pagination=pagination)

@bp.route('/user/<id>')
@login_required
def user(id):
    user = db.first_or_404(sa.select(User).where(User.id == id))

    page = request.args.get('page', 1, int)
    query = sa.select(AdminAction).where(AdminAction.admin == user).order_by(AdminAction.timestamp.desc())
    actions = db.paginate(query, page=page, error_out=False, 
                          per_page=current_app.config['ADMIN_ACTIONS_PER_PAGE'])
    
    pagination = {
        'page': page,
        'next_url': url_for('dashboard.user', id=user.id,
                            page=actions.next_num) if actions.has_next else None,
        'prev_url': url_for('dashboard.user', id=user.id, 
                            page=actions.prev_num) if actions.has_prev else None,
    }

    return render_template('dashboard/user.html', user=user, 
                           actions=actions.items, pagination=pagination)

@bp.route('/users')
@login_required
def users():
    page = request.args.get('page', 1, int)
    query = sa.select(User).order_by(User.is_superadmin.desc(), User.last_seen.desc())
    all_users = db.paginate(
        query, page=page, per_page=current_app.config['ADMIN_ACTIONS_PER_PAGE'])

    pagination = {
        'page': page,
        'next_url': url_for('dashboard.user', id=user.id,
                            page=all_users.next_num) if all_users.has_next else None,
        'prev_url': url_for('dashboard.user', id=user.id, 
                            page=all_users.prev_num) if all_users.has_prev else None,
    }
    
    return render_template('dashboard/users.html', users=all_users, 
                           pagination=pagination)

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
@login_required
def loading():
    """
    Loading page that sends a request to process_view and redirects to final_view once the process is finished
    """
    process_description = request.args.get('process_description') or ''
    process_view = request.args.get('process_view') or 'dashboard.wait'
    final_view = request.args.get('final_view') or 'dashboard.index'
    return render_template('loading.html', process= url_for(process_view),
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

@bp.route('/break-app')
@login_required
def break_app():
    if not current_user.is_superadmin:
        return redirect(url_for('dashboard.index'))
    raise Exception('For testing app logger smtp handler')