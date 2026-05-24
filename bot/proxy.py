"""
Автоматический выбор рабочего SOCKS5 прокси.
Используется и для Telegram, и для Groq API.
Файл proxies.txt — список прокси, по одному на строку.
"""
import logging
import httpx
from pathlib import Path

logger = logging.getLogger(__name__)

PROXY_FILE = Path(__file__).parent / "proxies.txt"
TEST_URL   = "https://api.telegram.org"
TIMEOUT    = 6.0

# Найденный рабочий прокси — хранится после первого запуска
_active_proxy: str | None = None


def get_active_proxy() -> str | None:
    """Возвращает текущий рабочий прокси (или None если не нужен)."""
    return _active_proxy


def _load_proxies() -> list[str]:
    if not PROXY_FILE.exists():
        return []
    lines = PROXY_FILE.read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lines if l.strip() and not l.startswith("#")]


def find_working_proxy() -> str | None:
    """
    Перебирает прокси из proxies.txt, возвращает первый рабочий URL.
    Сохраняет результат в _active_proxy для использования в ai.py.
    Если ни один не работает — возвращает None (работаем напрямую).
    """
    global _active_proxy

    proxies = _load_proxies()
    if not proxies:
        logger.info("proxies.txt не найден или пуст — работаем без прокси")
        return None

    logger.info(f"Проверяю {len(proxies)} прокси...")

    for proxy_url in proxies:
        host = proxy_url.split("@")[-1]
        try:
            with httpx.Client(proxy=proxy_url, timeout=TIMEOUT) as client:
                r = client.get(TEST_URL)
                if r.status_code < 500:
                    logger.info(f"✅ Рабочий прокси: {host}")
                    _active_proxy = proxy_url
                    return proxy_url
        except Exception:
            logger.debug(f"❌ Не работает: {host}")

    logger.warning("⚠️  Ни один прокси не работает — запуск без прокси")
    _active_proxy = None
    return None
