from urllib.parse import urlsplit
from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_user, logout_user
import sqlalchemy as sa
from app import db
from app.models import User
from app.auth import bp
from app.auth.forms import LoginForm

USERS = [
    {
        'email': 'frodo@example.com',
        'password': '1234'
    },
    {
        'email': 'sam@example.com',
        'password': '1234'
    },
    {
        'email': 'sauron@example.com',
        'password': '4321'
    }]

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()

    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.email == form.email.data))
        
        if user is not None and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash('Inicio de sesión exitoso')
            next_page = request.args.get('next')
            if not next_page or urlsplit(next_page).netloc != '':
                next_page = url_for('index')

            return redirect(next_page)
        
        else:
            flash('Email o contraseña incorrectos')
            return redirect(url_for('auth.login'))
    
    return render_template('login.html', title='Inicio de sesión', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))