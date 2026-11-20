"""Автоматическая чистка фиксированного корпуса из шести книг.

python -m src.books.clean inspect | clean | review
raw не изменяется. Автоматический результат сохраняется в data/books/auto_clean.
Проверенный итог лежит в data/books/clean и отдельно в «книги для чанкинга».
Повторный запуск не воспроизводит исправления сложной верстки этого итога.
Номера страниц корпуса сверены с исходниками; method описывает извлечение,
а не определяет, является ли издание сканом или цифровой книгой.
"""

import argparse
import html
import json
import random
import re
import sys
from difflib import get_close_matches

from src.config import BOOKS_RAW_DIR

BOOKS_CLEAN_DIR = BOOKS_RAW_DIR.parent / "clean"
BOOKS_AUTO_DIR = BOOKS_RAW_DIR.parent / "auto_clean"


def read_jsonl(path):
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


# В PDF Сергеенко шесть страниц переставлены.
SERGEENKO_PAGES = {32: 34, 33: 35, 34: 36, 35: 37, 36: 32, 37: 33}


def page_number(book_id, file_page):
    if book_id == "gurgiy_turtles":
        return file_page - 1
    if book_id == "sergeenko_turtles":
        return SERGEENKO_PAGES.get(file_page, file_page)
    return file_page


HEADERS = {
    "bauer_fish_illnesses": [
        "БОЛЕЗНИ АКВАРИУМНЫХ РЫБ", "НЕИНФЕКЦИОННЫЕ БОЛЕЗНИ", "ВИРУСЫ",
        "ПРОСТЕЙШИЕ (PROTOZOA)", "БАКТЕРИИ", "ГРИБКОВЫЕ ЗАБОЛЕВАНИЯ",
        "ПЛОСКИЕ ЧЕРВИ (PLATHELMINTES)", "CRUSTACEA (РАКООБРАЗНЫЕ)",
        "КИШЕЧНОПОЛОСТНЫЕ", "NEMATODA (НИТЕВИДНЫЕ ЧЕРВИ)",
        "АКАНТОЦЕФАЛЫ (ACANTHOCEPHALA, СКРЕБНИ)", "HIRUDINEA (ПИЯВКИ)",
        "ПРОФИЛАКТИКА ЗАБОЛЕВАНИЙ", "РАСПОЗНАВАНИЕ (ДИАГНОСТИРОВАНИЕ) БОЛЕЗНЕЙ",
        "МЕДИКАМЕНТЫ И ИХ ПРИМЕНЕНИЕ", "СРЕДСТВА ДЛЯ НАРКОЗА И ОБЕЗДВИЖИВАНИЯ",
        "ДЕЗИНФИЦИРУЮЩИЕ СРЕДСТВА",
    ],
    "sergeenko_turtles": ["ЧЕРЕПАХИ", "ЖИВОТНЫЕ В ВАШЕМ ДОМЕ"],
}
WATERMARK = re.compile(r"[a-z]*(?:firma|ftrma)|[зх25]оор[тг]+[аa]", re.I)


def clean_page_edges(text, book_id, number):
    lines = [re.sub(r"[ \t\u00a0]+", " ", line).strip() for line in text.splitlines()]
    nonempty = [i for i, line in enumerate(lines) if line]
    edges = set(nonempty[:2] + nonempty[-5:])
    for i, line in enumerate(lines):
        if len(line) < 65 and WATERMARK.search(line):
            lines[i] = ""
        elif i in edges and line.replace(" ", "").strip("—-*|` ") == str(number):
            lines[i] = ""
        elif i in nonempty[-5:] and re.fullmatch(r"(?:\d+\*?\s+Черепахи.*|\d+[*+])", line):
            lines[i] = ""
    first = next((i for i, line in enumerate(lines) if line), None)
    if first is not None:
        heading = lines[first].strip(" *.—").upper()
        if get_close_matches(heading, HEADERS.get(book_id, []), n=1, cutoff=0.85):
            lines[first] = ""
    return "\n".join(lines).strip()


