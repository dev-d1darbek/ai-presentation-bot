"""
SQLite Database for User Tracking and Admin Analytics.
Stores user interactions, presentation generation logs, and statistics.
"""
import sqlite3
import os
import time
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "bot.db")

def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes tables if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS generations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        topic TEXT,
        slide_count INTEGER,
        design_id TEXT,
        format TEXT DEFAULT 'pptx',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def log_user(user_id: int, username: Optional[str] = None, first_name: Optional[str] = None):
    """Logs or updates user activity."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO users (user_id, username, first_name, last_active)
    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(user_id) DO UPDATE SET
        username=coalesce(?, users.username),
        first_name=coalesce(?, users.first_name),
        last_active=CURRENT_TIMESTAMP
    """, (user_id, username, first_name, username, first_name))
    conn.commit()
    conn.close()

def log_generation(user_id: int, topic: str, slide_count: int, design_id: str, format_type: str = "pptx"):
    """Logs presentation generation."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO generations (user_id, topic, slide_count, design_id, format)
    VALUES (?, ?, ?, ?, ?)
    """, (user_id, topic, slide_count, design_id, format_type))
    conn.commit()
    conn.close()

def get_admin_stats() -> Dict[str, Any]:
    """Retrieves aggregated statistics for /admin dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total and today's users
    cursor.execute("SELECT count(*) as total FROM users")
    total_users = cursor.fetchone()["total"]

    cursor.execute("SELECT count(*) as today FROM users WHERE date(last_active) = date('now')")
    users_today = cursor.fetchone()["today"]

    # Total and today's generations
    cursor.execute("SELECT count(*) as total FROM generations")
    total_generations = cursor.fetchone()["total"]

    cursor.execute("SELECT count(*) as today FROM generations WHERE date(created_at) = date('now')")
    generations_today = cursor.fetchone()["today"]

    # Top 5 Themes
    cursor.execute("""
    SELECT design_id, count(*) as count
    FROM generations
    GROUP BY design_id
    ORDER BY count DESC
    LIMIT 5
    """)
    top_themes = [dict(row) for row in cursor.fetchall()]

    # Top 5 Slide counts
    cursor.execute("""
    SELECT slide_count, count(*) as count
    FROM generations
    GROUP BY slide_count
    ORDER BY count DESC
    LIMIT 5
    """)
    top_slide_counts = [dict(row) for row in cursor.fetchall()]

    # Last 10 Generations
    cursor.execute("""
    SELECT g.topic, g.slide_count, g.design_id, g.format, g.created_at, u.first_name, u.username
    FROM generations g
    LEFT JOIN users u ON g.user_id = u.user_id
    ORDER BY g.id DESC
    LIMIT 10
    """)
    recent_generations = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "total_users": total_users,
        "users_today": users_today,
        "total_generations": total_generations,
        "generations_today": generations_today,
        "top_themes": top_themes,
        "top_slide_counts": top_slide_counts,
        "recent_generations": recent_generations,
    }

def get_all_user_ids() -> List[int]:
    """Returns all user IDs for broadcasting announcements."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    user_ids = [row["user_id"] for row in cursor.fetchall()]
    conn.close()
    return user_ids
