import os
from datetime import timedelta

class Config:
    # Nom de l'application
    APP_NAME = 'TeamMove'
    
    # Sécurité - Clé secrète forte
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'votre-cle-super-secrete-teammove-2024'
    
    # Base de données — Aiven MySQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or (
        
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
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Protection CSRF - ACTIVÉ
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_SECRET_KEY = SECRET_KEY
    
    # Limitation des tentatives de connexion
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_COOLDOWN_MINUTES = 15