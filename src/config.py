"""Настройки проекта: пути к папкам и значения из файла .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Корень проекта: папка на уровень выше src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Для результатов парсинга
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Исходные файлы книг и извлеченный из них текст
BOOKS_SOURCE_DIR = DATA_DIR / "books" / "source"
BOOKS_RAW_DIR = DATA_DIR / "books" / "raw"

# Переменные из .env
load_dotenv(PROJECT_ROOT / ".env")

GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
