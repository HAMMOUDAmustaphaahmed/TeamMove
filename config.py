import os
from datetime import timedelta
from dotenv import load_dotenv

# Charge les variables depuis .env (ignoré si déjà définies dans l'environnement)
load_dotenv()

class Config:
    # Nom de l'application
    APP_NAME = 'TeamMove'

    # Sécurité - Clé secrète
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # Base de données — Aiven MySQL (assemblée depuis les variables .env)
    _db_user     = os.environ.get('DB_USER')
    _db_password = os.environ.get('DB_PASSWORD')
    _db_host     = os.environ.get('DB_HOST')
    _db_port     = os.environ.get('DB_PORT', '10154')
    _db_name     = os.environ.get('DB_NAME')

    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL') or
        f"mysql+pymysql://{_db_user}:{_db_password}@{_db_host}:{_db_port}/{_db_name}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Optimisations pour Aiven free tier
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle':  280,
        'pool_pre_ping': True,
        'pool_size':     2,
        'max_overflow':  3,
        'pool_timeout':  30,
        'connect_args': {
            'connect_timeout': 20,
            'read_timeout':    20,
            'write_timeout':   20,
            'charset':         'utf8mb4',
            'use_unicode':     True,
            'ssl': {
                'ssl_mode': 'REQUIRED',
            }
        }
    }

    # Sécurité session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_SECURE      = False
    SESSION_COOKIE_HTTPONLY    = True
    SESSION_COOKIE_SAMESITE    = 'Lax'

    # Protection CSRF - ACTIVÉ
    WTF_CSRF_ENABLED    = True
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_SECRET_KEY = SECRET_KEY

    # Limitation des tentatives de connexion
    MAX_LOGIN_ATTEMPTS     = 5
    LOGIN_COOLDOWN_MINUTES = 15