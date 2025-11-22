# database.py
import sqlite3
import os

DB_FILE = "user_data.db"
CONVERSATION_DIR = "conversations"


def setup_database():
    """Initializes the SQLite database with user interests and social events."""
    print("Setting up database...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 1. User Interests Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_interests (
            user_name TEXT PRIMARY KEY,
            interests TEXT
        )
    """)
    # Example data: user 'Sagar' from your original file
    cursor.execute("INSERT OR IGNORE INTO user_interests VALUES (?, ?)",
                   ("Sagar", "hiking, tech meetups, abstract painting"))

    # 2. Social Events Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS social_events (
            id INTEGER PRIMARY KEY,
            interest_tag TEXT,
            event_name TEXT,
            date TEXT,
            location TEXT
        )
    """)

    # Example events
    events = [
        ("hiking", "Local Trail Group Hike", "2025-12-01", "City Park"),
        ("tech meetups", "AI & Wellness Conference", "2025-11-29", "Digital Hub"),
        ("abstract painting", "Beginners Abstract Workshop", "2025-12-05", "Art Studio 42"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO social_events (interest_tag, event_name, date, location) VALUES (?, ?, ?, ?)", events)

    conn.commit()
    conn.close()
    print("Database setup complete.")


def ensure_conversation_dir():
    """Ensures the directory for conversation history exists."""
    os.makedirs(CONVERSATION_DIR, exist_ok=True)
    print(f"Conversation directory '{CONVERSATION_DIR}' ensured.")


def save_conversation(user_name: str, summary: str):
    """Saves the conversation summary to a text file."""
    file_path = os.path.join(CONVERSATION_DIR, f"{user_name}_history.txt")
    with open(file_path, "a") as f:
        f.write(f"\n--- Session Summary ({os.path.basename(file_path)}) ---\n")
        f.write(summary)
    print(f"Conversation saved to {file_path}")


# Run setup on module import
setup_database()
ensure_conversation_dir()