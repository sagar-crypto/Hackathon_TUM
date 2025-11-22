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

    # ---------------------------
    # Core tables
    # ---------------------------

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

    # ---------------------------
    # NEW: wellness_questionnaire
    # ---------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wellness_questionnaire (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id             TEXT NOT NULL,
            entry_date          TEXT NOT NULL,            -- 'YYYY-MM-DD'
            mood_rating         INTEGER NOT NULL,         -- 1-10
            stress_rating       INTEGER NOT NULL,         -- 1-10 (higher = more stressed)
            energy_level        INTEGER NOT NULL,         -- 1-10
            sleep_quality       INTEGER NOT NULL,         -- 1-10
            social_interactions INTEGER NOT NULL,         -- 1-10 (how socially connected the day felt)
            free_text_note      TEXT,                     -- for sentiment analysis
            sentiment_score     REAL,                     -- -1.0..1.0 (optional)
            wellness_score      REAL                      -- 0..100 composite (optional)
        )
    """)
    # ---------------------------
    # NEW: apple_health_daily
    # ---------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apple_health_daily (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id              TEXT NOT NULL,
            date                 TEXT NOT NULL,      -- 'YYYY-MM-DD'
            steps                INTEGER NOT NULL,
            active_energy_kcal   REAL,
            sleep_hours          REAL,
            stand_hours          REAL,
            resting_hr           REAL,
            mindfulness_minutes  REAL
        )
    """)

    # ---------------------------
    # Insert sample user interests
    # ---------------------------
    cursor.execute("""
        INSERT OR IGNORE INTO user_interests (user_name, interests)
        VALUES (?, ?)
    """, ("Sagar", "wellness, hiking, tech meetups, meditation"))

    # ---------------------------
    # Insert sample social events (relative to today)
    # ---------------------------
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

    # ---------------------------
    # NEW: Insert dummy wellness_questionnaire + apple_health_daily
    # ---------------------------

    # For a nice graph, use the last 7 days (today-6 ... today)
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]  # oldest → newest

    # Dummy questionnaire data aligned with those 7 days
    questionnaire_rows = [
        # date, mood, stress, energy, sleep_quality, social_interactions, note
        (days[0], 6, 5, 6, 7, 6,
         "Feeling a bit tired but overall okay. Work was manageable today."),
        (days[1], 5, 7, 5, 6, 3,
         "Quite stressed about deadlines. Hard to relax in the evening."),
        (days[2], 7, 4, 7, 8, 7,
         "Had a nice walk and felt more relaxed. Day went better than expected."),
        (days[3], 4, 8, 4, 5, 2,
         "Very anxious and overwhelmed today, barely took any breaks."),
        (days[4], 6, 6, 6, 6, 5,
         "Average day. Not great, not terrible. Would like to sleep earlier."),
        (days[5], 8, 3, 8, 7, 8,
         "Productive and calm. Went for a run and cooked something nice."),
        (days[6], 7, 4, 7, 7, 6,
         "Feeling okay, a bit mentally tired but proud of this week."),
    ]

    # Clear old sample data for idempotent setup (optional but convenient)
    cursor.execute("DELETE FROM wellness_questionnaire WHERE user_id = ?", ("sagar",))
    cursor.execute("DELETE FROM apple_health_daily WHERE user_id = ?", ("sagar",))

    for date_dt, mood, stress, energy, sleep_q, social, note in questionnaire_rows:
        entry_date = date_dt.strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO wellness_questionnaire
            (user_id, entry_date, mood_rating, stress_rating, energy_level,
             sleep_quality, social_interactions, free_text_note, sentiment_score, wellness_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "sagar",
            entry_date,
            mood,
            stress,
            energy,
            sleep_q,
            social,
            note,
            None,   # sentiment_score to be filled later by analysis
            None    # wellness_score to be computed later
        ))

    # Dummy Apple Health aggregates aligned to same 7 days
    health_rows = [
        # date, steps, active_kcal, sleep_hours, stand_hours, resting_hr, mindfulness_min
        (days[0],  6500, 420.0, 7.0, 11.0, 64.0,  5.0),
        (days[1],  3200, 280.0, 6.0,  9.0, 70.0,  0.0),
        (days[2],  9000, 520.0, 7.5, 12.0, 62.0, 10.0),
        (days[3],  2500, 230.0, 5.5,  8.0, 72.0,  0.0),
        (days[4],  6000, 400.0, 6.5, 10.0, 66.0,  5.0),
        (days[5], 11000, 650.0, 7.0, 13.0, 60.0, 15.0),
        (days[6],  8000, 500.0, 7.0, 11.0, 63.0,  8.0),
    ]

    for date_dt, steps, kcal, sleep_h, stand_h, hr, mindful_min in health_rows:
        date_str = date_dt.strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO apple_health_daily
            (user_id, date, steps, active_energy_kcal, sleep_hours,
             stand_hours, resting_hr, mindfulness_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "sagar",
            date_str,
            steps,
            kcal,
            sleep_h,
            stand_h,
            hr,
            mindful_min
        ))

    conn.commit()
    conn.close()

    print("✓ Database setup complete!")
    print(f"✓ Created tables: user_interests, social_events, conversations, "
          f"wellness_questionnaire, apple_health_daily")
    print(f"✓ Added sample data for user 'Sagar'")
    print(f"✓ Added {len(events)} upcoming social events")
    print("✓ Added 7 days of wellness_questionnaire + apple_health_daily data for 'sagar'")


if __name__ == "__main__":
    setup_database()
