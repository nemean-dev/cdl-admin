from urllib.parse import urlsplit
from flask import render_template, redirect, url_for, flash, request
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
    form = LoginForm()

    if form.validate_on_submit():
        if not any([form.email.data == user['email'] and 
                    form.password.data == user['password'] for user in USERS]):
            flash("Credenciales de inicio de sesión inválidas")
            return redirect(url_for('auth.login'))
        
        else:
            flash("Inicio de sesión exitoso")

            next_page = request.args.get('next')
            if not next_page or urlsplit(next_page).netloc != '':
                next_page = url_for('index')

            return redirect(next_page)

    return render_template('login.html', title='Inicio de Sesión', form=form)