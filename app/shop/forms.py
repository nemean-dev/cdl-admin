from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import Length

class SubmitForm(FlaskForm):
    submit = SubmitField('Enviar')