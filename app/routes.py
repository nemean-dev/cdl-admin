import os
import time
from datetime import datetime, timezone
from flask import render_template, abort, flash, redirect, url_for, request, send_file
from flask_login import login_required, current_user
import sqlalchemy as sa
from app import app, db
from app.models import User, AdminAction
from app.forms import UserSettingsForm
from app.price_tags import fetch_data_from_sheety, generate_pdf

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

@app.route('/action-log')
@login_required
def action_log():
    actions = db.session.scalars(sa.select(AdminAction)).all()
    return render_template('action_log.html', actions=actions) #TODO add pagination here and in the user profiles
    #TODO: add number id to action log and proper spacing

@app.route('/user/<id>')
@login_required
def user(id):
    user = db.session.get(User, id)
    if user is None:
        abort(404)

    actions = db.session.scalars(sa.select(AdminAction).where(AdminAction.admin == user))

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

@app.route('/generar-pdf-etiquetas')
@login_required
def generate_labels():
    sheety_url = app.config['SHEETY_PRICETAGS_URL']
    bearer_token = app.config['SHEETY_PRICETAGS_BEARER']

    try:
        data = fetch_data_from_sheety(sheety_url, bearer_token)
        
        timestamp = int(time.time())
        pdf_filename = f"labels_{timestamp}.pdf"
        pdf_path = os.path.join(app.static_folder, 'pdfs', pdf_filename)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        generate_pdf(data, pdf_path)
        
        return send_file(pdf_path, as_attachment=True, download_name=pdf_filename)

    except Exception as e:
        app.logger.error(f"Error generating labels: {e}")
        flash('Failed to generate labels. Please try again.', 'danger')
        return redirect(url_for('index'))

@app.route('/exportar-productos')
@login_required
def exportar_productos():
    return 'building...'