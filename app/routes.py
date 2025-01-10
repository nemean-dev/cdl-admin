from flask import render_template
from app import app

@app.route('/')
@app.route('/index')
def index():
    return "<h1>Casa de Luna</h1>"