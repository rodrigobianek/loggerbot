import sqlite3
from config import DB_NAME

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    """Cria a tabela de logs de voz se não existir."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voice_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                channel_name TEXT NOT NULL,
                join_time TEXT NOT NULL,
                leave_time TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL
            )
        """)
        conn.commit()

def save_voice_session(user_name: str, channel_name: str, join_time, leave_time, duration_seconds: int):
    """Salva um registro de permanência em canal de voz."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO voice_logs (user_name, channel_name, join_time, leave_time, duration_seconds)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_name,
            channel_name,
            join_time.strftime("%Y-%m-%d %H:%M:%S"),
            leave_time.strftime("%Y-%m-%d %H:%M:%S"),
            duration_seconds
        ))
        conn.commit()

def get_logs_by_date(date_str: str):
    """Busca os registros de uma data específica (Formato: AAAA-MM-DD)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_name, channel_name, join_time, leave_time, duration_seconds
            FROM voice_logs
            WHERE DATE(join_time) = ?
            ORDER BY id DESC
        """, (date_str,))
        return cursor.fetchall()