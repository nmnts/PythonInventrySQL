import os
import sqlite3

CONFIG_DIR = 'config'
LOCALDB_FILE = os.path.join(CONFIG_DIR, 'localdb.sqlite')

if os.path.exists(LOCALDB_FILE):
    conn = sqlite3.connect(LOCALDB_FILE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(sell_history)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'cost_price' not in columns:
        cursor.execute("ALTER TABLE sell_history ADD COLUMN cost_price REAL DEFAULT 0")
        conn.commit()
        print('Added cost_price column to sell_history.')
    else:
        print('cost_price column already exists in sell_history.')
    conn.close()
else:
    print('localdb.sqlite does not exist.') 