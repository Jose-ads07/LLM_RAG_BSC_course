import os
import sqlite3
from datetime import datetime
from typing import Dict, List


DATABASE_PATH = os.getenv("DATABASE_PATH", "data/easy_chatgpt.db")


def get_connection():
    return sqlite3.connect(DATABASE_PATH)


def init_database():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    connection.commit()
    connection.close()


def save_message(role: str, content: str):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO messages (role, content, created_at)
        VALUES (?, ?, ?)
        """,
        (role, content, datetime.utcnow().isoformat())
    )

    connection.commit()
    connection.close()


def load_messages() -> List[Dict[str, str]]:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT role, content
        FROM messages
        ORDER BY id ASC
        """
    )

    rows = cursor.fetchall()
    connection.close()

    return [
        {
            "role": role,
            "content": content
        }
        for role, content in rows
    ]


def clear_messages():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM messages")

    connection.commit()
    connection.close()
