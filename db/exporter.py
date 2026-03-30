# db/exporter.py
import pandas as pd
from datetime import datetime
from config import EXPORT_DIR

def export_to_csv(df: pd.DataFrame, filename_prefix: str = "leads") -> str:
    """Экспорт DataFrame в CSV файл."""
    if df.empty:
        return ""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{filename_prefix}_{timestamp}.csv"
    filepath = EXPORT_DIR / filename
    
    df.to_csv(filepath, index=False, encoding='utf-8-sig') # utf-8-sig для Excel
    return str(filepath)

def export_to_excel(df: pd.DataFrame, filename_prefix: str = "leads") -> str:
    """Экспорт DataFrame в Excel файл (.xlsx)."""
    if df.empty:
        return ""
        
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{filename_prefix}_{timestamp}.xlsx"
    filepath = EXPORT_DIR / filename
    
    df.to_excel(filepath, index=False, engine='openpyxl')
    return str(filepath)
