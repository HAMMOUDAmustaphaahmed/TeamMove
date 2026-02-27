from flask import Flask
from flask_login import LoginManager
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from config import Config
from models import db, User
import os

# Initialisation globale de CSRF
csrf = CSRFProtect()

# ─────────────────────────────────────────────────────────
# Content Security Policy — autorise tous les CDN utilisés
# ─────────────────────────────────────────────────────────
CSP = {
    'default-src': ["'self'"],
    'script-src': [
        "'self'",
        "'unsafe-inline'",       # Fonctionne UNIQUEMENT si aucun nonce n'est injecté
        "'unsafe-eval'",         # Pour jQuery et autres libs qui utilisent eval
        "https://cdn.jsdelivr.net",
        "https://code.jquery.com",
        "https://cdnjs.cloudflare.com",
    ],
    'style-src': [
        "'self'",
        "'unsafe-inline'",
        "https://cdn.jsdelivr.net",
        "https://cdnjs.cloudflare.com",
        "https://fonts.googleapis.com",
    ],
    'font-src': [
        "'self'",
        "https://fonts.gstatic.com",
        "https://cdnjs.cloudflare.com",
    ],
    'img-src': [
        "'self'",
        "data:",
        "https:",
    ],
    'connect-src': [
        "'self'",
        "https://cdn.jsdelivr.net",   # Nécessaire pour les source maps Bootstrap/Chart.js
    ],
}

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Extensions
    db.init_app(app)
    csrf.init_app(app)

    # ⚠️  IMPORTANT : NE PAS utiliser content_security_policy_nonce_in
    # Quand Talisman injecte un nonce, le navigateur ignore 'unsafe-inline'
    # ce qui bloque tous les scripts inline des templates.
    Talisman(
        app,
        force_https=False,
        strict_transport_security=False,
        content_security_policy=CSP,
        # content_security_policy_nonce_in retiré intentionnellement
    )

    # Rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )

    # Login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Enregistrement des blueprints
    from routes import main
    app.register_blueprint(main)

    # Création des tables et admin par défaut
    with app.app_context():
        db.create_all()
        create_default_admin()

    return app


def create_default_admin():
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@teammove.tn',
            is_admin=True
        )
        admin.set_password('admin123')  # Changer en production !
        db.session.add(admin)
        db.session.commit()


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)