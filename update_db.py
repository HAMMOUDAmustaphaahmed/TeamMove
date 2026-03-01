import pymysql

conn = pymysql.connect()

with conn:
    with conn.cursor() as cur:
        # List all tables
        cur.execute("SHOW TABLES")
        tables = [row[0] for row in cur.fetchall()]
        print(f"Tables found: {tables}\n")

        for table in tables:
            print(f"{'='*60}")
            print(f"TABLE: {table}")
            print(f"{'='*60}")

            # Full column info
            cur.execute(f"""
                SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT,
                       EXTRA, COLUMN_KEY
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """, (table,))
            cols = cur.fetchall()
            print(f"{'COLUMN':<25} {'TYPE':<30} {'NULL':<6} {'DEFAULT':<15} {'EXTRA':<20} {'KEY'}")
            print("-"*110)
            for c in cols:
                print(f"{str(c[0]):<25} {str(c[1]):<30} {str(c[2]):<6} {str(c[3]):<15} {str(c[4]):<20} {str(c[5])}")

            # Foreign keys
            cur.execute(f"""
                SELECT CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = %s
                  AND REFERENCED_TABLE_NAME IS NOT NULL
            """, (table,))
            fks = cur.fetchall()
            if fks:
                print("\nFOREIGN KEYS:")
                for fk in fks:
                    print(f"  {fk[0]}: {fk[1]} → {fk[2]}.{fk[3]}")
            print()