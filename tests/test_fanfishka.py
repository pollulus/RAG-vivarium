"""Тесты парсера fanfishka.ru на сохраненных страницах форума."""

import json
from pathlib import Path

import pytest

from src.parsers import fanfishka
from src.parsers.http import SiteUnavailableError

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "fanfishka"
TOPIC_URL = "https://fanfishka.ru/forum/topic/666-zapusk-akvariuma-voprosy-novichka/"


def read_fixture(file_name: str) -> str:
    return (FIXTURES_DIR / file_name).read_text(encoding="utf-8")


class FakeFetcher:
    """Отдает сохраненные страницы вместо скачивания."""

    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.requested_urls = []

    def get(self, url: str) -> str | None:
        self.requested_urls.append(url)
        return self.pages.get(url)


def test_make_clean_url_removes_page_and_query():
    assert fanfishka.make_clean_url(f"{TOPIC_URL}?page=2") == TOPIC_URL
    assert fanfishka.make_clean_url(f"{TOPIC_URL}?page=2/") == TOPIC_URL
    assert fanfishka.make_clean_url(TOPIC_URL.rstrip("/")) == TOPIC_URL


def test_second_topic_page_has_clean_topic_url():
    topic = fanfishka.parse_topic_page(read_fixture("topic_page2.html"), f"{TOPIC_URL}?page=2")
    assert topic["topic_url"] == TOPIC_URL
    assert topic["topic_id"] == 666
    assert topic["next_url"] == f"{TOPIC_URL}?page=3"
    assert len(topic["posts"]) > 0


def test_topic_title_and_section():
    topic = fanfishka.parse_topic_page(read_fixture("topic_page2.html"), f"{TOPIC_URL}?page=2")
    assert topic["topic_title"] == "Запуск аквариума - вопросы новичка"
    assert topic["section"] == "Запуск, перезапуск и обустройство аквариума"
    assert topic["section_path"][-1] == topic["section"]


def test_posts_have_iso_dates_and_clean_text():
    topic = fanfishka.parse_topic_page(read_fixture("topic.html"), "https://fanfishka.ru/forum/topic/23081-pervyy-akvarium/")
    assert len(topic["posts"]) == 19
    for post in topic["posts"]:
        assert post["date"].endswith("Z") and "T" in post["date"]
        assert post["text"]
        assert "сказал(а)" not in post["text"]


def test_new_style_quote_gives_reply_to_on_same_page():
    topic = fanfishka.parse_topic_page(read_fixture("topic.html"), "https://fanfishka.ru/forum/topic/23081-pervyy-akvarium/")
    post_ids = {post["post_id"] for post in topic["posts"]}
    replies = [post for post in topic["posts"] if post["reply_to"]]
    assert replies
    assert all(post["reply_to"] in post_ids for post in replies)


def test_legacy_quotes_removed_and_date_of_quoted_post_saved():
    topic = fanfishka.parse_topic_page(read_fixture("topic_old_quotes.html"), TOPIC_URL)
    posts = {post["post_id"]: post for post in topic["posts"]}
    assert all("Цитата " not in post["text"] for post in posts.values())
    assert posts["14975"]["text"].startswith("Большинство африканские цихлид")
    assert posts["14975"]["reply_to"] is None  # у старых цитат номера нет


def test_section_page_topics_and_pinned():
    section_url = "https://fanfishka.ru/forum/forum/35-zapusk-perezapusk-i-obustroystvo-akvariuma/"
    page = fanfishka.parse_section_page(read_fixture("section.html"), section_url)
    assert len(page["topics"]) == 35
    assert sum(topic["pinned"] for topic in page["topics"]) == 4
    assert page["topics"][0]["url"] == TOPIC_URL
    assert page["topics"][0]["pinned"]
    assert page["subsections"] == []
    assert page["next_url"].endswith("?page=2")


def test_container_section_has_subsections_and_no_topics():
    page = fanfishka.parse_section_page(
        read_fixture("forum_parent.html"),
        "https://fanfishka.ru/forum/forum/4-akvarium-dlya-nachinayuschih-sovety-pomosch-razreshenie-problem/",
    )
    assert page["topics"] == []
    ids = [fanfishka.get_section_id(subsection["url"]) for subsection in page["subsections"]]
    assert ids == [35, 36, 37]


def test_tetra_section_has_thirteen_subsections():
    page = fanfishka.parse_section_page(read_fixture("forum_tetra.html"), "https://fanfishka.ru/forum/forum/78-kompaniya-tetra/")
    assert len(page["subsections"]) == 13
    assert page["subsections"][0]["title"].startswith("Новости, акции")


