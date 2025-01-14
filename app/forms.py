from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import Length

class UserSettingsForm(FlaskForm):
    fname = StringField('Nombre', validators=[Length(min=0, max=128)])
    lname = StringField('Apellido', validators=[Length(min=0, max=128)])
    submit = SubmitField('Actualizar')