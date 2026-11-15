"""Парсер форума fanfishka.ru (Invision Community).

Из каждого раздела FANFISHKA_SECTIONS и его подразделов берет свежие темы,
а из тем сообщения. Закрепленные темы берутся только у производителей и из
списка PINNED_TOPICS_TO_KEEP. Цитаты убираются из текста, номер цитируемого
сообщения сохраняется в reply_to.
Результат: data/forums/raw/fanfishka/<id раздела>.jsonl, одна строка на
сообщение. Уже собранные разделы пропускаются.

Запуск из корня проекта:
    python -m src.parsers.fanfishka
    python -m src.parsers.fanfishka --max-topics 10   # пробный запуск: по 10 тем
"""

import argparse
import json
import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from src.config import (
    FANFISHKA_SECTIONS,
    FANFISHKA_URL,
    FORUMS_RAW_DIR,
    MAX_PAGES_PER_PINNED_TOPIC,
    MAX_PAGES_PER_TOPIC,
    PINNED_TOPICS_TO_KEEP,
    SKIP_TITLE_WORDS,
    TAKE_ALL_PINNED_SECTIONS,
)
from src.parsers.http import PoliteFetcher, SiteUnavailableError
from src.parsers.storage import save_jsonl

logger = logging.getLogger(__name__)

SOURCE = "fanfishka.ru"

# В старых сообщениях (с прежнего форума) цитата это блок с рамкой
LEGACY_QUOTE_BOX = 'div[style*="border:1px inset"]'
# Подпись форума внутри сообщения: "Изменено 11 июля пользователем <ник>"
EDIT_NOTICE = re.compile(r"^Изменено .+ пользователем .+$", re.MULTILINE)

# \b перед словом: "акци" находит "Акция", но не "Реакция"
SKIP_TITLE_PATTERN = re.compile(r"\b(" + "|".join(SKIP_TITLE_WORDS) + ")", re.IGNORECASE)


def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def make_clean_url(url: str) -> str:
    """Адрес без параметров и якоря, со слэшем на конце."""
    return url.split("?")[0].split("#")[0].rstrip("/") + "/"


def get_section_id(url: str) -> int | None:
    match = re.search(r"/forum/forum/(\d+)-", url)
    return int(match.group(1)) if match else None


def get_topic_id(url: str) -> int | None:
    match = re.search(r"/topic/(\d+)-", url)
    return int(match.group(1)) if match else None


def get_next_url(soup: BeautifulSoup, page_url: str) -> str | None:
    """Адрес следующей страницы списка тем или темы."""
    link = soup.find("link", rel="next")
    return urljoin(page_url, link["href"]) if link and link.get("href") else None


def get_breadcrumbs(soup: BeautifulSoup) -> list[str]:
    """Хлебные крошки без "Главная". На странице их два набора, берем первый."""
    breadcrumbs = soup.select_one('ul[data-role="breadcrumbList"]')
    if breadcrumbs is None:
        return []
    names = [item.get_text(" ", strip=True) for item in breadcrumbs.find_all("li")]
    return [name for name in names if name and name != "Главная"]


def is_news_or_promo(title: str) -> bool:
    """Новость или акция компании, а не вопрос: такие темы и подразделы пропускаем."""
    return SKIP_TITLE_PATTERN.search(title) is not None


def parse_section_page(html: str, page_url: str) -> dict:
    """Разбирает страницу раздела: темы, подразделы и следующая страница."""
    soup = parse_html(html)

    topics = []
    for row in soup.select("li.ipsDataItem[data-rowid]"):
        for link in row.select('h4.ipsDataItem_title a[href*="/topic/"]'):
            # Ссылки с page= это мини-пагинация внутри заголовка
            if "page=" in link["href"]:
                continue
            topics.append({
                "url": make_clean_url(urljoin(page_url, link["href"])),
                "title": link.get_text(" ", strip=True),
                "pinned": row.select_one(".fa-thumb-tack") is not None,
            })
            break

    subsections = []
    for row in soup.select("li.cForumRow[data-forumid]"):
        link = row.select_one('h4 a[href*="/forum/forum/"]')
        if link:
            subsections.append({
                "url": make_clean_url(urljoin(page_url, link["href"])),
                "title": link.get_text(" ", strip=True),
            })

    return {
        "topics": topics,
        "subsections": subsections,
        "next_url": get_next_url(soup, page_url),
    }


