# config.py
import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "leads.db"

# 2GIS Settings
BASE_URL = "https://2gis.kg" # Using .kg for Kyrgyzstan by default
SEARCH_URL_TEMPLATE = "{base}/{city}/search/{query}"

# Predefined Cities (Kyrgyzstan)
CITIES = {
    "bishkek": "Бишкек",
    "osh": "Ош",
    "jalal-abad": "Джалал-Абад",
    "karakol": "Каракол"
}

# Predefined Categories (for CLI menu)
CATEGORIES = [
    "Стоматологии",
    "Салоны красоты",
    "Кофейни",
    "Рестораны",
    "Строительные компании",
    "Фитнес-клубы",
    "Автосервисы"
]

# Selenium Settings
HEADLESS = True # Set to False for debugging
REQUEST_DELAY_SECONDS = 2
PAGE_LOAD_TIMEOUT = 15

# DataFrame Export Settings
EXPORT_DIR = BASE_DIR / "exports"
os.makedirs(EXPORT_DIR, exist_ok=True)
