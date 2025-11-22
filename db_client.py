# db_client.py

import os
import sqlite3
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv

load_dotenv()

# Path to your SQLite DB file (override via .env if needed)
DB_PATH = os.getenv("SOCIAL_EVENTS_DB_PATH", "social_events.db")


class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass


def get_db_connection() -> sqlite3.Connection:
    """
    Open a new SQLite connection with Row factory so we can get dict-like rows.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        raise DatabaseError(f"Error connecting to database: {e}") from e


def fetch_social_events_by_name(event_name: str) -> List[Dict[str, Any]]:
    """
    Return all rows from the `social_events` table that match the given event_name.

    You can switch between exact match and partial match by changing the SQL.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # OPTION A: exact match
        # sql = "SELECT * FROM social_events WHERE event_name = ?"
        # params = (event_name,)

        # OPTION B: partial match (e.g. "%yoga%" will find "Evening Yoga Meetup")
        sql = "SELECT * FROM social_events WHERE event_name LIKE ?"
        params = (f"%{event_name}%",)

        cur.execute(sql, params)
        rows = cur.fetchall()

        # Convert sqlite3.Row → dict
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise DatabaseError(f"Error querying social_events: {e}") from e
    finally:
        conn.close()