def pop_quotes(content: Tag, topic_id: int | None) -> str | None:
    """Удаляет цитаты из сообщения и возвращает номер первого цитируемого сообщения."""
    # Сначала находим все цитаты и только потом удаляем: после удаления внешней
    # цитаты вложенные в нее пустеют, и читать их уже нельзя
    outer_quotes = [
        quote for quote in content.select("blockquote.ipsQuote")
        if quote.find_parent("blockquote") is None
    ]
    legacy_quotes = []
    for box in content.select(LEGACY_QUOTE_BOX):
        label = box.parent.find("b")
        if label is not None and label.get_text(strip=True) == "Цитата":
            legacy_quotes.append(box.parent)

    reply_to = None
    for quote in outer_quotes:
        if quote.get("data-ipsquote-contentid") == str(topic_id):
            reply_to = quote.get("data-ipsquote-contentcommentid")
            break

    for quote in outer_quotes + legacy_quotes:
        if not quote.decomposed:  # вложенная старая цитата уже исчезла вместе с внешней
            quote.decompose()
    return reply_to


def has_photos(content: Tag) -> bool:
    """Есть ли в сообщении фото (смайлики и значки не считаются)."""
    return bool(
        content.select("img.ipsImage, a.ipsAttachLink_image")
        or content.select('img[src*="/_fr/"]')
    )


