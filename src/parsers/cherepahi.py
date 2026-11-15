"""Парсер статей сайта cherepahi.ru.

Начинает с главной страницы и ходит по ссылкам внутри трех разделов:
содержание, статьи и виды черепах. Текст статьи достает trafilatura.
Страницы-списки рубрик не сохраняются: у них нет даты публикации.
Результат: data/sites/raw/cherepahi.jsonl, одна строка на статью.

Запуск из корня проекта:
    python -m src.parsers.cherepahi
"""

import json
import logging
import re
from collections import deque
from urllib.parse import urljoin, urlparse

import trafilatura
from bs4 import BeautifulSoup

from src.config import CHEREPAHI_SECTIONS, CHEREPAHI_URL, MIN_ARTICLE_CHARS, SITES_RAW_DIR
from src.parsers.http import PoliteFetcher, SiteUnavailableError
from src.parsers.storage import save_jsonl

logger = logging.getLogger(__name__)

SOURCE = "cherepahi.ru"
# Плашка про cookie попадает в текст некоторых страниц
COOKIE_NOTICE = re.compile(r"^Мы используем файлы cookie.*$", re.MULTILINE)


def normalize_url(url: str) -> str:
    """Адрес без якоря и слэша на конце."""
    return url.split("#")[0].rstrip("/")


def is_section_url(url: str) -> bool:
    """Страница cherepahi.ru из одного из трех нужных разделов."""
    parts = urlparse(url)
    section_slug = parts.path.strip("/").split("/")[0]
    return parts.netloc == SOURCE and section_slug in CHEREPAHI_SECTIONS


def extract_links(html: str, page_url: str) -> list[str]:
    """Ссылки со страницы на другие страницы нужных разделов."""
    soup = BeautifulSoup(html, "html.parser")
    links = [normalize_url(urljoin(page_url, link["href"])) for link in soup.find_all("a", href=True)]
    return [link for link in links if is_section_url(link)]


def parse_article_page(html: str, url: str) -> dict | None:
    """Разбирает страницу. Возвращает статью или None, если это список рубрики."""
    extracted = trafilatura.extract(html, url=url, output_format="json", with_metadata=True)
    if extracted is None:
        return None
    data = json.loads(extracted)
    text = COOKIE_NOTICE.sub("", data["text"]).strip()
    if data.get("date") is None or len(text) < MIN_ARTICLE_CHARS:
        return None

    path_parts = urlparse(url).path.strip("/").split("/")
    return {
        "source": SOURCE,
        "section": CHEREPAHI_SECTIONS[path_parts[0]],
        # Рубрика из адреса: kormlenie, testudinidae и т.п.
        "rubric": path_parts[1] if len(path_parts) > 2 else None,
        "url": url,
        "title": data.get("title"),
        "date": data["date"],
        "text": text,
    }


def crawl_site(fetcher: PoliteFetcher) -> list[dict]:
    """Обходит разделы сайта по ссылкам и собирает статьи."""
    start_url = normalize_url(CHEREPAHI_URL)
    queue = deque([start_url])
    seen_urls = {start_url}
    articles = []

    while queue:
        url = queue.popleft()
        html = fetcher.get(url)
        if html is None:
            continue
        for link in extract_links(html, url):
            if link not in seen_urls:
                seen_urls.add(link)
                queue.append(link)

        # Главная страница нужна только ради ссылок
        if is_section_url(url):
            article = parse_article_page(html, url)
            if article is not None:
                articles.append(article)
                logger.info("статья %d: %s", len(articles), article["title"])
    return articles


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    output_path = SITES_RAW_DIR / "cherepahi.jsonl"
    if output_path.exists():
        logger.info("Файл уже есть: %s", output_path)
        return
    try:
        articles = crawl_site(PoliteFetcher(CHEREPAHI_URL))
    except SiteUnavailableError as error:
        logger.error("Сайт недоступен (%s), файл не сохранен", error)
        return
    save_jsonl(articles, output_path)
    logger.info("Сохранено статей: %d -> %s", len(articles), output_path)


if __name__ == "__main__":
    main()
