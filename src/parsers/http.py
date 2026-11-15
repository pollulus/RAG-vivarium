"""Вежливая загрузка страниц: robots.txt, пауза между запросами, повторы."""

import logging
import time
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import requests
import urllib3

from src.config import (
    MAX_CONSECUTIVE_FAILURES,
    REQUEST_DELAY_SECONDS,
    REQUEST_RETRIES,
    REQUEST_TIMEOUT_SECONDS,
    USER_AGENT,
)

logger = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SiteUnavailableError(Exception):
    """Сайт не отвечает: слишком много неудач подряд."""


class PoliteFetcher:
    """Скачивает страницы одного сайта, соблюдая его robots.txt."""

    def __init__(self, site_url: str) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.failures = 0
        self.robots = self.load_robots(urljoin(site_url, "/robots.txt"))
        # Если сайт просит паузу больше нашей, берем его паузу
        self.delay = max(REQUEST_DELAY_SECONDS, self.robots.crawl_delay(USER_AGENT) or 0)

    def load_robots(self, robots_url: str) -> RobotFileParser:
        try:
            response = self.session.get(
                robots_url,
                timeout=REQUEST_TIMEOUT_SECONDS,
                verify=False,
            )
        except requests.RequestException as error:
            raise SiteUnavailableError(f"{robots_url}: {error}") from error
        robots = RobotFileParser()
        robots.parse(response.text.splitlines() if response.status_code == 200 else [])
        return robots

    def get(self, url: str) -> str | None:
        """Возвращает HTML страницы или None, если страницу получить не удалось."""
        if not self.robots.can_fetch(USER_AGENT, url):
            logger.info("robots.txt запрещает: %s", url)
            return None

        for attempt in range(1, REQUEST_RETRIES + 1):
            try:
                response = self.session.get(
                    url,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                    verify=False,
                )
            except requests.RequestException as error:
                logger.warning(
                    "Ошибка запроса (попытка %s/%s) %s: %s",
                    attempt, REQUEST_RETRIES, url, error,
                )
                self.failures += 1
                if self.failures >= MAX_CONSECUTIVE_FAILURES:
                    raise SiteUnavailableError(
                        f"Слишком много неудач подряд, последний URL: {url}"
                    ) from error
                time.sleep(self.delay * attempt)
                continue

            # Успешный ответ — сбрасываем счетчик неудач
            self.failures = 0
            time.sleep(self.delay)

            if response.status_code == 200:
                return response.text

            # 404/410 — страницы нет, повторять смысла нет
            if response.status_code in (404, 410):
                logger.info("Страница не найдена (%s): %s", response.status_code, url)
                return None

            logger.warning(
                "HTTP %s (попытка %s/%s): %s",
                response.status_code, attempt, REQUEST_RETRIES, url,
            )
            time.sleep(self.delay * attempt)

        logger.warning("Не удалось скачать за %s попыток: %s", REQUEST_RETRIES, url)
        return None