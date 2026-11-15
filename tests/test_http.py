"""Тесты загрузчика страниц: пауза из robots.txt, повторы, недоступный сайт."""

from pathlib import Path

import pytest
import requests

from src.parsers import http
from src.parsers.http import PoliteFetcher, SiteUnavailableError


class FakeResponse:
    def __init__(self, status_code: int = 200, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


def make_session_get(responses: dict):
    """Подменяет Session.get: ответ или исключение по адресу."""
    def fake_get(self, url, timeout=None, verify=True):
        answer = responses.get(url, FakeResponse(404))
        if isinstance(answer, Exception):
            raise answer
        return answer
    return fake_get


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(http.time, "sleep", lambda seconds: None)


def test_crawl_delay_from_robots_overrides_default(monkeypatch):
    robots = FakeResponse(200, "User-agent: *\nCrawl-delay: 10\n")
    monkeypatch.setattr(requests.Session, "get", make_session_get({"https://x.ru/robots.txt": robots}))
    assert PoliteFetcher("https://x.ru/").delay == 10


def test_get_returns_html_none_for_404_and_respects_robots(monkeypatch):
    responses = {
        "https://x.ru/robots.txt": FakeResponse(200, "User-agent: *\nDisallow: /closed\n"),
        "https://x.ru/a": FakeResponse(200, "<html>ok</html>"),
    }
    monkeypatch.setattr(requests.Session, "get", make_session_get(responses))
    fetcher = PoliteFetcher("https://x.ru/")
    assert fetcher.get("https://x.ru/a") == "<html>ok</html>"
    assert fetcher.get("https://x.ru/missing") is None
    assert fetcher.get("https://x.ru/closed/page") is None  # запрещено robots.txt


def test_site_unavailable_after_consecutive_failures(monkeypatch):
    responses = {"https://x.ru/robots.txt": FakeResponse(404)}
    for number in range(10):
        responses[f"https://x.ru/{number}"] = requests.ConnectionError("нет связи")
    monkeypatch.setattr(requests.Session, "get", make_session_get(responses))
    fetcher = PoliteFetcher("https://x.ru/")
    with pytest.raises(SiteUnavailableError):
        for number in range(10):
            assert fetcher.get(f"https://x.ru/{number}") is None


def test_cherepahi_robots_gives_ten_second_delay(monkeypatch):
    robots_text = (Path(__file__).parent / "fixtures" / "robots_cherepahi.txt").read_text(encoding="utf-8")
    responses = {"https://cherepahi.ru/robots.txt": FakeResponse(200, robots_text)}
    monkeypatch.setattr(requests.Session, "get", make_session_get(responses))
    assert PoliteFetcher("https://cherepahi.ru/").delay == 10


def test_robots_unreachable_means_site_unavailable(monkeypatch):
    responses = {"https://x.ru/robots.txt": requests.ConnectionError("нет связи")}
    monkeypatch.setattr(requests.Session, "get", make_session_get(responses))
    with pytest.raises(SiteUnavailableError):
        PoliteFetcher("https://x.ru/")
