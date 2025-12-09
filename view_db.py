import sqlite3
import sys
import os
from collections import defaultdict

# Add the parent directory to sys.path to import from owl_keys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from owl_keys.controls.utils import decimal_to_ascii

conn = sqlite3.connect("my_keybindings.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT * FROM keybindings")
rows = cur.fetchall()

if not rows:
    print("No keybindings found in database")
    conn.close()
    sys.exit(0)

# Group by game_exe
games = defaultdict(list)
for r in rows:
    row_dict = dict(r)
    # Convert key_code bytes to int and then to ASCII
    key_code_bytes = row_dict['key_code']
    key_code_int = int.from_bytes(key_code_bytes, 'little')
    key_name = decimal_to_ascii(key_code_int)
    
    games[row_dict['game_exe']].append({
        'key_name': key_name,
        'action': row_dict['action']
    })

# Print in neat format
for game_exe, bindings in games.items():
    print(f"\n{game_exe}:")
    for binding in bindings:
        print(f"  {binding['key_name']}: {binding['action']}")

conn.close()
