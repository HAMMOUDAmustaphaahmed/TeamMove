import os
from flask import Flask
from flask_login import LoginManager
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from config import Config
from models import db, User

# ── Extension CSRF globale ──
csrf = CSRFProtect()

# ─────────────────────────────────────────────────────────
# Content Security Policy — autorise tous les CDN utilisés
# ─────────────────────────────────────────────────────────
CSP = {
    'default-src': ["'self'"],
    'script-src': [
        "'self'",
        "'unsafe-inline'",
        "'unsafe-eval'",
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
    'img-src': ["'self'", "data:", "https:", "https://server.arcgisonline.com", "https://*.arcgisonline.com", "https://tile.openstreetmap.org"],
    'connect-src': ["'self'", "https://cdn.jsdelivr.net", "https://server.arcgisonline.com", "https://*.arcgisonline.com"],
}


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ── Extensions ──
    db.init_app(app)
    csrf.init_app(app)

    Talisman(
        app,
        force_https=False,
        strict_transport_security=False,
        content_security_policy=CSP,
    )

    Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )

    # ── Login manager ──
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ── Blueprint ──
    from routes import main
    app.register_blueprint(main)

    # ── Initialisation BDD ──
    with app.app_context():
        db.create_all()
        _create_default_admin(app)

    return app


def _create_default_admin(app):
    """Crée l'admin par défaut si absent.
    Le mot de passe initial est lu depuis .env (ADMIN_DEFAULT_PASSWORD).
    """
    if not User.query.filter_by(username='admin').first():
        default_pwd = os.environ.get('ADMIN_DEFAULT_PASSWORD', 'Admin.Init!2026')
        admin = User(
            username='admin',
            email='admin@teammove.tn',
            role='admin',
            is_admin=True,
        )
        admin.set_password(default_pwd)
        db.session.add(admin)
        db.session.commit()
        app.logger.warning(
            "Compte admin créé avec le mot de passe par défaut. "
            "Changez-le immédiatement via Mon Profil !"
        )


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)