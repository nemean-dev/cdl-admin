import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or '421a8124af2a47529272631abf3d0218'
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    
    SHOPIFY_STORE = os.getenv('SHOPIFY_STORE')
    SHOPIFY_LOCATION_ID = os.getenv('SHOPIFY_LOCATION_ID') 
    SHOPIFY_API_TOKEN = os.getenv('SHOPIFY_API_TOKEN') 

    LOGS_DIR = os.path.join(basedir, 'logs/')
    DATA_DIR = os.path.join(basedir, 'data/')

    # some deployments require logging to stdout
    LOG_TO_STDOUT = os.getenv('LOG_TO_STDOUT') == '1'

    # integrations
    GSHEETS_CREDENTIALS = os.getenv("GSHEETS_CREDENTIALS")
    GSHEETS_CAPTURA_ID = os.getenv('GSHEETS_CAPTURA_ID')
    
    SHEETY_USERNAME=os.getenv('SHEETY_USERNAME')
    SHEETY_BEARER=os.getenv('SHEETY_BEARER')

    # email configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS') is not None and os.getenv('MAIL_USE_TLS') != 0
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    ADMINS = os.getenv('MAIL_ADMINS').split(',') if os.getenv('MAIL_ADMINS') else None

    # S3 storage
    USE_LOCAL_STORAGE = os.getenv('USE_LOCAL_STORAGE', False)
    AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
    AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
    AWS_REGION = os.getenv('AWS_REGION')
    AWS_BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')

    # External links
    URL_WORKLOG=os.getenv('URL_WORKLOG')
    URL_KANBAN=os.getenv('URL_KANBAN')

    # Customize app:
    ADMIN_ACTIONS_PER_PAGE = 50
    VENDORS_PER_PAGE = 50
