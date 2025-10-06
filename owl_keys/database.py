import sqlite3
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class KeybindingDatabase:
    """Database for storing game keybindings indexed by hardware ID and game executable."""

    def __init__(self, db_path: str = "keybindings.db"):
        """Initialize database connection and create tables if needed.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Create keybindings table and indexes if they don't exist."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS keybindings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hw_id TEXT NOT NULL,
                game_exe TEXT NOT NULL,
                key_code INTEGER NOT NULL,
                action TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(hw_id, game_exe, key_code)
            )
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hw_game
            ON keybindings(hw_id, game_exe)
        """)

        self.conn.commit()

    def combo_exists(self, hw_id: str, game_exe: str) -> bool:
        """Check if a hardware ID + game executable combo already exists.

        Args:
            hw_id: Hardware identifier
            game_exe: Game executable name

        Returns:
            True if combo exists in database, False otherwise
        """
        self.cursor.execute(
            "SELECT 1 FROM keybindings WHERE hw_id = ? AND game_exe = ? LIMIT 1",
            (hw_id, game_exe)
        )
        return self.cursor.fetchone() is not None

    def insert_keybindings(self, hw_id: str, game_exe: str, bindings: Dict[int, str]):
        """Insert keybindings for a hardware ID + game executable combo.

        Args:
            hw_id: Hardware identifier
            game_exe: Game executable name
            bindings: Dictionary mapping key codes (int) to actions (str)
        """
        self.cursor.executemany(
            "INSERT OR IGNORE INTO keybindings (hw_id, game_exe, key_code, action) VALUES (?, ?, ?, ?)",
            [(hw_id, game_exe, key_code, action) for key_code, action in bindings.items()]
        )
        self.conn.commit()

    def get_keybindings(self, hw_id: str, game_exe: str) -> Dict[int, str]:
        """Get all keybindings for a hardware ID + game executable combo.

        Args:
            hw_id: Hardware identifier
            game_exe: Game executable name

        Returns:
            Dictionary mapping key codes to actions
        """
        self.cursor.execute(
            "SELECT key_code, action FROM keybindings WHERE hw_id = ? AND game_exe = ?",
            (hw_id, game_exe)
        )
        return dict(self.cursor.fetchall())

    def get_all_combos(self) -> List[Tuple[str, str]]:
        """Get all unique hardware ID + game executable combinations.

        Returns:
            List of (hw_id, game_exe) tuples
        """
        self.cursor.execute(
            "SELECT DISTINCT hw_id, game_exe FROM keybindings ORDER BY hw_id, game_exe"
        )
        return self.cursor.fetchall()

    def update_keybinding(self, hw_id: str, game_exe: str, key_code: int, action: str):
        """Update a specific keybinding.

        Args:
            hw_id: Hardware identifier
            game_exe: Game executable name
            key_code: Key code to update
            action: New action for this key
        """
        self.cursor.execute(
            "INSERT OR REPLACE INTO keybindings (hw_id, game_exe, key_code, action) VALUES (?, ?, ?, ?)",
            (hw_id, game_exe, key_code, action)
        )
        self.conn.commit()

    def delete_combo(self, hw_id: str, game_exe: str):
        """Delete all keybindings for a hardware ID + game executable combo.

        Args:
            hw_id: Hardware identifier
            game_exe: Game executable name
        """
        self.cursor.execute(
            "DELETE FROM keybindings WHERE hw_id = ? AND game_exe = ?",
            (hw_id, game_exe)
        )
        self.conn.commit()

    @staticmethod
    def compute_hash(hw_id: str, game_exe: str) -> str:
        """Compute MD5 hash for a hardware ID + game executable combo.

        Args:
            hw_id: Hardware identifier
            game_exe: Game executable name

        Returns:
            MD5 hash string
        """
        return hashlib.md5(f"{hw_id}:{game_exe}".encode()).hexdigest()

    def close(self):
        """Close database connection."""
        self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Example usage
if __name__ == "__main__":
    # Create database
    with KeybindingDatabase("keybindings.db") as db:
        # Example data
        hw_id = "hw123"
        game_exe = "valorant.exe"

        # Check if combo exists
        if not db.combo_exists(hw_id, game_exe):
            print(f"Processing new combo: {hw_id} + {game_exe}")

            # Insert keybindings (from VLM output)
            bindings = {
                87: "move_forward",    # W key
                65: "move_left",       # A key
                83: "move_backward",   # S key
                68: "move_right",      # D key
                32: "jump",            # Space
                16: "crouch"           # Shift
            }
            db.insert_keybindings(hw_id, game_exe, bindings)
            print("Keybindings inserted")
        else:
            print(f"Combo already exists, skipping video processing")
            bindings = db.get_keybindings(hw_id, game_exe)
            print(f"Existing bindings: {bindings}")

        # Get all combos
        print("\nAll combos in database:")
        for combo in db.get_all_combos():
            print(f"  {combo[0]} + {combo[1]}")
