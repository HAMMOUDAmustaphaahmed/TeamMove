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
import pymysql
from dotenv import load_dotenv

# ── Charger les variables d'environnement depuis .env ──
load_dotenv()

# ══════════════════════════════════════════════════════════════
# CONFIG CONNEXION
# ══════════════════════════════════════════════════════════════

def get_connection():
    """Crée une connexion PyMySQL depuis les variables d'env."""
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
        print("    Vérifiez votre fichier .env\n")
        sys.exit(1)

    conn = pymysql.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database=db_name,
        charset='utf8mb4',
        ssl={'ssl_mode': 'REQUIRED'},
        connect_timeout=20,
        cursorclass=pymysql.cursors.DictCursor,
    )
    return conn


# ══════════════════════════════════════════════════════════════
# COMMANDE : INSPECT
# ══════════════════════════════════════════════════════════════

def cmd_inspect():
    """Affiche la structure complète de la base de données."""
    print("\n" + "═" * 60)
    print("  📊  INSPECTION DE LA BASE DE DONNÉES")
    print("═" * 60)

    conn = get_connection()
    try:
        with conn.cursor() as cur:

            # ── Liste des tables ──
            cur.execute("SHOW TABLES")
            tables = [list(row.values())[0] for row in cur.fetchall()]

            if not tables:
                print("\n  ⚠️  Aucune table trouvée dans la base de données.\n")
                return

            print(f"\n  Base : {os.environ.get('DB_NAME')}  |  {len(tables)} table(s) trouvée(s)")
            print(f"  Tables : {', '.join(tables)}\n")

            for table in tables:
                print("─" * 60)
                print(f"  📋  TABLE : {table.upper()}")
                print("─" * 60)

                # ── Colonnes ──
                cur.execute(f"DESCRIBE `{table}`")
                cols = cur.fetchall()

                col_widths = [20, 20, 6, 10, 15, 10]
                headers = ['Colonne', 'Type', 'Null', 'Clé', 'Défaut', 'Extra']
                header_line = "  " + "  ".join(
                    h.ljust(col_widths[i]) for i, h in enumerate(headers)
                )
                print(header_line)
                print("  " + "-" * 80)

                for col in cols:
                    row_vals = [
                        str(col.get('Field', '')),
                        str(col.get('Type', '')),
                        str(col.get('Null', '')),
                        str(col.get('Key', '')),
                        str(col.get('Default', '') or ''),
                        str(col.get('Extra', '')),
                    ]
                    line = "  " + "  ".join(
                        v[:col_widths[i]].ljust(col_widths[i]) for i, v in enumerate(row_vals)
                    )
                    print(line)

                # ── Index ──
                cur.execute(f"SHOW INDEX FROM `{table}`")
                indexes = cur.fetchall()
                if indexes:
                    index_summary = {}
                    for idx in indexes:
                        name = idx.get('Key_name', '')
                        col  = idx.get('Column_name', '')
                        uniq = '(UNIQUE)' if idx.get('Non_unique') == 0 else ''
                        index_summary.setdefault(name, []).append(col)
                    print()
                    print(f"  Index :")
                    for iname, icols in index_summary.items():
                        uniq_flag = ''
                        for idx in indexes:
                            if idx.get('Key_name') == iname and idx.get('Non_unique') == 0:
                                uniq_flag = ' [UNIQUE]'
                                break
                        print(f"    • {iname}{uniq_flag} → ({', '.join(icols)})")

                # ── Foreign Keys ──
                cur.execute("""
                    SELECT
                        kcu.CONSTRAINT_NAME,
                        kcu.COLUMN_NAME,
                        kcu.REFERENCED_TABLE_NAME,
                        kcu.REFERENCED_COLUMN_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                    JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                        ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                        AND tc.TABLE_NAME = kcu.TABLE_NAME
                    WHERE tc.CONSTRAINT_TYPE = 'FOREIGN KEY'
                      AND kcu.TABLE_SCHEMA = %s
                      AND kcu.TABLE_NAME   = %s
                """, (os.environ.get('DB_NAME'), table))
                fks = cur.fetchall()
                if fks:
                    print()
                    print(f"  Clés étrangères :")
                    for fk in fks:
                        print(f"    • {fk['COLUMN_NAME']} → {fk['REFERENCED_TABLE_NAME']}.{fk['REFERENCED_COLUMN_NAME']}")

                # ── Nombre de lignes ──
                cur.execute(f"SELECT COUNT(*) as cnt FROM `{table}`")
                count = cur.fetchone()['cnt']
                print()
                print(f"  Lignes : {count}")
                print()

    finally:
        conn.close()

    print("═" * 60)
    print("  ✅  Inspection terminée")
    print("═" * 60 + "\n")


# ══════════════════════════════════════════════════════════════
# COMMANDE : CHECK
# ══════════════════════════════════════════════════════════════

