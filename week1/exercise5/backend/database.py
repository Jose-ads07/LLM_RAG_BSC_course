import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional


DATABASE_PATH = os.getenv("DATABASE_PATH", "data/easy_chatgpt.db")


def get_connection():
    return sqlite3.connect(DATABASE_PATH)


def now_iso() -> str:
    return datetime.utcnow().isoformat()


def init_database():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
        """
    )

    connection.commit()
    connection.close()


def create_conversation(title: str = "New chat") -> int:
    connection = get_connection()
    cursor = connection.cursor()

    created_at = now_iso()

    cursor.execute(
        """
        INSERT INTO conversations (title, created_at, updated_at)
        VALUES (?, ?, ?)
        """,
        (title, created_at, created_at)
    )

    conversation_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return conversation_id


def get_latest_conversation_id() -> Optional[int]:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM conversations
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """
    )

    row = cursor.fetchone()
    connection.close()

    if row is None:
        return None

    return row[0]


def get_or_create_latest_conversation_id() -> int:
    conversation_id = get_latest_conversation_id()

    if conversation_id is None:
        return create_conversation()

    return conversation_id


def list_conversations() -> List[Dict[str, str]]:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, title, created_at, updated_at
        FROM conversations
        ORDER BY updated_at DESC, id DESC
        """
    )

    rows = cursor.fetchall()
    connection.close()

    return [
        {
            "id": row[0],
            "title": row[1],
            "created_at": row[2],
            "updated_at": row[3],
        }
        for row in rows
    ]


def load_messages(conversation_id: int) -> List[Dict[str, str]]:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT role, content
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id ASC
        """,
        (conversation_id,)
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


def save_message(conversation_id: int, role: str, content: str):
    connection = get_connection()
    cursor = connection.cursor()

    created_at = now_iso()

    cursor.execute(
        """
        INSERT INTO messages (conversation_id, role, content, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (conversation_id, role, content, created_at)
    )

    cursor.execute(
        """
        UPDATE conversations
        SET updated_at = ?
        WHERE id = ?
        """,
        (created_at, conversation_id)
    )

    connection.commit()
    connection.close()


def update_conversation_title(conversation_id: int, title: str):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE conversations
        SET title = ?, updated_at = ?
        WHERE id = ?
        """,
        (title, now_iso(), conversation_id)
    )

    connection.commit()
    connection.close()


def clear_conversation(conversation_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM messages
        WHERE conversation_id = ?
        """,
        (conversation_id,)
    )

    connection.commit()
    connection.close()
