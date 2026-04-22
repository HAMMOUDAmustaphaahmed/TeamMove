#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║           TeamMove — Database Inspector & Migrator           ║
║                                                              ║
║  Usage:                                                      ║
║    python db_tool.py inspect    → affiche la structure DB    ║
║    python db_tool.py migrate    → ajoute les nouvelles tables║
║    python db_tool.py check      → vérifie si migration OK    ║
╚══════════════════════════════════════════════════════════════╝

Placez ce fichier dans le dossier racine du projet (à côté de app.py).
Assurez-vous que votre fichier .env est présent.
"""

import os
import sys
import re
import pymysql
from dotenv import load_dotenv

load_dotenv()


# ══════════════════════════════════════════════════════════════
# CONFIG CONNEXION
# ══════════════════════════════════════════════════════════════

def get_connection():
    db_user     = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_host     = os.environ.get('DB_HOST')
    db_port     = int(os.environ.get('DB_PORT', '10154'))
    db_name     = os.environ.get('DB_NAME')

    missing = [k for k, v in {
        'DB_USER': db_user, 'DB_PASSWORD': db_password,
        'DB_HOST': db_host, 'DB_NAME': db_name
    }.items() if not v]

    if missing:
        print(f"\n❌  Variables .env manquantes : {', '.join(missing)}")
        sys.exit(1)

    return pymysql.connect(
        host=db_host, port=db_port,
        user=db_user, password=db_password,
        database=db_name,
        charset='utf8mb4',
        ssl={'ssl_mode': 'REQUIRED'},
        connect_timeout=20,
        cursorclass=pymysql.cursors.DictCursor,
    )


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def table_exists(cur, db_name, table_name):
    cur.execute("""
        SELECT COUNT(*) as cnt
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
    """, (db_name, table_name))
    return cur.fetchone()['cnt'] > 0


def column_exists(cur, db_name, table_name, col_name):
    cur.execute("""
        SELECT COUNT(*) as cnt
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
    """, (db_name, table_name, col_name))
    return cur.fetchone()['cnt'] > 0


def index_exists(cur, db_name, table_name, index_name):
    cur.execute("""
        SELECT COUNT(*) as cnt
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND INDEX_NAME = %s
    """, (db_name, table_name, index_name))
    return cur.fetchone()['cnt'] > 0


def get_columns(cur, table_name):
    cur.execute(f"DESCRIBE `{table_name}`")
    return cur.fetchall()


# ══════════════════════════════════════════════════════════════
# COMMANDE : INSPECT
# ══════════════════════════════════════════════════════════════

def cmd_inspect():
    print("\n" + "═" * 60)
    print("  📊  INSPECTION DE LA BASE DE DONNÉES")
    print("═" * 60)

    conn = get_connection()
    db_name = os.environ.get('DB_NAME')
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            tables = [list(row.values())[0] for row in cur.fetchall()]

            if not tables:
                print("\n  ⚠️  Aucune table trouvée.\n")
                return

            print(f"\n  Base : {db_name}  |  {len(tables)} table(s) trouvée(s)")
            print(f"  Tables : {', '.join(tables)}\n")

            for table in tables:
                print("─" * 60)
                print(f"  📋  TABLE : {table.upper()}")
                print("─" * 60)

                col_widths = [20, 20, 6, 10, 15, 10]
                headers    = ['Colonne', 'Type', 'Null', 'Clé', 'Défaut', 'Extra']
                print("  " + "  ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)))
                print("  " + "-" * 80)

                for col in get_columns(cur, table):
                    vals = [
                        str(col.get('Field', '')),
                        str(col.get('Type', '')),
                        str(col.get('Null', '')),
                        str(col.get('Key', '')),
                        str(col.get('Default', '') or ''),
                        str(col.get('Extra', '')),
                    ]
                    print("  " + "  ".join(v[:col_widths[i]].ljust(col_widths[i]) for i, v in enumerate(vals)))

                cur.execute(f"SHOW INDEX FROM `{table}`")
                indexes = cur.fetchall()
                if indexes:
                    idx_map = {}
                    for idx in indexes:
                        idx_map.setdefault(idx['Key_name'], []).append(idx['Column_name'])
                    print("\n  Index :")
                    for iname, icols in idx_map.items():
                        uniq = any(i['Key_name'] == iname and i['Non_unique'] == 0 for i in indexes)
                        flag = ' [UNIQUE]' if uniq else ''
                        print(f"    • {iname}{flag} → ({', '.join(icols)})")

                cur.execute("""
                    SELECT kcu.COLUMN_NAME, kcu.REFERENCED_TABLE_NAME, kcu.REFERENCED_COLUMN_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                    JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                        ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                       AND tc.TABLE_NAME      = kcu.TABLE_NAME
                    WHERE tc.CONSTRAINT_TYPE = 'FOREIGN KEY'
                      AND kcu.TABLE_SCHEMA   = %s
                      AND kcu.TABLE_NAME     = %s
                """, (db_name, table))
                fks = cur.fetchall()
                if fks:
                    print("\n  Clés étrangères :")
                    for fk in fks:
                        print(f"    • {fk['COLUMN_NAME']} → {fk['REFERENCED_TABLE_NAME']}.{fk['REFERENCED_COLUMN_NAME']}")

                cur.execute(f"SELECT COUNT(*) as cnt FROM `{table}`")
                print(f"\n  Lignes : {cur.fetchone()['cnt']}\n")

    finally:
        conn.close()

    print("═" * 60)
    print("  ✅  Inspection terminée")
    print("═" * 60 + "\n")


# ══════════════════════════════════════════════════════════════
# COMMANDE : CHECK
# ══════════════════════════════════════════════════════════════

# Liste exhaustive de tout ce que la migration doit garantir :
#   (type, table, colonne_ou_None)
MIGRATION_CHECKS = [
    # Tables existantes à compléter
    ('column', 'projets',                  'etat'),
    ('column', 'deplacements',             'nuitees'),        # v3 — nuitées multi-jours
    ('column', 'heures_supplementaires',   'date'),           # v4 — granularité par jour
    # Nouvelles tables
    ('table',  'payroll_config',           None),
    # Tables déjà présentes (vérification)
    ('table',  'work_schedules',           None),
    ('table',  'heures_supplementaires',   None),
]


def cmd_check():
    print("\n" + "═" * 60)
    print("  🔍  VÉRIFICATION DES TABLES ET COLONNES")
    print("═" * 60)

    conn    = get_connection()
    db_name = os.environ.get('DB_NAME')
    all_ok  = True

    try:
        with conn.cursor() as cur:
            for kind, table, col in MIGRATION_CHECKS:
                if kind == 'table':
                    exists = table_exists(cur, db_name, table)
                    status = '✅' if exists else '❌'
                    note   = 'existe' if exists else 'MANQUANTE → migration nécessaire'
                    print(f"\n  {status}  table  `{table}` — {note}")
                    if exists:
                        for c in get_columns(cur, table):
                            print(f"       • {c['Field']:25s} {c['Type']}")
                    else:
                        all_ok = False

                elif kind == 'column':
                    exists = column_exists(cur, db_name, table, col)
                    status = '✅' if exists else '❌'
                    note   = 'présente' if exists else 'MANQUANTE → migration nécessaire'
                    print(f"\n  {status}  colonne `{table}.{col}` — {note}")
                    if not exists:
                        all_ok = False

        print()
        if all_ok:
            print("  ✅  Base de données à jour. Aucune migration nécessaire.\n")
        else:
            print("  ⚠️   Exécutez :  python db_tool.py migrate\n")

    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
# MIGRATION SQL
# Chaque entrée : (description, SQL, idempotent)
# ══════════════════════════════════════════════════════════════

def build_migration_steps(cur, db_name):
    """
    Retourne la liste des étapes à exécuter selon l'état réel de la DB.
    Chaque étape : (label, sql_statement)
    """
    steps = []

    # ── 1. Colonne projets.etat ──────────────────────────────
    if not column_exists(cur, db_name, 'projets', 'etat'):
        steps.append((
            "ADD COLUMN projets.etat",
            """
            ALTER TABLE `projets`
            ADD COLUMN `etat` ENUM('en_cours','planifie','termine')
                NOT NULL DEFAULT 'en_cours'
                AFTER `coordinates`
            """
        ))
    else:
        steps.append(("SKIP   projets.etat (déjà présent)", None))

    # ── 2. Colonne deplacements.nuitees (v3) ─────────────────
    if not column_exists(cur, db_name, 'deplacements', 'nuitees'):
        steps.append((
            "ADD COLUMN deplacements.nuitees",
            """
            ALTER TABLE `deplacements`
            ADD COLUMN `nuitees` TEXT NULL
                COMMENT 'JSON list of booleans: true=reste sur site, false=rentre (v3)'
                AFTER `statut`
            """
        ))
    else:
        steps.append(("SKIP   deplacements.nuitees (déjà présent)", None))

    # ── 3. Table payroll_config ──────────────────────────────
    if not table_exists(cur, db_name, 'payroll_config'):
        steps.append((
            "CREATE TABLE payroll_config",
            """
            CREATE TABLE `payroll_config` (
                `id`         INT UNSIGNED  NOT NULL AUTO_INCREMENT,
                `jour_debut` TINYINT       NOT NULL DEFAULT 1
                                           COMMENT 'Jour de début du mois salarial (1-28)',
                `updated_by` INT UNSIGNED  NULL,
                `updated_at` DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                           ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (`id`),
                CONSTRAINT `fk_pc_user`
                    FOREIGN KEY (`updated_by`)
                    REFERENCES `users` (`id`)
                    ON DELETE SET NULL ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
              COMMENT='Configuration de la période salariale mensuelle'
            """
        ))
    else:
        steps.append(("SKIP   payroll_config (déjà présente)", None))

    # ── 4. Table work_schedules ──────────────────────────────
    if not table_exists(cur, db_name, 'work_schedules'):
        steps.append((
            "CREATE TABLE work_schedules",
            """
            CREATE TABLE `work_schedules` (
                `id`          INT UNSIGNED  NOT NULL AUTO_INCREMENT,
                `nom`         VARCHAR(100)  NOT NULL,
                `heure_debut` TIME          NOT NULL,
                `heure_fin`   TIME          NOT NULL,
                `is_active`   TINYINT(1)    NOT NULL DEFAULT 1,
                `created_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        ))
    else:
        steps.append(("SKIP   work_schedules (déjà présente)", None))

    # ── 5. Table heures_supplementaires ─────────────────────
    if not table_exists(cur, db_name, 'heures_supplementaires'):
        steps.append((
            "CREATE TABLE heures_supplementaires",
            """
            CREATE TABLE `heures_supplementaires` (
                `id`             INT UNSIGNED  NOT NULL AUTO_INCREMENT,
                `deplacement_id` INT UNSIGNED  NOT NULL,
                `date`           DATE          NULL,
                `heures`         DECIMAL(6,2)  NOT NULL,
                `commentaire`    TEXT,
                `created_by`     INT UNSIGNED  NULL,
                `created_at`     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (`id`),
                INDEX `ix_hs_date` (`date`),
                INDEX `ix_hs_deplacement` (`deplacement_id`),
                INDEX `ix_hs_created_by` (`created_by`),
                CONSTRAINT `fk_hs_deplacement`
                    FOREIGN KEY (`deplacement_id`)
                    REFERENCES `deplacements` (`id`)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT `fk_hs_created_by`
                    FOREIGN KEY (`created_by`)
                    REFERENCES `users` (`id`)
                    ON DELETE SET NULL ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        ))
    else:
        steps.append(("SKIP   heures_supplementaires (déjà présente)", None))

    # ── 6. Colonne heures_supplementaires.date (v4) ──────────
    # Pour les bases existantes où la table existe déjà sans cette colonne.
    if (table_exists(cur, db_name, 'heures_supplementaires')
            and not column_exists(cur, db_name, 'heures_supplementaires', 'date')):
        steps.append((
            "ADD COLUMN heures_supplementaires.date + INDEX",
            """
            ALTER TABLE `heures_supplementaires`
            ADD COLUMN `date` DATE NULL
                COMMENT 'Jour précis concerné par les HS (v4)'
                AFTER `deplacement_id`,
            ADD INDEX `ix_hs_date` (`date`)
            """
        ))
    elif table_exists(cur, db_name, 'heures_supplementaires'):
        # Colonne présente — vérifier quand même que l'index existe
        if not index_exists(cur, db_name, 'heures_supplementaires', 'ix_hs_date'):
            steps.append((
                "ADD INDEX ix_hs_date sur heures_supplementaires.date",
                "ALTER TABLE `heures_supplementaires` ADD INDEX `ix_hs_date` (`date`)"
            ))
        else:
            steps.append(("SKIP   heures_supplementaires.date (déjà présente + indexée)", None))

    return steps


def cmd_migrate():
    print("\n" + "═" * 60)
    print("  🚀  MIGRATION — MISE À JOUR DE LA BASE DE DONNÉES")
    print("═" * 60)

    conn    = get_connection()
    db_name = os.environ.get('DB_NAME')

    try:
        with conn.cursor() as cur:

            # Vérifier prérequis
            for required in ('users', 'projets', 'deplacements'):
                if not table_exists(cur, db_name, required):
                    print(f"\n  ❌  Table prérequise `{required}` manquante.")
                    print("      Lancez d'abord l'application Flask : python app.py\n")
                    return

            steps = build_migration_steps(cur, db_name)

            print(f"\n  {len(steps)} étape(s) planifiée(s) :\n")
            for label, sql in steps:
                print(f"    {'⏭️ ' if sql is None else '▶️ '}  {label}")

            print()
            executed = 0
            skipped  = 0
            errors   = 0

            for label, sql in steps:
                if sql is None:
                    print(f"  ⏭️   {label}")
                    skipped += 1
                    continue
                try:
                    clean_sql = re.sub(r'\s+', ' ', sql).strip()
                    cur.execute(clean_sql)
                    conn.commit()
                    print(f"  ✅  {label}")
                    executed += 1
                except Exception as e:
                    conn.rollback()
                    print(f"  ❌  {label}")
                    print(f"       Erreur : {e}")
                    errors += 1

            # ── Résumé ──
            print()
            print("─" * 60)
            print(f"  Exécutées : {executed}")
            print(f"  Ignorées  : {skipped}  (déjà à jour)")
            print(f"  Erreurs   : {errors}")
            print("─" * 60)

            if errors == 0:
                print("\n  ✅  Migration terminée avec succès !\n")
            else:
                print("\n  ⚠️   Migration terminée avec des erreurs. Vérifiez ci-dessus.\n")

            # ── Afficher la structure finale des tables touchées ──
            TABLES_TO_SHOW = [
                'projets', 'deplacements', 'payroll_config',
                'work_schedules', 'heures_supplementaires',
            ]
            print("  Structure finale des tables migrées :\n")
            for tname in TABLES_TO_SHOW:
                if not table_exists(cur, db_name, tname):
                    continue
                print(f"  📋  {tname.upper()} :")
                for c in get_columns(cur, tname):
                    key_flag  = f" [{c['Key']}]"      if c['Key']              else ''
                    null_flag = ''                     if c['Null'] == 'NO'     else ' (nullable)'
                    dft_flag  = f" = {c['Default']}"  if c['Default'] is not None else ''
                    print(f"    • {c['Field']:22s} {str(c['Type']):28s}{key_flag}{null_flag}{dft_flag}")
                print()

    finally:
        conn.close()

    print("═" * 60 + "\n")


# ══════════════════════════════════════════════════════════════
# ENTRÉE PRINCIPALE
# ══════════════════════════════════════════════════════════════

def print_help():
    print("""
╔══════════════════════════════════════════════════════════════╗
║           TeamMove — Database Inspector & Migrator           ║
╠══════════════════════════════════════════════════════════════╣
║  Commandes disponibles :                                     ║
║                                                              ║
║   python db_tool.py inspect  → Structure complète de la DB  ║
║   python db_tool.py check    → Colonnes/tables à jour ?     ║
║   python db_tool.py migrate  → Appliquer les migrations     ║
╚══════════════════════════════════════════════════════════════╝

  Prérequis : fichier .env avec DB_USER, DB_PASSWORD, DB_HOST,
              DB_PORT, DB_NAME définis.
""")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)

    command = sys.argv[1].lower()
    if   command == 'inspect': cmd_inspect()
    elif command == 'check':   cmd_check()
    elif command == 'migrate': cmd_migrate()
    else:
        print(f"\n  ❌  Commande inconnue : '{command}'")
        print_help()
        sys.exit(1)