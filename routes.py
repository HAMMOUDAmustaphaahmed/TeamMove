from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func, and_, or_
from models import db, User, Personnel, Projet, Deplacement
from datetime import datetime, date, timedelta
from functools import wraps
import html

main = Blueprint('main', __name__)

# ── Décorateur admin ──
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Accès réservé aux administrateurs.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ── Sanitization ──
def sanitize_input(data):
    if isinstance(data, str):
        return html.escape(data.strip())
    return data

# ==================== ROUTES PUBLIQUES ====================

@main.route('/')
def landing():
    return render_template('landing.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = sanitize_input(request.form.get('username', ''))
        password = request.form.get('password', '')

        attempts_key = f'login_attempts_{request.remote_addr}'
        attempts = session.get(attempts_key, 0)

        if attempts >= 5:
            flash('Trop de tentatives. Veuillez réessayer plus tard.', 'danger')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=False)
            user.last_login = datetime.utcnow()
            db.session.commit()
            session.pop(attempts_key, None)
            flash(f'Bienvenue, {user.username}!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            session[attempts_key] = attempts + 1
            flash('Identifiants incorrects.', 'danger')

    return render_template('login.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Déconnexion réussie.', 'info')
    return redirect(url_for('main.landing'))

# ==================== DASHBOARD ====================

@main.route('/dashboard')
@login_required
def dashboard():
    today = date.today()

    # ── KPIs de base ──
    total_personnels   = Personnel.query.filter_by(active=True).count()
    total_projets      = Projet.query.filter_by(active=True).count()
    total_deplacements = Deplacement.query.count()

    # Déplacements ce mois-ci
    first_day_month = today.replace(day=1)
    total_deplacements_mois = Deplacement.query.filter(
        Deplacement.created_at >= first_day_month
    ).count()

    # ── Chart 1 (DRH) : Top personnels les plus mobiles en JOURS ──
    # On calcule la somme des (date_fin - date_debut + 1) par personnel
    all_deps = db.session.query(
        Personnel.nom,
        Personnel.prenom,
        Deplacement.date_debut,
        Deplacement.date_fin
    ).join(Deplacement, Deplacement.personnel_id == Personnel.id)\
     .filter(Personnel.active == True).all()

    # Agréger les jours par personnel côté Python (portable MySQL/SQLite)
    from collections import defaultdict
    jours_par_personnel = defaultdict(int)
    for nom, prenom, dd, df in all_deps:
        key = f"{nom} {prenom}"
        jours_par_personnel[key] += (df - dd).days + 1

    top_personnel_jours = sorted(
        jours_par_personnel.items(), key=lambda x: x[1], reverse=True
    )[:5]  # Top 5

    # ── Chart 2 (DRH) : Déplacements par société ──
    deps_par_societe = db.session.query(
        Personnel.societe,
        func.count(Deplacement.id).label('nb')
    ).join(Deplacement, Deplacement.personnel_id == Personnel.id)\
     .group_by(Personnel.societe)\
     .order_by(func.count(Deplacement.id).desc()).all()

    # ── Chart 3 (DG) : Répartition géographique — nb déplacements par région ──
    deps_par_region = db.session.query(
        Projet.region,
        func.count(Deplacement.id).label('nb')
    ).join(Deplacement, Deplacement.projet_id == Projet.id)\
     .filter(Projet.active == True)\
     .group_by(Projet.region)\
     .order_by(func.count(Deplacement.id).desc()).all()

    # ── Tableau récents ──
    recent_deplacements = Deplacement.query\
        .order_by(Deplacement.created_at.desc()).limit(8).all()

    return render_template('dashboard.html',
        total_personnels=total_personnels,
        total_projets=total_projets,
        total_deplacements=total_deplacements,
        total_deplacements_mois=total_deplacements_mois,
        # Chart 1
        top_personnel_jours=top_personnel_jours,
        # Chart 2
        deps_par_societe=deps_par_societe,
        # Chart 3
        deps_par_region=deps_par_region,
        # Récents
        recent_deplacements=recent_deplacements,
    )

# ==================== PERSONNELS ====================

@main.route('/personnels')
@login_required
def personnels():
    page   = request.args.get('page', 1, type=int)
    search = sanitize_input(request.args.get('search', ''))

    query = Personnel.query.filter_by(active=True)
    if search:
        query = query.filter(or_(
            Personnel.nom.ilike(f'%{search}%'),
            Personnel.prenom.ilike(f'%{search}%'),
            Personnel.matricule.ilike(f'%{search}%')
        ))

    personnels = query.order_by(Personnel.nom).paginate(page=page, per_page=10)
    return render_template('personnels.html', personnels=personnels, search=search)

@main.route('/personnels/add', methods=['POST'])
@login_required
def add_personnel():
    try:
        personnel = Personnel(
            matricule=sanitize_input(request.form['matricule']),
            nom=sanitize_input(request.form['nom']),
            prenom=sanitize_input(request.form['prenom']),
            societe=sanitize_input(request.form['societe']),
            salaire=float(request.form['salaire']),
            type_salaire=request.form['type_salaire']
        )
        db.session.add(personnel)
        db.session.commit()
        flash('Personnel ajouté avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur: {str(e)}', 'danger')
    return redirect(url_for('main.personnels'))

@main.route('/personnels/edit/<int:id>', methods=['POST'])
@login_required
def edit_personnel(id):
    personnel = Personnel.query.get_or_404(id)
    try:
        personnel.matricule    = sanitize_input(request.form['matricule'])
        personnel.nom          = sanitize_input(request.form['nom'])
        personnel.prenom       = sanitize_input(request.form['prenom'])
        personnel.societe      = sanitize_input(request.form['societe'])
        personnel.salaire      = float(request.form['salaire'])
        personnel.type_salaire = request.form['type_salaire']
        db.session.commit()
        flash('Personnel modifié avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur: {str(e)}', 'danger')
    return redirect(url_for('main.personnels'))

@main.route('/personnels/delete/<int:id>', methods=['POST'])
@login_required
def delete_personnel(id):
    personnel = Personnel.query.get_or_404(id)
    try:
        personnel.active = False
        db.session.commit()
        flash('Personnel supprimé avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur: {str(e)}', 'danger')
    return redirect(url_for('main.personnels'))

# ==================== PROJETS ====================

@main.route('/projets')
@login_required
def projets():
    projets_list = Projet.query.filter_by(active=True).order_by(Projet.nom).all()
    for p in projets_list:
        p.nb_deplacements = p.deplacements.count()
    total_deplacements = sum(p.nb_deplacements for p in projets_list)
    return render_template('projets.html',
                           projets=projets_list,
                           total_deplacements=total_deplacements)

@main.route('/projets/add', methods=['POST'])
@login_required
def add_projet():
    try:
        projet = Projet(
            nom=sanitize_input(request.form['nom']),
            region=sanitize_input(request.form['region']),
            gouvernorat=sanitize_input(request.form['gouvernorat']),
            ville=sanitize_input(request.form['ville']),
            adresse=sanitize_input(request.form['adresse'])
        )
        db.session.add(projet)
        db.session.commit()
        flash('Projet créé avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur: {str(e)}', 'danger')
    return redirect(url_for('main.projets'))

@main.route('/projets/edit/<int:id>', methods=['POST'])
@login_required
def edit_projet(id):
    projet = Projet.query.get_or_404(id)
    try:
        projet.nom         = sanitize_input(request.form['nom'])
        projet.region      = sanitize_input(request.form['region'])
        projet.gouvernorat = sanitize_input(request.form['gouvernorat'])
        projet.ville       = sanitize_input(request.form['ville'])
        projet.adresse     = sanitize_input(request.form['adresse'])
        db.session.commit()
        flash('Projet modifié avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur: {str(e)}', 'danger')
    return redirect(url_for('main.projets'))

@main.route('/projets/delete/<int:id>', methods=['POST'])
@login_required
def delete_projet(id):
    projet = Projet.query.get_or_404(id)
    try:
        projet.active = False
        db.session.commit()
        flash('Projet supprimé avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur: {str(e)}', 'danger')
    return redirect(url_for('main.projets'))

# ── API: données projet (modal édition) ──
@main.route('/api/projet/<int:id>')
@login_required
def api_projet(id):
    projet = Projet.query.get_or_404(id)
    return jsonify({
        'id':          projet.id,
        'nom':         projet.nom,
        'region':      projet.region,
        'gouvernorat': projet.gouvernorat,
        'ville':       projet.ville,
        'adresse':     projet.adresse,
        'created_at':  projet.created_at.strftime('%d/%m/%Y') if projet.created_at else ''
    })

# ── API: statistiques projet ──
@main.route('/api/projet/<int:id>/stats')
@login_required
def api_projet_stats(id):
    projet = Projet.query.get_or_404(id)

    nb_deplacements = projet.deplacements.count()
    nb_personnels   = db.session.query(
        func.count(Deplacement.personnel_id.distinct())
    ).filter(Deplacement.projet_id == id).scalar() or 0

    deplacements_list = projet.deplacements.all()
    nb_jours = sum((d.date_fin - d.date_debut).days + 1 for d in deplacements_list)

    personnels_data = [{
        'matricule':  d.personnel.matricule,
        'nom':        d.personnel.nom,
        'prenom':     d.personnel.prenom,
        'date_debut': d.date_debut.strftime('%d/%m/%Y'),
        'date_fin':   d.date_fin.strftime('%d/%m/%Y'),
        'jours':      (d.date_fin - d.date_debut).days + 1
    } for d in deplacements_list]

    return jsonify({
        'nom':             projet.nom,
        'ville':           projet.ville,
        'gouvernorat':     projet.gouvernorat,
        'created_at':      projet.created_at.strftime('%d/%m/%Y') if projet.created_at else '',
        'nb_deplacements': nb_deplacements,
        'nb_personnels':   nb_personnels,
        'nb_jours':        nb_jours,
        'personnels':      personnels_data
    })

# ==================== DÉPLACEMENTS ====================

@main.route('/deplacements')
@login_required
def deplacements():
    date_filter = request.args.get('date_filter', date.today().isoformat())
    search      = sanitize_input(request.args.get('search', ''))

    query = db.session.query(
        Personnel,
        func.group_concat(Projet.nom.distinct()).label('projets_list'),
        func.count(Deplacement.id).label('nb_deplacements')
    ).outerjoin(Deplacement, and_(
        Deplacement.personnel_id == Personnel.id,
        Deplacement.date_debut   <= date_filter,
        Deplacement.date_fin     >= date_filter
    )).outerjoin(Projet, Deplacement.projet_id == Projet.id)

    if search:
        query = query.filter(or_(
            Personnel.nom.ilike(f'%{search}%'),
            Personnel.prenom.ilike(f'%{search}%'),
            Personnel.matricule.ilike(f'%{search}%')
        ))

    personnels_data = query.filter(Personnel.active == True).group_by(Personnel.id).all()
    projets         = Projet.query.filter_by(active=True).all()

    total_personnels_actifs = Personnel.query.filter_by(active=True).count()
    total_en_deplacement = db.session.query(
        func.count(Deplacement.personnel_id.distinct())
    ).filter(
        Deplacement.date_debut <= date_filter,
        Deplacement.date_fin   >= date_filter
    ).scalar() or 0

    total_projets_actifs = Projet.query.filter_by(active=True).count()

    first_day_month = date.today().replace(day=1)
    total_deplacements_mois = Deplacement.query.filter(
        Deplacement.created_at >= first_day_month
    ).count()

    return render_template('deplacements.html',
                           personnels=personnels_data,
                           projets=projets,
                           date_filter=date_filter,
                           search=search,
                           total_personnels_actifs=total_personnels_actifs,
                           total_en_deplacement=total_en_deplacement,
                           total_projets_actifs=total_projets_actifs,
                           total_deplacements_mois=total_deplacements_mois)

@main.route('/api/search-personnels')
@login_required
def search_personnels():
    term  = sanitize_input(request.args.get('term', ''))
    query = Personnel.query.filter(Personnel.active == True)

    if term:
        query = query.filter(or_(
            Personnel.nom.ilike(f'%{term}%'),
            Personnel.prenom.ilike(f'%{term}%'),
            Personnel.matricule.ilike(f'%{term}%')
        ))

    limit = 30 if term else 200
    personnels = query.order_by(Personnel.nom, Personnel.prenom).limit(limit).all()

    return jsonify([{
        'id':       p.id,
        'matricule': p.matricule,
        'nom':      p.nom,
        'prenom':   p.prenom,
        'societe':  p.societe,
        'display':  f"{p.matricule} — {p.nom} {p.prenom}"
    } for p in personnels])

@main.route('/api/personnel/<int:id>/deplacements')
@login_required
def api_personnel_deplacements(id):
    personnel = Personnel.query.get_or_404(id)
    deps = Deplacement.query\
        .filter_by(personnel_id=id)\
        .order_by(Deplacement.date_debut.desc()).all()

    return jsonify([{
        'id':         d.id,
        'projet':     d.projet.nom,
        'projet_id':  d.projet_id,
        'date_debut': d.date_debut.strftime('%d/%m/%Y'),
        'date_fin':   d.date_fin.strftime('%d/%m/%Y'),
        'heure_debut': d.heure_debut.strftime('%H:%M'),
        'heure_fin':   d.heure_fin.strftime('%H:%M'),
        'jours':      (d.date_fin - d.date_debut).days + 1
    } for d in deps])

@main.route('/api/deplacement/<int:id>')
@login_required
def api_deplacement(id):
    d = Deplacement.query.get_or_404(id)
    return jsonify({
        'id':         d.id,
        'projet_id':  d.projet_id,
        'date_debut': d.date_debut.isoformat(),
        'date_fin':   d.date_fin.isoformat(),
        'heure_debut': d.heure_debut.strftime('%H:%M'),
        'heure_fin':   d.heure_fin.strftime('%H:%M')
    })

@main.route('/deplacements/add', methods=['POST'])
@login_required
def add_deplacement():
    try:
        personnel_ids = request.form.getlist('personnel_ids[]')
        if not personnel_ids:
            flash('Veuillez sélectionner au moins un personnel.', 'warning')
            return redirect(url_for('main.deplacements'))

        projet_id   = int(request.form['projet_id'])
        date_debut  = datetime.strptime(request.form['date_debut'], '%Y-%m-%d').date()
        heure_debut = datetime.strptime(request.form['heure_debut'], '%H:%M').time()
        date_fin    = datetime.strptime(request.form['date_fin'], '%Y-%m-%d').date()
        heure_fin   = datetime.strptime(request.form['heure_fin'], '%H:%M').time()

        if date_fin < date_debut:
            flash('La date de fin ne peut pas être antérieure à la date de début.', 'warning')
            return redirect(url_for('main.deplacements'))

        for pid in personnel_ids:
            dep = Deplacement(
                personnel_id=int(pid),
                projet_id=projet_id,
                date_debut=date_debut,
                heure_debut=heure_debut,
                date_fin=date_fin,
                heure_fin=heure_fin,
                created_by=current_user.id
            )
            db.session.add(dep)

        db.session.commit()
        flash(f'{len(personnel_ids)} déplacement(s) ajouté(s) avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur: {str(e)}', 'danger')

    return redirect(url_for('main.deplacements'))

@main.route('/deplacements/edit/<int:id>', methods=['POST'])
@login_required
def edit_deplacement(id):
    dep = Deplacement.query.get_or_404(id)
    try:
        dep.projet_id   = int(request.form['projet_id'])
        dep.date_debut  = datetime.strptime(request.form['date_debut'], '%Y-%m-%d').date()
        dep.heure_debut = datetime.strptime(request.form['heure_debut'], '%H:%M').time()
        dep.date_fin    = datetime.strptime(request.form['date_fin'], '%Y-%m-%d').date()
        dep.heure_fin   = datetime.strptime(request.form['heure_fin'], '%H:%M').time()
        db.session.commit()
        flash('Déplacement modifié avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur: {str(e)}', 'danger')
    return redirect(url_for('main.deplacements'))

@main.route('/deplacements/delete/<int:id>', methods=['POST'])
@login_required
def delete_deplacement(id):
    dep = Deplacement.query.get_or_404(id)
    try:
        db.session.delete(dep)
        db.session.commit()
        flash('Déplacement supprimé avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur: {str(e)}', 'danger')
    return redirect(url_for('main.deplacements'))

# ==================== UTILISATEURS ====================

@main.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template('users.html', users=users)

@main.route('/users/add', methods=['POST'])
@login_required
@admin_required
def add_user():
    try:
        user = User(
            username=sanitize_input(request.form['username']),
            email=sanitize_input(request.form['email']),
            is_admin=request.form.get('is_admin') == 'on'
        )
        user.set_password(request.form['password'])
        db.session.add(user)
        db.session.commit()
        flash('Utilisateur créé avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur: {str(e)}', 'danger')
    return redirect(url_for('main.users'))

@main.route('/users/toggle/<int:id>', methods=['POST'])
@login_required
@admin_required
def toggle_user(id):
    user = User.query.get_or_404(id)
    if user.id != current_user.id:
        user.is_active = not user.is_active
        db.session.commit()
        flash("Statut de l'utilisateur modifié.", 'success')
    else:
        flash("Vous ne pouvez pas désactiver votre propre compte.", 'danger')
    return redirect(url_for('main.users'))