def cmd_check():
    """Vérifie si les nouvelles tables existent déjà."""
    print("\n" + "═" * 60)
    print("  🔍  VÉRIFICATION DES TABLES DE MIGRATION")
    print("═" * 60)

    REQUIRED_TABLES = ['work_schedules', 'heures_supplementaires']

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            existing = {list(row.values())[0] for row in cur.fetchall()}

            all_ok = True
            for table in REQUIRED_TABLES:
                if table in existing:
                    print(f"\n  ✅  {table} — existe déjà")
                    # Afficher les colonnes rapidement
                    cur.execute(f"DESCRIBE `{table}`")
                    cols = cur.fetchall()
                    for c in cols:
                        print(f"       • {c['Field']:25s} {c['Type']}")
                else:
                    print(f"\n  ❌  {table} — MANQUANTE → migration nécessaire")
                    all_ok = False

            print()
            if all_ok:
                print("  ✅  Toutes les tables sont présentes. Migration déjà effectuée.\n")
            else:
                print("  ⚠️   Exécutez :  python db_tool.py migrate\n")

    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
# COMMANDE : MIGRATE
# ══════════════════════════════════════════════════════════════

MIGRATION_SQL = """
-- ────────────────────────────────────────────────────────────
-- Table : work_schedules
-- Séances de travail journalières (ex : matin 08h-12h)
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `work_schedules` (
    `id`          INT           NOT NULL AUTO_INCREMENT,
    `nom`         VARCHAR(100)  NOT NULL,
    `heure_debut` TIME          NOT NULL,
    `heure_fin`   TIME          NOT NULL,
    `is_active`   TINYINT(1)    NOT NULL DEFAULT 1,
    `created_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ────────────────────────────────────────────────────────────
-- Table : heures_supplementaires
-- Heures supplémentaires rattachées à un déplacement
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `heures_supplementaires` (
    `id`             INT          NOT NULL AUTO_INCREMENT,
    `deplacement_id` INT          NOT NULL,
    `heures`         DECIMAL(6,2) NOT NULL,
    `commentaire`    TEXT,
    `created_by`     INT,
    `created_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `ix_hs_deplacement_id` (`deplacement_id`),
    CONSTRAINT `fk_hs_deplacement`
        FOREIGN KEY (`deplacement_id`)
        REFERENCES `deplacements` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT `fk_hs_created_by`
        FOREIGN KEY (`created_by`)
        REFERENCES `users` (`id`)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


def cmd_migrate():
    """Crée les nouvelles tables dans la base de données."""
    print("\n" + "═" * 60)
    print("  🚀  MIGRATION — AJOUT DES NOUVELLES TABLES")
    print("═" * 60)

    conn = get_connection()
    try:
        with conn.cursor() as cur:

            # Vérifier les tables existantes avant
            cur.execute("SHOW TABLES")
            existing_before = {list(row.values())[0] for row in cur.fetchall()}

            # Vérifier que la table deplacements existe (dépendance FK)
            if 'deplacements' not in existing_before:
                print("\n  ❌  La table 'deplacements' n'existe pas encore.")
                print("      Lancez d'abord l'application Flask pour créer les tables de base.")
                print("      (python app.py)\n")
                return

            print(f"\n  Tables existantes : {', '.join(sorted(existing_before))}\n")

            # Exécuter les CREATE TABLE
            statements = [s.strip() for s in MIGRATION_SQL.split(';') if s.strip()
                          and not s.strip().startswith('--')]

            created = []
            skipped = []

            for stmt in statements:
                # Extraire le nom de table du statement
                import re
                m = re.search(r'CREATE TABLE IF NOT EXISTS `(\w+)`', stmt)
                if not m:
                    continue
                table_name = m.group(1)

                try:
                    cur.execute(stmt)
                    conn.commit()
                    if table_name in existing_before:
                        skipped.append(table_name)
                        print(f"  ⏭️   {table_name:35s} déjà existante — ignorée")
                    else:
                        created.append(table_name)
                        print(f"  ✅  {table_name:35s} créée avec succès")
                except Exception as e:
                    conn.rollback()
                    print(f"  ❌  {table_name:35s} ERREUR : {e}")

            # Résumé
            print()
            print("─" * 60)
            print(f"  Créées  : {len(created)}  ({', '.join(created) if created else 'aucune'})")
            print(f"  Ignorées: {len(skipped)}  ({', '.join(skipped) if skipped else 'aucune'})")
            print("─" * 60)

            if created:
                print("\n  ✅  Migration terminée avec succès !")
                print("      Les nouvelles tables sont prêtes.\n")
            else:
                print("\n  ℹ️   Aucune nouvelle table créée (déjà à jour).\n")

            # Afficher la structure des tables créées/vérifiées
            for tname in ['work_schedules', 'heures_supplementaires']:
                cur.execute(f"DESCRIBE `{tname}`")
                cols = cur.fetchall()
                print(f"  Structure de '{tname}' :")
                for c in cols:
                    null_flag = '' if c['Null'] == 'NO' else ' (nullable)'
                    key_flag  = f" [{c['Key']}]" if c['Key'] else ''
                    print(f"    • {c['Field']:20s} {c['Type']:20s}{key_flag}{null_flag}")
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
║   python db_tool.py check    → Tables migration présentes ? ║
║   python db_tool.py migrate  → Créer les nouvelles tables   ║
╚══════════════════════════════════════════════════════════════╝

  Prérequis : fichier .env avec DB_USER, DB_PASSWORD, DB_HOST,
              DB_PORT, DB_NAME définis.
""")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == 'inspect':
        cmd_inspect()
    elif command == 'check':
        cmd_check()
    elif command == 'migrate':
        cmd_migrate()
    else:
        print(f"\n  ❌  Commande inconnue : '{command}'")
        print_help()
        sys.exit(1)
