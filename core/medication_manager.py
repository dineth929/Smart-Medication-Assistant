from datetime import datetime

from core.database import get_connection


def add_medicine(name, strength, instructions=""):
    name = name.strip()
    strength = strength.strip()
    instructions = instructions.strip()

    if not name or not strength:
        raise ValueError("Name and strength are required.")

    with get_connection() as connection:
        connection.execute("""
            INSERT INTO medications (name, strength, instructions, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            name,
            strength,
            instructions,
            datetime.now().isoformat(timespec="seconds"),
        ))


def get_all_medicines():
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT id, name, strength, instructions "
            "FROM medications ORDER BY id DESC"
        )
        return cursor.fetchall()


def get_medicine(medicine_id):
    with get_connection() as connection:
        cursor = connection.execute("""
            SELECT id, name, strength, instructions, created_at
            FROM medications
            WHERE id = ?
        """, (medicine_id,))
        return cursor.fetchone()


def update_medicine(medicine_id, name, strength, instructions=""):
    name = name.strip()
    strength = strength.strip()
    instructions = instructions.strip()

    if not name or not strength:
        raise ValueError("Name and strength are required.")

    with get_connection() as connection:
        cursor = connection.execute("""
            UPDATE medications
            SET name = ?, strength = ?, instructions = ?
            WHERE id = ?
        """, (name, strength, instructions, medicine_id))
        return cursor.rowcount > 0


def delete_medicine(medicine_id):
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM medications WHERE id = ?", (medicine_id,)
        )
        return cursor.rowcount > 0
