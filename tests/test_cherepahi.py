"""Тесты парсера cherepahi.ru на небольших страницах, собранных по образцу сайта."""

from src.parsers import cherepahi

ARTICLE_URL = "https://cherepahi.ru/soderzhanie/kormlenie"
SPECIES_URL = "https://cherepahi.ru/vidy-cherepax/trionychidae/apalone-ferox-zloj-trioniks"

ARTICLE_TEXT = (
    "<p>В природе черепахи сами выбирают подходящую для них еду в соответствии с местом "
    "и регионом обитания. В их рацион входит растительная и животная пища, а также "
    "минеральные вещества.</p>"
    "<p>В домашних условиях правильным питанием черепаху должен обеспечить ее хозяин. "
    "Сухопутных черепах кормят в основном растениями: одуванчиком, клевером, подорожником "
    "и салатами. Водным черепахам нужна рыба, креветки и улитки.</p>"
    "<p>Кальций и витамины дают отдельно: черепахам нужна сепия или кормовой мел, а "
    "ультрафиолетовая лампа помогает усваивать кальций.</p>"
)


def make_page(body: str, date: str | None = None, title: str = "Кормление черепах") -> str:
    """Страница в разметке, похожей на сайт: меню, статья, плашка про cookie."""
    date_meta = f'<meta property="article:published_time" content="{date}T10:00:00+03:00">' if date else ""
    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><title>{title}</title>
<meta property="og:title" content="{title}">{date_meta}</head>
<body>
<nav><a href="/soderzhanie">Содержание</a> <a href="/articles">Статьи</a> <a href="/tforum">Форум</a></nav>
<div class="item-page"><h1>{title}</h1>{body}</div>
<div class="cookies">Мы используем файлы cookie и аналогичные технологии для удобства сайта.</div>
</body></html>"""


class FakeFetcher:
    """Отдает заготовленные страницы и запоминает, что запрашивали."""

    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.requested_urls = []

    def get(self, url: str) -> str | None:
        self.requested_urls.append(url)
        return self.pages.get(url)


def test_normalize_url_removes_anchor_and_slash():
    assert cherepahi.normalize_url("https://cherepahi.ru/soderzhanie/kormlenie/#top") == ARTICLE_URL


def test_is_section_url_allows_only_three_sections():
    assert cherepahi.is_section_url(ARTICLE_URL)
    assert cherepahi.is_section_url("https://cherepahi.ru/articles/drugoe/yadovitost-u-cherepakh")
    assert cherepahi.is_section_url(SPECIES_URL)
    assert not cherepahi.is_section_url("https://cherepahi.ru/tforum/viewtopic")
    assert not cherepahi.is_section_url("https://cherepahi.ru/kpch/proekty-kpch")
    assert not cherepahi.is_section_url("https://example.com/soderzhanie/kormlenie")


def test_article_page_parsed_without_cookie_notice():
    article = cherepahi.parse_article_page(make_page(ARTICLE_TEXT, date="2022-09-29"), ARTICLE_URL)

    assert article["title"] == "Кормление черепах"
    assert article["date"] == "2022-09-29"
    assert article["section"] == "Содержание"
    assert article["rubric"] is None
    assert "одуванчиком" in article["text"]
    assert "cookie" not in article["text"]


def test_species_page_gets_rubric_from_address():
    page = make_page(ARTICLE_TEXT, date="2023-05-01", title="Apalone ferox (Злой трионикс)")
    article = cherepahi.parse_article_page(page, SPECIES_URL)

    assert article["section"] == "Виды черепах"
    assert article["rubric"] == "trionychidae"


def test_list_page_without_date_is_skipped():
    teasers = "<p>Описание видов черепах, места обитания.</p><p>Дополнительные статьи про содержание.</p>"
    page = make_page(teasers, title="Кормление")
    assert cherepahi.parse_article_page(page, "https://cherepahi.ru/articles/kormlenie") is None


def test_crawl_site_follows_only_section_links(monkeypatch):
    main_page = make_page('<a href="/soderzhanie">Содержание</a> <a href="/kpch">КПЧ</a>', title="Черепахи.ру")
    section_page = make_page(
        '<a href="/soderzhanie/kormlenie">Кормление</a>'
        '<a href="/soderzhanie/kormlenie?start=10">Дальше</a>'
        '<a href="https://example.com/soderzhanie/x">Чужой сайт</a>',
        title="Содержание",
    )
    fetcher = FakeFetcher({
        "https://cherepahi.ru": main_page,
        "https://cherepahi.ru/soderzhanie": section_page,
        ARTICLE_URL: make_page(ARTICLE_TEXT, date="2022-09-29"),
    })
    monkeypatch.setattr(cherepahi, "CHEREPAHI_SECTIONS", {"soderzhanie": "Содержание"})

    articles = cherepahi.crawl_site(fetcher)

    assert [article["url"] for article in articles] == [ARTICLE_URL]
    assert "https://cherepahi.ru/soderzhanie/kormlenie?start=10" in fetcher.requested_urls
    assert not any("tforum" in url or "kpch" in url or "example.com" in url for url in fetcher.requested_urls)
