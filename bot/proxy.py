"""
Менеджер прокси для Telegram-бота.

Загружает список SOCKS5-прокси из proxies.csv, тестирует их параллельно
и возвращает рабочий. При сбое — автоматически переключается на следующий.
"""
from __future__ import annotations

import asyncio
import logging
import random
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Файл с прокси лежит рядом с этим модулем
PROXY_FILE = Path(__file__).parent / "proxies.csv"
TEST_URL   = "https://api.telegram.org"
TIMEOUT    = 6      # секунд на проверку одного прокси
BATCH      = 15     # сколько прокси проверяем параллельно


# ── Загрузка ──────────────────────────────────────────────────────────────────

def load_proxies() -> list[str]:
    """Читает proxies.csv и возвращает перемешанный список URL прокси."""
    if not PROXY_FILE.exists():
        logger.warning(f"[ПРОКСИ] Файл не найден: {PROXY_FILE}")
        return []

    proxies: list[str] = []
    with open(PROXY_FILE, encoding="utf-8") as f:
        for line in f:
            url = line.strip().split(",")[0].strip()
            if url.startswith("socks"):
                proxies.append(url)

    random.shuffle(proxies)
    logger.info(f"[ПРОКСИ] Загружено {len(proxies)} прокси")
    return proxies


# ── Проверка ──────────────────────────────────────────────────────────────────

async def _check(proxy_url: str) -> tuple[str, bool]:
    """Проверяет один прокси. Возвращает (url, работает)."""
    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=TIMEOUT) as client:
            r = await client.get(TEST_URL)
            return proxy_url, r.status_code < 500
    except Exception:
        return proxy_url, False


async def _find_async(proxies: list[str]) -> str | None:
    """Проверяет прокси батчами по BATCH штук, возвращает первый рабочий."""
    for i in range(0, len(proxies), BATCH):
        batch = proxies[i : i + BATCH]
        logger.info(f"[ПРОКСИ] Проверяю {i+1}–{i+len(batch)} из {len(proxies)}...")
        results = await asyncio.gather(*[_check(p) for p in batch])
        for url, ok in results:
            if ok:
                return url
    return None


def find_working_proxy(proxies: list[str]) -> str | None:
    """
    Синхронная обёртка — вызывается до старта event loop бота.
    Возвращает URL рабочего прокси или None.
    """
    if not proxies:
        return None
    result = asyncio.run(_find_async(proxies))
    if result:
        logger.info(f"[ПРОКСИ] ✓ Рабочий прокси: {result}")
    else:
        logger.warning("[ПРОКСИ] ✗ Ни один прокси не прошёл проверку")
    return result


# ── Ротация при сбое ─────────────────────────────────────────────────────────

class ProxyRotator:
    """
    Хранит список прокси и умеет выдавать следующий рабочий
    когда текущий перестал работать.
    """

    def __init__(self, proxies: list[str]):
        self._all      = proxies.copy()
        self._tried:   set[str] = set()
        self._current: str | None = None

    @property
    def current(self) -> str | None:
        return self._current

    def set_current(self, proxy: str | None) -> None:
        self._current = proxy
        if proxy:
            self._tried.add(proxy)

    def next(self) -> str | None:
        """Ищет следующий рабочий прокси из ещё не проверенных."""
        remaining = [p for p in self._all if p not in self._tried]
        if not remaining:
            # Все исчерпаны — начинаем заново
            logger.warning("[ПРОКСИ] Все прокси исчерпаны, начинаю сначала")
            self._tried.clear()
            remaining = self._all.copy()
            random.shuffle(remaining)

        result = asyncio.run(_find_async(remaining))
        if result:
            self.set_current(result)
            logger.info(f"[ПРОКСИ] Переключился на: {result}")
        else:
            self._current = None
            logger.warning("[ПРОКСИ] Рабочий прокси не найден, работаю без прокси")
        return result
