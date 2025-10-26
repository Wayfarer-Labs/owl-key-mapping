import sqlite3

conn = sqlite3.connect("keybindings.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT * FROM keybindings")
rows = cur.fetchall()

if rows:
    print("Columns:", list(rows[0].keys()))
else:
    print("Columns: (no rows)")

for r in rows:
    print(dict(r))

conn.close()
