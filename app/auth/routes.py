from time import sleep
from urllib.parse import urlsplit
from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required, login_user, logout_user
import sqlalchemy as sa
from app import db
from app.models import User
from app.auth import bp
from app.auth.email import send_password_reset_email
from app.auth.forms import LoginForm, RegisterUsersForm, ResetPasswordRequestForm, ResetPasswordForm

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()

    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.email == form.email.data))
        
        if user.failed_logins > 100:
            flash('Han habido demasiados intentos de inicio de sesión erróneos.' 
                  'Contacta a un administrador si el problema persiste.')
            redirect(url_for('auth.login'))
        
        if user is not None and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash('Inicio de sesión exitoso')
            next_page = request.args.get('next')
            if not next_page or urlsplit(next_page).netloc != '':
                next_page = url_for('dashboard.index')

            return redirect(next_page)
        
        else:
            sleep(2)
            flash('Email o contraseña incorrectos')
            return redirect(url_for('auth.login'))
    
    return render_template('auth/login.html', title='Inicio de sesión', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@bp.route('/register-users', methods=['GET', 'POST'])
@login_required
def register_users():
    if not current_user.is_superadmin:
        flash("You do not have permission to access this page.", "warning")
        return redirect(url_for('dashboard.index'))
    
    form = RegisterUsersForm()

    if form.validate_on_submit():
        email = form.email.data
        if db.session.scalar(sa.select(User).where(User.email == email)) is not None:
            flash(f'Error: User for {email} already exists.', "warning")
            return redirect(url_for('auth.register_users'))

        fname, lname, password = \
            form.fname.data, form.lname.data, form.password.data
        new_user = User(email=email, fname=fname, lname=lname)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash(f"User for {new_user.email} added successfully!")

        return redirect(url_for('auth.register_users'))
    
    return render_template('auth/register_users.html', form=form)

@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.email == form.email.data))
        if user:
            send_password_reset_email(user)
        flash('Revisa tu correo para restablecer tu contraseña.')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html',
                           title='Restablecer Contraseña', form=form)

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        flash("No es posible restablecer la contraseña cuando hay una sesión activa.")
        return redirect(url_for('dashboard.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('auth.login'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        try:
            user.set_password(form.password.data)
        except:
            flash('No fue posible restablecer tu contraseña. Inténtalo nuevamente.', 'warning')
            return redirect(url_for('auth.reset_password', token=token))
        db.session.commit()
        flash('Se restableció tu contraseña')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)