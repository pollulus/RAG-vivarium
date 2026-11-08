"""Постраничное извлечение текста из книг.

Обрабатывает все PDF из data/books/source.
Результат: data/books/raw/<имя файла>.jsonl, одна строка JSON на страницу.
Книги, для которых файл уже есть, пропускаются.

Запуск из терминала:
    python -m src.books.extract
"""

import json
from pathlib import Path

import pymupdf

from src.config import BOOKS_RAW_DIR, BOOKS_SOURCE_DIR


def extract_pdf_pages(pdf_path: Path) -> list[dict]:
    """Достает текстовый слой каждой страницы PDF."""
    pages = []
    with pymupdf.open(pdf_path) as document:
        # Нумеруем с 1, чтобы номера совпадали с номерами в просмотрщике PDF
        for page_number, page in enumerate(document, start=1):
            pages.append({
                "book_id": pdf_path.stem,
                "page": page_number,
                "method": "text_layer",
                "text": page.get_text(),
            })
    return pages


def save_jsonl(records: list[dict], output_path: Path) -> None:
    """Сохраняет записи в JSONL: одна запись — одна строка."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output_file:
        for record in records:
            # ensure_ascii=False сохраняет русские буквы как есть, а не кодами \u0410
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")

def main() -> None:
    for pdf_path in BOOKS_SOURCE_DIR.glob("*.pdf"):
        output_path = BOOKS_RAW_DIR / f"{pdf_path.stem}.jsonl"
        # Пропускаем обработанные книги
        if output_path.exists():
            continue

        pages = extract_pdf_pages(pdf_path)
        save_jsonl(pages, output_path)

if __name__ == "__main__":
    main()