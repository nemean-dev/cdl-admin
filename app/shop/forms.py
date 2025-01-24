from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField

class SubmitForm(FlaskForm):
    submit = SubmitField('Enviar')

class QueryProductsForm(FlaskForm):
    state = StringField('Estado')
    town = StringField('Pueblo/Ciudad')
    vendor = StringField('Artesano/Proveedor')
    submit = SubmitField('Buscar')
