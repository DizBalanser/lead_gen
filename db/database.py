# db/database.py
import sqlite3
import pandas as pd
from typing import List, Dict, Optional
from core.models import Lead
from config import DB_PATH

def get_connection():
    """Возвращает соединение к SQLite БД."""
    return sqlite3.connect(str(DB_PATH))

def init_db():
    """Инициализация базы данных (создание таблицы 'leads')."""
    conn = get_connection()
    c = conn.cursor()
    # Таблица для хранения лидов
    c.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            external_id TEXT PRIMARY KEY,
            name TEXT,
            city TEXT,
            address TEXT,
            district TEXT,
            category TEXT,
            search_category TEXT,
            phone TEXT,
            email TEXT,
            website TEXT,
            instagram TEXT,
            rating REAL,
            review_count INTEGER,
            url TEXT,
            scraped_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_leads(leads: List[Lead]) -> int:
    """
    Сохраняет список лидов в БД (с дедупликацией по external_id).
    Возвращает количество добавленных/обновлённых записей.
    """
    if not leads:
        return 0
    
    init_db()
    
    # Преобразуем список датаклассов в список словарей, затем в DataFrame
    df_new = pd.DataFrame([lead.to_dict() for lead in leads])
    
    conn = get_connection()
    try:
        # Проверяем существующие ID для дедупликации, сохраняем только новые, 
        # или используем "ON CONFLICT REPLACE".
        # SQLite через Pandas to_sql не поддерживает UPSERT напрямую,
        # поэтому ручками или через временную таблицу.
        
        # Загружаем текущие ID
        existing_ids = pd.read_sql('SELECT external_id FROM leads', conn)['external_id'].tolist()
        
        # Фильтруем только новые
        df_to_insert = df_new[~df_new['external_id'].isin(existing_ids)]
        
        if not df_to_insert.empty:
            df_to_insert.to_sql('leads', conn, if_exists='append', index=False)
            
        return len(df_to_insert)
    finally:
        conn.close()

def load_leads() -> pd.DataFrame:
    """Загружает всю базу лидов в DataFrame."""
    init_db()
    conn = get_connection()
    try:
        df = pd.read_sql('SELECT * FROM leads', conn)
        return df
    finally:
        conn.close()

def get_db_stats() -> Dict[str, Any]:
    """Возвращает статистику базы данных."""
    df = load_leads()
    if df.empty:
        return {"total": 0}
    
    stats = {
        "total": len(df),
        "with_phone": df['phone'].notna().sum() if 'phone' in df.columns else 0,
        "with_email": df['email'].notna().sum() if 'email' in df.columns else 0,
        "with_instagram": df['instagram'].notna().sum() if 'instagram' in df.columns else 0,
        "by_city": df['city'].value_counts().to_dict() if 'city' in df.columns else {},
        "by_category": df['category'].value_counts().to_dict() if 'category' in df.columns else {}
    }
    return stats

def clear_db():
    """Очищает базу данных."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS leads')
    conn.commit()
    conn.close()
    init_db()
