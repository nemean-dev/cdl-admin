from urllib.parse import urlsplit
from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required, login_user, logout_user
import sqlalchemy as sa
from app import db
from app.models import User
from app.auth import bp
from app.auth.forms import LoginForm, RegisterUsersForm

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

@bp.route('/register-users', methods=['GET', 'POST'])
@login_required
def register_users():
    if not current_user.is_superadmin:
        flash("You do not have permission to access this page.", "warning")
        return redirect(url_for('index'))#TODO test and flash a warning
    
    form = RegisterUsersForm()

    if form.validate_on_submit():
        email = form.email.data
        if db.session.scalar(sa.select(User).where(User.email == email)) is not None:
            flash(f'Error: User for {email} already exists.', "warning")
            #TODO: make this flashed message be red or yellow. How to do warnings?
            return redirect(url_for('auth.register_users'))

        fname, lname, password = \
            form.fname.data, form.lname.data, form.password.data
        new_user = User(email=email, fname=fname, lname=lname)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash(f"User for {new_user.email} added successfully!")

        return redirect(url_for('auth.register_users'))
    
    return render_template('register_users.html', form=form)