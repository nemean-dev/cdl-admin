from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length

class LoginForm(FlaskForm):
    email = StringField('email', validators=[
            DataRequired(message="Ingresa tu correo electrónico."), 
            Email(message="El correo ingresado no es válido."),
        ])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Recordarme')
    submit = SubmitField('Iniciar Sesión')

class RegisterUsersForm(FlaskForm):
    email = StringField('email', validators=[
            DataRequired(message="Ingresa tu correo electrónico."), 
            Email(message="El correo ingresado no es válido."),
        ])
    fname = StringField('Nombre', validators=[Length(min=0, max=128)])
    lname = StringField('Apellido', validators=[Length(min=0, max=128)])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Crear Usuario')