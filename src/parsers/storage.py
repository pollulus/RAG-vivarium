"""Сохранение результатов парсинга."""

import json
from pathlib import Path


def save_jsonl(records: list[dict], output_path: Path) -> None:
    """Сохраняет записи в JSONL: одна запись на одну строку."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Сначала временный файл: готовый файл появляется только когда все собрано
    temp_path = output_path.with_name(output_path.name + ".tmp")
    with temp_path.open("w", encoding="utf-8") as output_file:
        for record in records:
            # ensure_ascii=False сохраняет русские буквы, а не коды А
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
    temp_path.replace(output_path)
