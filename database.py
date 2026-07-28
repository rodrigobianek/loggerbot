import sqlite3
from datetime import datetime

DB_NAME = "activity_logs.db"

def init_db():
    """Cria as tabelas necessárias caso não existam."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabela para sessões de voz completas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voice_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            channel_name TEXT NOT NULL,
            join_time TEXT NOT NULL,
            leave_time TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL,
            date TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

def save_voice_session(user_name, channel_name, join_time, leave_time, duration_seconds):
    """Salva uma sessão finalizada de voz."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    date_str = join_time.strftime("%Y-%m-%d")
    
    cursor.execute('''
        INSERT INTO voice_logs (user_name, channel_name, join_time, leave_time, duration_seconds, date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        user_name,
        channel_name,
        join_time.strftime("%Y-%m-%d %H:%M:%S"),
        leave_time.strftime("%Y-%m-%d %H:%M:%S"),
        duration_seconds,
        date_str
    ))
    
    conn.commit()
    conn.close()

def get_logs_by_date(date_str):
    """Busca registros de uma data específica (Formato: YYYY-MM-DD)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_name, channel_name, join_time, leave_time, duration_seconds
        FROM voice_logs
        WHERE date = ?
        ORDER BY join_time ASC
    ''', (date_str,))
    
    rows = cursor.fetchall()
    conn.close()
    return rows