def test_crawl_topic_post_types_and_records(monkeypatch):
    fetcher = FakeFetcher({
        TOPIC_URL: read_fixture("topic_old_quotes.html"),
        f"{TOPIC_URL}?page=2": read_fixture("topic_page2.html"),
    })
    records = fanfishka.crawl_topic(fetcher, TOPIC_URL, section_id=35, max_pages=2)

    assert [record["post_type"] for record in records].count("question") == 1
    assert records[0]["post_type"] == "question"
    assert len({record["post_id"] for record in records}) == len(records)
    for record in records:
        assert record["topic_url"] == TOPIC_URL
        assert "?page" not in record["post_url"]
        assert record["post_url"] == f"{TOPIC_URL}?do=findComment&comment={record['post_id']}"
        assert record["section_id"] == 35
        assert isinstance(record["has_photos"], bool)
        assert record["is_pinned"] is False


def test_save_jsonl_writes_final_file_without_temp(tmp_path):
    output_path = tmp_path / "sub" / "35.jsonl"
    fanfishka.save_jsonl([{"text": "привет"}], output_path)
    assert output_path.read_text(encoding="utf-8") == '{"text": "привет"}\n'
    assert not (tmp_path / "sub" / "35.jsonl.tmp").exists()


def test_main_collects_subsections_and_skips_finished_sections(monkeypatch, tmp_path):
    parent_url = "https://fanfishka.ru/forum/forum/4-akvarium-dlya-nachinayuschih-sovety-pomosch-razreshenie-problem/"
    section_url = "https://fanfishka.ru/forum/forum/35-zapusk-perezapusk-i-obustroystvo-akvariuma/"
    pages = {
        parent_url: read_fixture("forum_parent.html"),
        section_url: read_fixture("section.html"),
    }
    # Любая тема раздела отдает одну и ту же сохраненную страницу
    section_page = fanfishka.parse_section_page(pages[section_url], section_url)
    for topic in section_page["topics"]:
        pages[topic["url"]] = read_fixture("topic_old_quotes.html")
    fetcher = FakeFetcher(pages)
    monkeypatch.setattr(fanfishka, "PoliteFetcher", lambda site_url: fetcher)
    monkeypatch.setattr(fanfishka, "FORUMS_RAW_DIR", tmp_path)
    monkeypatch.setattr(fanfishka, "FANFISHKA_SECTIONS", {parent_url: 3})
    monkeypatch.setattr(fanfishka, "MAX_PAGES_PER_TOPIC", 1)
    monkeypatch.setattr("sys.argv", ["fanfishka"])

    fanfishka.main()

    output_dir = tmp_path / "fanfishka"
    # Подраздел 35 получил лимит родителя: 3 темы
    topic_ids = {record["topic_id"] for record in map(json.loads, (output_dir / "35.jsonl").open(encoding="utf-8"))}
    assert len(topic_ids) <= 3
    # Контейнер без тем получил пустой файл, раздел 35 (найден как подраздел) собран;
    # 36 и 37 в тесте не загрузились и файлов не получили
    assert (output_dir / "4.jsonl").read_text(encoding="utf-8") == ""
    assert (output_dir / "35.jsonl").stat().st_size > 0
    assert not (output_dir / "36.jsonl").exists()
    assert not list(output_dir.glob("*.tmp"))

    # Повторный запуск не трогает готовые файлы
    modified = (output_dir / "35.jsonl").stat().st_mtime_ns
    fanfishka.main()
    assert (output_dir / "35.jsonl").stat().st_mtime_ns == modified


def test_is_news_or_promo_checks_word_start():
    assert fanfishka.is_news_or_promo("Акция Tetra: скидка 20%")
    assert fanfishka.is_news_or_promo("Новинки Sera 2025 года")
    assert fanfishka.is_news_or_promo("Конкурсная работа: один день из жизни аквариума")
    assert fanfishka.is_news_or_promo("Новости, акции, мастер-классы компании Tetra")
    assert not fanfishka.is_news_or_promo("Реакция рыб на Sera Baktopur")
    assert not fanfishka.is_news_or_promo("Внутренний фильтр AquaEl перестал работать")


def make_section_page(topics: list[dict]) -> dict:
    return {"topics": topics, "subsections": [], "next_url": None}


def fake_crawl_topic(fetcher, topic_url, section_id, max_pages, is_pinned=False):
    """Вместо скачивания темы возвращает одну запись с параметрами вызова."""
    return [{"topic_url": topic_url, "max_pages": max_pages, "is_pinned": is_pinned}]


