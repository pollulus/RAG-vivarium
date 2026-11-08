"""Постраничное извлечение текста из книг.

Обрабатывает все PDF и DjVu из data/books/source:
- из PDF берется текстовый слой;
- страницы DjVu распознаются через Tesseract (OCR).
Результат: data/books/raw/<имя файла>.jsonl, одна строка JSON на страницу.
Книги, для которых файл уже есть, пропускаются.

Запуск из корня проекта:
    python -m src.books.extract
"""

import io
import json
import subprocess
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image

from src.config import BOOKS_RAW_DIR, BOOKS_SOURCE_DIR

OCR_LANGUAGES = "rus+eng"

def extract_pdf_pages(pdf_path: Path) -> list[dict]:
    """Извлекает текстовый слой каждой страницы PDF."""
    pages = []
    with pymupdf.open(pdf_path) as document:
        # Нумеруем с 1, чтобы номера совпадали с номерами в просмотрщике
        for page_number, page in enumerate(document, start=1):
            pages.append({
                "book_id": pdf_path.stem,
                "page": page_number,
                "method": "text_layer",
                "text": page.get_text(),
            })
    return pages


def count_djvu_pages(djvu_path: Path) -> int:
    """Возвращает число страниц в DjVu, не работает без этого"""
    command = ["djvused", "-e", "n", str(djvu_path)]
    return int(subprocess.run(command, capture_output=True, text=True, check=True).stdout)


def render_djvu_page(djvu_path: Path, page_number: int) -> Image.Image:
    """Превращает страницу DjVu в картинку."""
    # "-" вместо имени выходного файла: ddjvu отдает картинку в программу
    # вместо сохранения на диск
    command = ["ddjvu", "-format=pnm", f"-page={page_number}", str(djvu_path), "-"]
    image_bytes = subprocess.run(command, capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(image_bytes))


def extract_djvu_pages(djvu_path: Path) -> list[dict]:
    """Распознает текст каждой страницы DjVu."""
    pages = []
    for page_number in range(1, count_djvu_pages(djvu_path) + 1):
        image = render_djvu_page(djvu_path, page_number)
        pages.append({
            "book_id": djvu_path.stem,
            "page": page_number,
            "method": "ocr",
            "text": pytesseract.image_to_string(image, lang=OCR_LANGUAGES),
        })
    return pages


def save_jsonl(records: list[dict], output_path: Path) -> None:
    """Сохраняет записи в JSONL: одна запись на одну строку."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output_file:
        for record in records:
            # ensure_ascii=False сохраняет русские буквы, а не коды \u0410
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    for book_path in BOOKS_SOURCE_DIR.iterdir():
        output_path = BOOKS_RAW_DIR / f"{book_path.stem}.jsonl"
        # Пропускает уже обработанные книги
        if output_path.exists():
            continue

        if book_path.suffix == ".pdf":
            pages = extract_pdf_pages(book_path)
        elif book_path.suffix == ".djvu":
            pages = extract_djvu_pages(book_path)
        else:
            continue
        save_jsonl(pages, output_path)


if __name__ == "__main__":
    main()