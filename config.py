import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or '421a8124af2a47529272631abf3d0218'