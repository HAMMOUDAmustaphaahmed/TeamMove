from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# ── Rôles disponibles ──
ROLE_ADMIN              = 'admin'
ROLE_RESPONSABLE_PROJET = 'responsable_projet'
ROLE_LECTEUR            = 'lecteur'

ROLES = [ROLE_ADMIN, ROLE_RESPONSABLE_PROJET, ROLE_LECTEUR]

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80),  unique=True, nullable=False, index=True)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    is_admin      = db.Column(db.Boolean, default=False)
    role          = db.Column(db.String(50), nullable=False, default=ROLE_LECTEUR)

    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    last_login    = db.Column(db.DateTime)

    @property
    def is_responsable_projet(self):
        return self.role == ROLE_RESPONSABLE_PROJET

    @property
    def is_lecteur(self):
        return self.role == ROLE_LECTEUR

    def has_write_access(self):
        return self.role in (ROLE_ADMIN, ROLE_RESPONSABLE_PROJET)

    def set_password(self, password):
        self.password_hash = generate_password_hash(
            password, method='pbkdf2:sha256', salt_length=16)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Personnel(db.Model):
    __tablename__ = 'personnels'

    id            = db.Column(db.Integer, primary_key=True)
    matricule     = db.Column(db.String(50),  unique=True, nullable=False, index=True)
    nom           = db.Column(db.String(100), nullable=False)
    prenom        = db.Column(db.String(100), nullable=False)
    fonction      = db.Column(db.String(150), nullable=True)
    societe       = db.Column(db.String(100), nullable=False)
    salaire       = db.Column(db.Numeric(10, 2), nullable=False)
    type_salaire  = db.Column(db.Enum('mensuel', 'horaire'), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    active        = db.Column(db.Boolean, default=True)

    deplacements  = db.relationship(
        'Deplacement', backref='personnel', lazy='dynamic',
        cascade='all, delete-orphan')


class Projet(db.Model):
    __tablename__ = 'projets'

    id                  = db.Column(db.Integer, primary_key=True)
    nom                 = db.Column(db.String(200), nullable=False)
    region              = db.Column(db.String(100), nullable=False)
    gouvernorat         = db.Column(db.String(100), nullable=False)
    ville               = db.Column(db.String(100), nullable=False)
    adresse             = db.Column(db.Text, nullable=False)
    # ── Coordonnées GPS (format "lat, lng") ──
    coordinates         = db.Column(db.String(100), nullable=True)
    date_debut_estimee  = db.Column(db.Date, nullable=True)
    date_fin_estimee    = db.Column(db.Date, nullable=True)
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)
    active              = db.Column(db.Boolean, default=True)

    deplacements = db.relationship('Deplacement', backref='projet', lazy='dynamic')


class Deplacement(db.Model):
    __tablename__ = 'deplacements'

    id            = db.Column(db.Integer, primary_key=True)
    personnel_id  = db.Column(db.Integer, db.ForeignKey('personnels.id'), nullable=False)
    projet_id     = db.Column(db.Integer, db.ForeignKey('projets.id'),    nullable=False)
    date_debut    = db.Column(db.Date, nullable=False)
    heure_debut   = db.Column(db.Time, nullable=False)
    date_fin      = db.Column(db.Date, nullable=False)
    heure_fin     = db.Column(db.Time, nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    created_by    = db.Column(db.Integer, db.ForeignKey('users.id'))

    statut        = db.Column(
        db.Enum('valide', 'en_attente', 'approuve', 'rejete'),
        nullable=False, default='valide')

    creator       = db.relationship('User', backref='deplacements_crees')


class DeplacementValidation(db.Model):
    __tablename__ = 'deplacement_validations'

    id               = db.Column(db.Integer, primary_key=True)
    deplacement_id   = db.Column(db.Integer, db.ForeignKey('deplacements.id'),
                                 nullable=False)
    validated_by     = db.Column(db.Integer, db.ForeignKey('users.id'),
                                 nullable=False)
    action           = db.Column(db.Enum('approuve', 'rejete'), nullable=False)
    commentaire      = db.Column(db.Text, nullable=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    deplacement      = db.relationship('Deplacement', backref='validations')
    validator        = db.relationship('User', backref='validations_effectuees')

# ══════════════════════════════════════════════════════════════════
# AJOUTS À COLLER À LA FIN DE models.py
# ══════════════════════════════════════════════════════════════════


class WorkSchedule(db.Model):
    """Séances de travail journalières définies par l'admin.
    Ex : Séance matin 08:00-12:00 / Séance après-midi 13:00-17:00
    """
    __tablename__ = 'work_schedules'

    id          = db.Column(db.Integer, primary_key=True)
    nom         = db.Column(db.String(100), nullable=False)          # "Séance matin"
    heure_debut = db.Column(db.Time, nullable=False)                  # 08:00
    heure_fin   = db.Column(db.Time, nullable=False)                  # 12:00
    is_active   = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def duree_heures(self):
        """Durée de la séance en heures (float)."""
        from datetime import datetime as dt
        d = dt.combine(dt.today(), self.heure_fin) - dt.combine(dt.today(), self.heure_debut)
        return round(d.total_seconds() / 3600, 2)


class HeureSupplementaire(db.Model):
    """Heures supplémentaires rattachées à un déplacement."""
    __tablename__ = 'heures_supplementaires'

    id             = db.Column(db.Integer, primary_key=True)
    deplacement_id = db.Column(db.Integer, db.ForeignKey('deplacements.id'),
                               nullable=False, index=True)
    heures         = db.Column(db.Numeric(6, 2), nullable=False)    # ex: 1.5
    commentaire    = db.Column(db.Text, nullable=True)
    created_by     = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    deplacement    = db.relationship('Deplacement',
                                     backref=db.backref('heures_sup', uselist=False))
    creator        = db.relationship('User', backref='hs_creees')