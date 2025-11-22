# setup_database.py
"""
Helper script to set up the SQLite database with sample data.
Run this once before starting the orchestrator.
"""

import sqlite3
from datetime import datetime, timedelta

DB_FILE = "user_data.db"


def setup_database():
    """Creates the database tables and populates with sample data."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create user_interests table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_interests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            interests TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create social_events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS social_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            date TEXT NOT NULL,
            location TEXT NOT NULL,
            interest_tag TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create conversations table (optional, for history)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            conversation_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert sample user interests
    cursor.execute("""
        INSERT OR IGNORE INTO user_interests (user_name, interests)
        VALUES (?, ?)
    """, ("Sagar", "wellness, hiking, tech meetups, meditation"))

    # Insert sample social events
    today = datetime.now()
    events = [
        ("Morning Yoga in the Park", (today + timedelta(days=2)).strftime('%Y-%m-%d'),
         "Central Park", "wellness", "Start your day with gentle yoga"),

        ("Tech Networking Mixer", (today + timedelta(days=5)).strftime('%Y-%m-%d'),
         "TechHub Downtown", "tech meetups", "Connect with local tech professionals"),

        ("Guided Meditation Session", (today + timedelta(days=3)).strftime('%Y-%m-%d'),
         "Zen Center", "meditation", "Evening mindfulness practice"),

        ("Weekend Hiking Group", (today + timedelta(days=6)).strftime('%Y-%m-%d'),
         "Mountain Trail", "hiking", "Moderate 5-mile hike with group"),

        ("Wellness Workshop", (today + timedelta(days=4)).strftime('%Y-%m-%d'),
         "Community Center", "wellness", "Learn stress management techniques"),
    ]

    for event in events:
        cursor.execute("""
            INSERT OR IGNORE INTO social_events 
            (event_name, date, location, interest_tag, description)
            VALUES (?, ?, ?, ?, ?)
        """, event)

    conn.commit()
    conn.close()

    print("✓ Database setup complete!")
    print(f"✓ Created tables: user_interests, social_events, conversations")
    print(f"✓ Added sample data for user 'Sagar'")
    print(f"✓ Added {len(events)} upcoming social events")


if __name__ == "__main__":
    setup_database()