def test_crawl_section_skips_news_and_pinned_topics(monkeypatch):
    topics = [
        {"url": "https://fanfishka.ru/forum/topic/1-pravila/", "title": "Правила раздела", "pinned": True},
        {"url": "https://fanfishka.ru/forum/topic/2-novinki/", "title": "Новинки AquaEl 2025", "pinned": False},
        {"url": "https://fanfishka.ru/forum/topic/3-filtr/", "title": "Фильтр AquaEl гудит", "pinned": False},
        {"url": "https://fanfishka.ru/forum/topic/4-reakciya/", "title": "Реакция рыб на кондиционер", "pinned": False},
    ]
    monkeypatch.setattr(fanfishka, "parse_section_page", lambda html, page_url: make_section_page(topics))
    monkeypatch.setattr(fanfishka, "crawl_topic", fake_crawl_topic)
    monkeypatch.setattr(fanfishka, "PINNED_TOPICS_TO_KEEP", set())

    records = fanfishka.crawl_section(FakeFetcher({}), "https://fanfishka.ru/forum/forum/16-x/", "<html></html>", max_topics=10)

    assert [record["topic_url"] for record in records] == [
        "https://fanfishka.ru/forum/topic/3-filtr/",
        "https://fanfishka.ru/forum/topic/4-reakciya/",
    ]


def test_crawl_section_keeps_listed_pinned_topic_outside_limit(monkeypatch):
    topics = [
        {"url": "https://fanfishka.ru/forum/topic/1-pravila/", "title": "Правила раздела", "pinned": True},
        {"url": "https://fanfishka.ru/forum/topic/5-koryagi/", "title": "Коряги для аквариума", "pinned": True},
        {"url": "https://fanfishka.ru/forum/topic/6-vopros/", "title": "Мутная вода", "pinned": False},
        {"url": "https://fanfishka.ru/forum/topic/7-vopros/", "title": "Рыбки у поверхности", "pinned": False},
    ]
    monkeypatch.setattr(fanfishka, "parse_section_page", lambda html, page_url: make_section_page(topics))
    monkeypatch.setattr(fanfishka, "crawl_topic", fake_crawl_topic)
    monkeypatch.setattr(fanfishka, "PINNED_TOPICS_TO_KEEP", {"https://fanfishka.ru/forum/topic/5-koryagi/"})

    records = fanfishka.crawl_section(FakeFetcher({}), "https://fanfishka.ru/forum/forum/36-x/", "<html></html>", max_topics=1)

    assert records == [
        {"topic_url": "https://fanfishka.ru/forum/topic/5-koryagi/", "max_pages": 1, "is_pinned": True},
        {"topic_url": "https://fanfishka.ru/forum/topic/6-vopros/", "max_pages": 3, "is_pinned": False},
    ]


def test_crawl_section_takes_all_pinned_in_brand_sections(monkeypatch):
    topics = [
        {"url": "https://fanfishka.ru/forum/topic/8-tetra-ex/", "title": "Фильтры Tetra EX: отзывы и вопросы", "pinned": True},
        {"url": "https://fanfishka.ru/forum/topic/9-tetra-in/", "title": "Фильтр Tetra IN plus: отзывы и вопросы", "pinned": True},
    ]
    monkeypatch.setattr(fanfishka, "parse_section_page", lambda html, page_url: make_section_page(topics))
    monkeypatch.setattr(fanfishka, "crawl_topic", fake_crawl_topic)
    monkeypatch.setattr(fanfishka, "PINNED_TOPICS_TO_KEEP", set())

    records = fanfishka.crawl_section(
        FakeFetcher({}), "https://fanfishka.ru/forum/forum/136-filtry-tetra/", "<html></html>",
        max_topics=10, take_all_pinned=True,
    )

    assert [record["topic_url"] for record in records] == [topic["url"] for topic in topics]
    assert all(record["max_pages"] == 1 for record in records)


def test_main_skips_news_subsection(monkeypatch, tmp_path):
    tetra_url = "https://fanfishka.ru/forum/forum/78-kompaniya-tetra/"
    fetcher = FakeFetcher({tetra_url: read_fixture("forum_tetra.html")})
    monkeypatch.setattr(fanfishka, "PoliteFetcher", lambda site_url: fetcher)
    monkeypatch.setattr(fanfishka, "FORUMS_RAW_DIR", tmp_path)
    monkeypatch.setattr(fanfishka, "FANFISHKA_SECTIONS", {tetra_url: 10})
    monkeypatch.setattr("sys.argv", ["fanfishka"])

    fanfishka.main()

    assert len(fetcher.requested_urls) == 13  # раздел Tetra и 12 подразделов
    assert not any("novosti-akcii" in url for url in fetcher.requested_urls)


