import os
from datetime import timedelta

class Config:
    # Nom de l'application
    APP_NAME = 'TeamMove'
    
    # Sécurité - Clé secrète forte
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'votre-cle-super-secrete-teammove-2024'
    
    # Base de données MySQL/XAMPP
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://root:@localhost/teammove_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Sécurité session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Protection CSRF - ACTIVÉ
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_SECRET_KEY = SECRET_KEY  # Ajoutez cette ligne
    
    # Limitation des tentatives de connexion
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_COOLDOWN_MINUTES = 15