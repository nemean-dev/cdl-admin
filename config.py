import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or '421a8124af2a47529272631abf3d0218'

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    
    SHEETY_USERNAME=os.getenv('SHEETY_USERNAME')
    SHEETY_BEARER=os.getenv('SHEETY_BEARER')
    