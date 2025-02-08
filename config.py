import os
from datetime import timedelta
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['stevejameson238@gmail.com']
    POSTS_PER_PAGE = 25
    MSEARCH_INDEX_NAME = 'msearch'  # Name of the index directory
    MSEARCH_BACKEND = 'whoosh'  # Can also be 'sphinx' or 'elasticsearch'
    MSEARCH_ENABLE = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)