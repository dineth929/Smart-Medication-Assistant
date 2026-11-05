"""SQLite access layer for the Smart Medication Assistant."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

# Default location (desktop / tests). The app overrides this at startup with
# a writable per-user folder via set_db_path(), which is required on Android.
_db_path = Path(__file__).resolve().parent.parent / "medication.db"


def set_db_path(path):
    """Change the database file location. Call before initializing tables."""
    global _db_path
    _db_path = Path(path)


def get_db_path():
    return _db_path


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


@contextmanager
def get_connection():
    """Yield a connection that commits on success, rolls back on error,
    and is always closed afterwards."""
    connection = sqlite3.connect(_db_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS medications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                strength TEXT NOT NULL,
                instructions TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)


def initialize_schedule_table():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS schedule_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                medication_id INTEGER NOT NULL,
                scheduled_time TEXT NOT NULL,
                note TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (medication_id)
                    REFERENCES medications(id)
                    ON DELETE CASCADE
            )
        """)


def initialize_profile_table():
    """One-row table (id is always 1) holding the user's name and birthday."""
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name TEXT NOT NULL,
                birthday TEXT NOT NULL
            )
        """)


def personal_infor_read():
    """Return (name, birthday_iso). Raises KeyError if nothing is saved yet."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT name, birthday FROM profile WHERE id = 1"
        ).fetchone()
    if row is None:
        raise KeyError("profile")
    return row


def personal_infor_write(name, birthday_iso):
    """Insert or update the single profile row. birthday_iso is 'YYYY-MM-DD'."""
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO profile (id, name, birthday) VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE
                SET name = excluded.name, birthday = excluded.birthday
        """, (name, birthday_iso))


# ---------------------------------------------------------------------
# Medicine counts. `dose` is the number of pills counted at `updated_at`.
# ---------------------------------------------------------------------
def initialize_medicine_count_table():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS counts (
                name TEXT PRIMARY KEY,
                dose TEXT NOT NULL,
                updated_at TEXT,
                buy_marker TEXT
            )
        """)
        # Migration: older databases have no updated_at column.
        columns = [row[1] for row in
                   connection.execute("PRAGMA table_info(counts)")]
        if "updated_at" not in columns:
            connection.execute("ALTER TABLE counts ADD COLUMN updated_at TEXT")
        if "buy_marker" not in columns:
            connection.execute("ALTER TABLE counts ADD COLUMN buy_marker TEXT")
        connection.execute(
            "UPDATE counts SET updated_at = ? WHERE updated_at IS NULL",
            (_now_iso(),))
        # Repair old databases: keep only the newest row per name,
        # then enforce uniqueness even if the old table lacked a PRIMARY KEY.
        connection.execute("""
            DELETE FROM counts
            WHERE rowid NOT IN (SELECT MAX(rowid) FROM counts GROUP BY name)
        """)
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_counts_name ON counts(name)"
        )


def medicine_count_read():
    """Return (name, dose) rows."""
    with get_connection() as connection:
        return connection.execute(
            "SELECT name, dose FROM counts ORDER BY name"
        ).fetchall()


def medicine_count_dates():
    """Return {name: updated_at_iso}: when each count was last set."""
    with get_connection() as connection:
        return dict(connection.execute(
            "SELECT name, updated_at FROM counts").fetchall())


def medicine_count_write(name, dose):
    """Insert or replace a count and stamp it with the current time."""
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO counts (name, dose, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE
                SET dose = excluded.dose, updated_at = excluded.updated_at,
                    buy_marker = NULL
        """, (name, str(dose), _now_iso()))


def medicine_count_markers():
    """Return {name: buy_marker}: which 'time to buy' notice was already
    handled for each count (reset whenever the count is written)."""
    with get_connection() as connection:
        return dict(connection.execute(
            "SELECT name, buy_marker FROM counts").fetchall())


def medicine_count_set_marker(name, marker):
    with get_connection() as connection:
        connection.execute(
            "UPDATE counts SET buy_marker = ? WHERE name = ?", (marker, name))


def medicine_count_delete(name):
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM counts WHERE name = ?", (name,))
        return cursor.rowcount > 0