import os

SECRET_KEY = 'your_secret_key_here'
basedir = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'attendance.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False