COMPOUND_PREFIXES = {
    "юго", "северо", "светло", "темно", "желто", "черно", "красно", "серо",
    "сине", "зелено", "бледно", "ярко", "научно", "водно", "солоновато",
    "восточно", "западно", "бело", "голубовато", "золотисто", "оливково",
    "желтовато", "оранжево", "нежно", "серебристо", "кроваво",
}
PRONOUN_BASES = {
    "кто", "кого", "кому", "кем", "ком", "что", "чего", "чему", "чем",
    "какой", "какая", "какое", "какие", "какого", "какую", "какому",
    "каким", "какими", "каких", "каком", "как", "где", "куда", "откуда",
    "когда", "почему", "зачем", "чей", "чья", "чье", "чьи",
}
PLACE_PREFIXES = {"ла", "шри", "сан", "сен", "нью", "рио"}
WORD_WRAP = re.compile(r"([^\W\d_]{2,})-[ \t]*\n\s*([^\W\d_]+)", re.UNICODE)


def join_word(first, second):
    if first.islower() and second.isupper():
        second = second.lower()
    whole = first + second
    if whole.lower().startswith(("красноух", "черномор")):
        return whole
    if first.lower() in COMPOUND_PREFIXES and second.lower() == "до":
        return first + "- " + second
    keep_hyphen = (
        first.lower() in COMPOUND_PREFIXES
        or (first.lower() in PRONOUN_BASES and second.lower() in {"то", "либо", "нибудь"})
        or (first.lower() == "из" and second.lower() in {"за", "под"})
        or (first.lower() in PLACE_PREFIXES and second[0].isupper())
        or (first[0].isupper() and second[0].isupper() and not first.isupper())
    )
    return first + "-" + second if keep_hyphen else whole


def is_heading(line):
    words = line.split()
    return line.isupper() or (
        len(words) <= 3 and line[0].isupper() and len(line) < 55
        and not re.search(r"[,.;:!?\d]", line) and not line.endswith("-")
    )


def clean_text(text):
    text = html.unescape(text).translate({0x96: "–", 0x97: "—"})
    text = re.sub(r"[|`_]", "", text)
    text = text.replace("\u0451", "е").replace("\u0401", "Е")
    text = re.sub(r"\u00ad\s*\n\s*(?=\w)", "", text).replace("\u00ad", "")
    text = text.replace("\ufeff", "").replace("\u200b", "").replace("\u00a0", " ")
    text = text.replace("{", "(").replace("}", ")")
    text = re.sub(r"\b[a-z]*(?:firma|ftrma)\.\s*(?:ru|ти|ту)\b", "", text, flags=re.I)
    text = re.sub(r"Ошибка!\s*Закладка не\s*определена\.?", "", text)
    text = re.sub(r"(?<=\d)-\s*\n\s*(?=\d)", "-", text)
    text = WORD_WRAP.sub(lambda match: join_word(*match.groups()), text)
    result = []
    blank = False
    previous_line = ""
    for raw_line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if not line:
            blank = True
            continue
        if not re.search(r"\w", line):
            continue
        starts_list = bool(re.match(r"^(?:[—–•*-]\s|\d+[.)]\s)", line))
        separate = (not result or line.isupper() or starts_list
                    or (blank and is_heading(line))
                    or (blank and is_heading(previous_line) and not line[0].islower())
                    or (blank and re.search(r'[.!?:;][»"]?$', result[-1])))
        if separate:
            result.append(line)
        else:
            result[-1] += " " + line
        previous_line, blank = line, False
    return "\n\n".join(result)


# Небольшой словарь повторяющихся, однозначных ошибок; разовые правим отдельно.
OCR_REPLACEMENTS = {
    "помошью": "помощью", "болыной": "большой", "зто": "это",
    "болыших": "больших", "болышим": "большим", "болышое": "большое",
    "болышой": "большой", "болыше": "больше",
    "болыпой": "большой", "болыпое": "большое", "болыпие": "большие",
    "болыним": "большим", "болыними": "большими", "болыцим": "большим",
    "болыцими": "большими", "болыному": "большому", "болыном": "большом",
    "болынинство": "большинство", "болышинства": "большинства",
    "меныше": "меньше", "менышая": "меньшая", "меныпими": "меньшими",
    "помоши": "помощи", "помешение": "помещение", "мошный": "мощный",
    "маломошную": "маломощную", "фильгр": "фильтр", "фильгра": "фильтра",
    "влоль": "вдоль", "ллина": "длина", "ллиной": "длиной", "ллину": "длину",
    "волой": "водой", "вылеляется": "выделяется", "полойдет": "подойдет",
    "зтой": "этой", "зтого": "этого", "зтот": "этот", "зтих": "этих",
    "продизенфицировать": "продезинфицировать", "наразитов": "паразитов",
}


