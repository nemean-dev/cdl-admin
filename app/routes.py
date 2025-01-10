from flask import render_template
from app import app

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/captura')
def captura():
    return 'building...'

@app.route('/etiquetas')
def etiquetas():
    return 'building...'

@app.route('/exportar-productos')
def exportar_productos():
    return 'building...'