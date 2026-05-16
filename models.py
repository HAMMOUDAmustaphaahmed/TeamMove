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
    # ── État du projet ──
    etat                = db.Column(
        db.Enum('en_cours', 'planifie', 'termine'),
        nullable=False, default='en_cours')
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

    # JSON list of booleans, one per "nuit" between date_debut and date_fin.
    # nuitees[i] = True  → l'équipe reste sur site (nuit i+1 comptée dans le même déplacement)
    # nuitees[i] = False → l'équipe rentre et repart (nuit i+1 = nouveau déplacement réel)
    # Ex: déplacement 01/04→03/04 : 2 nuits → nuitees = [True, False]
    # None / [] → déplacement d'1 seul jour, pas de question posée
    nuitees       = db.Column(db.Text, nullable=True)  # JSON

    creator       = db.relationship('User', backref='deplacements_crees')

    @property
    def nuitees_list(self):
        """Retourne la liste Python des nuitées (liste de booléens)."""
        import json
        if self.nuitees:
            try:
                return json.loads(self.nuitees)
            except Exception:
                pass
        return []

    @property
    def nb_deplacements_reels(self):
        """Nombre de déplacements réels selon les nuitées.
        Si nuitees non défini → 1.
        Sinon : 1 + nombre de nuits où l'équipe est rentrée (False).
        """
        nl = self.nuitees_list
        if not nl:
            return 1
        return 1 + sum(1 for n in nl if not n)


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
    """Heures supplémentaires rattachées à un déplacement, par jour."""
    __tablename__ = 'heures_supplementaires'

    id             = db.Column(db.Integer, primary_key=True)
    deplacement_id = db.Column(db.Integer, db.ForeignKey('deplacements.id'),
                               nullable=False, index=True)
    # date_jour : jour précis concerné (YYYY-MM-DD). Nullable pour rétrocompat.
    date_jour      = db.Column(db.Date, nullable=True, index=True)
    heures         = db.Column(db.Numeric(6, 2), nullable=False)    # ex: 1.5
    commentaire    = db.Column(db.Text, nullable=True)
    created_by     = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    deplacement    = db.relationship('Deplacement',
                                     backref=db.backref('heures_sup', lazy='dynamic'))
    creator        = db.relationship('User', backref='hs_creees')

class PayrollConfig(db.Model):
    """Configuration de la période salariale mensuelle.
    Ex : jour_debut = 26  →  mois salarial du 26/M-1 au 25/M
         jour_debut = 1   →  mois calendaire standard
    """
    __tablename__ = 'payroll_config'

    id          = db.Column(db.Integer, primary_key=True)
    jour_debut  = db.Column(db.Integer, nullable=False, default=1)  # 1..28
    updated_by  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow)

    updater     = db.relationship('User', backref='payroll_configs')