def clean_post_text(content: Tag) -> str:
    """Текст сообщения, абзацы разделены пустой строкой."""
    for tag in content.find_all(["p", "div", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6"]):
        tag.insert_before("\n")
        tag.insert_after("\n")
    text = re.sub(r"[ \t\u00a0\ufeff]+", " ", content.get_text())
    text = re.sub(r"\s*\n\s*", "\n\n", text).strip()
    return EDIT_NOTICE.sub("", text).strip()


def parse_topic_page(html: str, page_url: str) -> dict:
    """Разбирает страницу темы: заголовок, раздел, сообщения, следующая страница."""
    soup = parse_html(html)

    title = None
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "", strict=False)
        except ValueError:
            continue
        if isinstance(data, dict) and data.get("@type") == "DiscussionForumPosting":
            title = data.get("headline") or data.get("name")
            break

    # На второй и дальше страницах canonical содержит ?page=N, его убираем
    topic_url = make_clean_url(soup.find("link", rel="canonical")["href"])
    topic_id = get_topic_id(topic_url)

    breadcrumbs = get_breadcrumbs(soup)
    if breadcrumbs and breadcrumbs[-1] == title:
        breadcrumbs = breadcrumbs[:-1]  # последняя крошка это сама тема

    posts = []
    for article_index, article in enumerate(soup.select('article[id^="elComment_"]')):
        content = article.select_one('[data-role="commentContent"]')
        if content is None:
            continue
        post_id = article["id"].split("_", 1)[1]
        time_tag = article.find("time")
        reply_to = pop_quotes(content, topic_id)
        text = clean_post_text(content)
        if not text:  # в сообщении была одна цитата или одно фото
            continue
        posts.append({
            "post_id": post_id,
            "date": time_tag.get("datetime") if time_tag else None,
            "reply_to": reply_to,
            "has_photos": has_photos(content),
            "text": text,
            # Если первое сообщение было одним фото, вопросом не должен стать первый ответ
            "is_first_on_page": article_index == 0,
        })

    return {
        "topic_id": topic_id,
        "topic_title": title,
        "topic_url": topic_url,
        "section": breadcrumbs[-1] if breadcrumbs else None,
        "section_path": breadcrumbs,
        "posts": posts,
        "next_url": get_next_url(soup, page_url),
    }


def crawl_topic(
    fetcher: PoliteFetcher,
    topic_url: str,
    section_id: int,
    max_pages: int,
    is_pinned: bool = False,
) -> list[dict]:
    """Скачивает первые страницы темы и возвращает записи по сообщениям."""
    posts = []
    topic = None
    url = topic_url
    for page_number in range(1, max_pages + 1):
        html = fetcher.get(url)
        if html is None:
            break
        topic = parse_topic_page(html, url)
        for post in topic["posts"]:
            is_first_post = page_number == 1 and post["is_first_on_page"]
            post["post_type"] = "question" if is_first_post else "answer"
        posts.extend(topic["posts"])
        url = topic["next_url"]
        if url is None:
            break

    if topic is None:
        return []

    return [
        {
            "source": SOURCE,
            "section_id": section_id,
            "section": topic["section"],
            "section_path": topic["section_path"],
            "topic_id": topic["topic_id"],
            "topic_title": topic["topic_title"],
            "topic_url": topic["topic_url"],
            "post_id": post["post_id"],
            "post_url": f"{topic['topic_url']}?do=findComment&comment={post['post_id']}",
            "post_type": post["post_type"],
            "is_pinned": is_pinned,
            "date": post["date"],
            "reply_to": post["reply_to"],
            "has_photos": post["has_photos"],
            "text": post["text"],
        }
        for post in posts
    ]


def crawl_section(
    fetcher: PoliteFetcher,
    section_url: str,
    first_page_html: str,
    max_topics: int,
    take_all_pinned: bool = False,
) -> list[dict]:
    """Собирает сообщения из свежих тем раздела.

    Закрепленные темы в лимит max_topics не входят: берутся только нужные
    из них, а лимит относится к обычным темам.
    """
    section_id = get_section_id(section_url)
    records = []
    seen_topic_urls = set()
    regular_topics_count = 0
    page_url = section_url
    html = first_page_html

    while html is not None and regular_topics_count < max_topics:
        page = parse_section_page(html, page_url)
        for topic in page["topics"]:
            if regular_topics_count >= max_topics:
                break
            if topic["url"] in seen_topic_urls or is_news_or_promo(topic["title"]):
                continue
            if topic["pinned"]:
                if not take_all_pinned and topic["url"] not in PINNED_TOPICS_TO_KEEP:
                    continue
                max_pages = MAX_PAGES_PER_PINNED_TOPIC
                logger.info("  закрепленная тема: %s", topic["title"])
            else:
                regular_topics_count += 1
                max_pages = MAX_PAGES_PER_TOPIC
                logger.info("  тема %d/%d: %s", regular_topics_count, max_topics, topic["title"])
            seen_topic_urls.add(topic["url"])
            try:
                records.extend(crawl_topic(fetcher, topic["url"], section_id, max_pages, topic["pinned"]))
            except SiteUnavailableError:
                raise
            except Exception:
                # Одна необычная страница не должна обрывать многочасовой сбор
                logger.exception("Тема пропущена из-за ошибки: %s", topic["url"])

        page_url = page["next_url"]
        html = fetcher.get(page_url) if page_url else None
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Парсер форума fanfishka.ru")
    parser.add_argument(
        "--max-topics",
        type=int,
        help="брать из каждого раздела столько тем вместо чисел из config.py",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    output_dir = FORUMS_RAW_DIR / "fanfishka"
    # Очередь: адрес раздела, сколько обычных тем брать, брать ли все закрепленные
    pending = [
        (make_clean_url(url), args.max_topics or max_topics, url in TAKE_ALL_PINNED_SECTIONS)
        for url, max_topics in FANFISHKA_SECTIONS.items()
    ]
    visited = set()

    try:
        fetcher = PoliteFetcher(FANFISHKA_URL)
        while pending:
            section_url, max_topics, take_all_pinned = pending.pop(0)
            if section_url in visited:
                continue
            visited.add(section_url)

            first_page_html = fetcher.get(section_url)
            if first_page_html is None:
                continue
            # Подраздел получает настройки родительского раздела
            for subsection in parse_section_page(first_page_html, section_url)["subsections"]:
                if not is_news_or_promo(subsection["title"]):
                    pending.append((subsection["url"], max_topics, take_all_pinned))

            output_path = output_dir / f"{get_section_id(section_url)}.jsonl"
            if output_path.exists():
                continue
            logger.info("Раздел: %s", section_url)
            records = crawl_section(fetcher, section_url, first_page_html, max_topics, take_all_pinned)
            save_jsonl(records, output_path)
            logger.info("Сохранено сообщений: %d -> %s", len(records), output_path)
    except SiteUnavailableError as error:
        logger.error("Сайт недоступен (%s). Собранные разделы сохранены.", error)


if __name__ == "__main__":
    main()