def test_photo_only_first_post_does_not_make_answer_a_question():
    html = f"""
    <link rel="canonical" href="{TOPIC_URL}">
    <article id="elComment_1"><time datetime="2026-01-01T10:00:00Z"></time>
      <div data-role="commentContent"><p><img class="ipsImage" src="photo.jpg"></p></div>
    </article>
    <article id="elComment_2"><time datetime="2026-01-01T11:00:00Z"></time>
      <div data-role="commentContent"><p>Похоже на ихтиофтириоз, поднимите температуру.</p></div>
    </article>
    """
    records = fanfishka.crawl_topic(FakeFetcher({TOPIC_URL: html}), TOPIC_URL, section_id=91, max_pages=1)

    assert len(records) == 1
    assert records[0]["post_id"] == "2"
    assert records[0]["post_type"] == "answer"


def test_edit_notice_removed_from_text():
    html = (
        '<div data-role="commentContent"><p>Грелку ставлю на 25 градусов.</p>'
        '<span><strong>Изменено <time>11 июля</time> пользователем user1</strong></span></div>'
    )
    content = fanfishka.parse_html(html).div
    assert fanfishka.clean_post_text(content) == "Грелку ставлю на 25 градусов."


def make_post_content(html: str):
    return fanfishka.parse_html(f'<div data-role="commentContent">{html}</div>').div


def test_nested_quotes_removed_when_outer_quote_is_from_another_topic():
    content = make_post_content(
        '<blockquote class="ipsQuote" data-ipsquote-contentid="1" data-ipsquote-contentcommentid="10">'
        '<blockquote class="ipsQuote" data-ipsquote-contentid="1" data-ipsquote-contentcommentid="5">'
        "<p>самое старое</p></blockquote><p>ответ на старое</p></blockquote>"
        "<p>Мой ответ на оба сообщения.</p>"
    )
    assert fanfishka.pop_quotes(content, topic_id=666) is None
    assert fanfishka.clean_post_text(content) == "Мой ответ на оба сообщения."


def test_nested_quote_gives_reply_to_of_outer_quote():
    content = make_post_content(
        '<blockquote class="ipsQuote" data-ipsquote-contentid="666" data-ipsquote-contentcommentid="10">'
        '<blockquote class="ipsQuote" data-ipsquote-contentid="666" data-ipsquote-contentcommentid="5">'
        "<p>старое</p></blockquote><p>ответ</p></blockquote><p>Мой ответ.</p>"
    )
    assert fanfishka.pop_quotes(content, topic_id=666) == "10"


def test_nested_legacy_quotes_removed_without_error():
    content = make_post_content(
        '<div><div><b>Цитата</b> Имя</div><div style="border:1px inset;">'
        '<div><div><b>Цитата</b> Другой</div><div style="border:1px inset;">старое</div></div>'
        "ответ на старое</div></div><p>Мой ответ.</p>"
    )
    fanfishka.pop_quotes(content, topic_id=666)
    assert fanfishka.clean_post_text(content) == "Мой ответ."


def test_crawl_section_skips_topic_that_raises_and_continues(monkeypatch):
    topics = [
        {"url": "https://fanfishka.ru/forum/topic/1-a/", "title": "Первая тема", "pinned": False},
        {"url": "https://fanfishka.ru/forum/topic/2-b/", "title": "Вторая тема", "pinned": False},
        {"url": "https://fanfishka.ru/forum/topic/3-c/", "title": "Третья тема", "pinned": False},
    ]

    def crawl_topic_with_one_error(fetcher, topic_url, section_id, max_pages, is_pinned=False):
        if "2-b" in topic_url:
            raise ValueError("необычная страница")
        return [{"topic_url": topic_url}]

    monkeypatch.setattr(fanfishka, "parse_section_page", lambda html, page_url: make_section_page(topics))
    monkeypatch.setattr(fanfishka, "crawl_topic", crawl_topic_with_one_error)

    records = fanfishka.crawl_section(FakeFetcher({}), "https://fanfishka.ru/forum/forum/16-x/", "<html></html>", max_topics=10)

    assert [record["topic_url"] for record in records] == [topics[0]["url"], topics[2]["url"]]


def test_crawl_section_does_not_hide_unavailable_site(monkeypatch):
    topics = [{"url": "https://fanfishka.ru/forum/topic/1-a/", "title": "Первая тема", "pinned": False}]

    def crawl_topic_site_down(fetcher, topic_url, section_id, max_pages, is_pinned=False):
        raise SiteUnavailableError("5 неудач подряд")

    monkeypatch.setattr(fanfishka, "parse_section_page", lambda html, page_url: make_section_page(topics))
    monkeypatch.setattr(fanfishka, "crawl_topic", crawl_topic_site_down)

    with pytest.raises(SiteUnavailableError):
        fanfishka.crawl_section(FakeFetcher({}), "https://fanfishka.ru/forum/forum/16-x/", "<html></html>", max_topics=10)
