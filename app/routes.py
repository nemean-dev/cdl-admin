from flask import render_template
from flask_login import login_required
from app import app

@app.route('/')
@app.route('/index')
@login_required
def index():
    return render_template('index.html')

@app.route('/captura')
@login_required
def captura():
    return render_template('captura.html', title='Captura')

@app.route('/etiquetas')
def etiquetas():
    return 'building...'

@app.route('/exportar-productos')
@login_required
def exportar_productos():
    return 'building...'