def fix_ocr(text):
    for wrong, correct in OCR_REPLACEMENTS.items():
        def replace_word(match):
            word = match[0]
            if word.isupper():
                return correct.upper()
            if word[0].isupper():
                return correct.capitalize()
            return correct
        pattern = r"(?<!\w)" + re.escape(wrong) + r"(?!\w)"
        text = re.sub(pattern, replace_word, text, flags=re.IGNORECASE)
    return text


def join_page_wraps(records):
    for left, right in zip(records, records[1:]):
        ending = re.search(r"([^\W\d_]{2,})-$", left["text"])
        beginning = re.match(r"([^\W\d_]+)\b", right["text"])
        if ending and beginning:
            left["text"] = left["text"][:ending.start()] + join_word(ending[1], beginning[1])
            right["text"] = right["text"][beginning.end():].lstrip()
        elif re.search(r"\d-$", left["text"]):
            number = re.match(r"\d+(?:[,.]\d+)?(?:°[CС])?", right["text"])
            if number:
                left["text"] += number[0]
                right["text"] = right["text"][number.end():].lstrip()


SERVICE_PAGES = {
    "bauer_fish_illnesses": set(range(1, 9)) | {176},
    "beily_aquariumist": set(range(1, 14)) | set(range(278, 282)),
    "gurgiy_turtles": {1, 2, 3, 4, 5, 140, 141, 142, 143, 144},
    "krasichkova_sliders": set(),
    "plonskiy_fish": {1, 2, 3, 4} | set(range(378, 410)),
    "sergeenko_turtles": {1, 2, 63, 64},
}

TABLE_PAGES = {"beily_aquariumist": {34, 35, 36, 37}, "gurgiy_turtles": {139}}


def clean_book(records, book_id):
    result = []
    for record in records:
        file_page = record["page"]
        if file_page in SERVICE_PAGES[book_id] | TABLE_PAGES.get(book_id, set()):
            continue
        number = page_number(book_id, file_page)
        text = clean_page_edges(record["text"], book_id, number)
        if book_id == "beily_aquariumist" and file_page == 38:
            text = text.partition("Глава 4 Поведение")[2]
            text = "Глава 4 Поведение\n\n" + text if text else record["text"]
        if book_id == "krasichkova_sliders" and file_page == 1:
            text = "Введение\n\n" + text.partition("Введение")[2]
        text = fix_ocr(clean_text(text))
        if text.strip():
            result.append({**record, "page": number, "text": text})
    result.sort(key=lambda record: record["page"])
    join_page_wraps(result)
    return [record for record in result if record["text"].strip()]


def show_page(raw, cleaned=None):
    if cleaned is None:
        record = random.choice([record for record in raw if record["text"]])
        print(f"\n{record['book_id']} — страница файла {record['page']}\n{record['text']}")
    else:
        record = random.choice(cleaned)
        source = next(item for item in raw
                      if page_number(item["book_id"], item["page"]) == record["page"])
        print(f"\n{record['book_id']} — page {record['page']}\nДО:\n{source['text']}")
        print("\nПОСЛЕ:\n" + record["text"])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Чистка и просмотр книг")
    parser.add_argument("mode", choices=["inspect", "clean", "review"])
    args = parser.parse_args()
    for path in sorted(BOOKS_RAW_DIR.glob("*.jsonl")):
        raw = read_jsonl(path)
        output = (BOOKS_AUTO_DIR if args.mode == "clean" else BOOKS_CLEAN_DIR) / path.name
        if args.mode == "clean":
            records = clean_book(raw, path.stem)
            pages = [record["page"] for record in records]
            if pages != sorted(set(pages)):
                raise ValueError(f"Повторяющиеся или неверные номера: {path.name}")
            BOOKS_AUTO_DIR.mkdir(parents=True, exist_ok=True)
            with output.open("w", encoding="utf-8") as file:
                for record in records:
                    file.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"{path.stem}: сохранено {len(records)} страниц.")
        else:
            show_page(raw, read_jsonl(output) if args.mode == "review" else None)


if __name__ == "__main__":
    main()
