"""
Инициализация Django ORM для standalone-бота.
Импортируй первым — до любых импортов моделей.

Бот использует ТУ ЖЕ базу данных, что и сайт (через Django ORM).
Отдельной БД у бота нет. Удаление папки bot/ не затронет сайт.
"""
import os
import sys
from pathlib import Path

# Корень проекта (diplom/)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
# Не трогаем USE_SQLITE — бот использует ту же БД, что и сайт

# ── Патчим настройки ДО django.setup() ────────────────────────────────────
import config.settings as _cfg  # noqa: E402

# Бот не использует Redis-кэш — заменяем на in-memory чтобы не нужен Redis
_cfg.CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}

# Убираем file-хендлер из логгирования
# (он пишет в logs/django.log — папка может не существовать)
_file_handlers = [
    name for name, h in _cfg.LOGGING.get("handlers", {}).items()
    if "FileHandler" in h.get("class", "")
]
for _h_name in _file_handlers:
    _cfg.LOGGING["handlers"].pop(_h_name, None)
    for _logger_cfg in _cfg.LOGGING.get("loggers", {}).values():
        if _h_name in _logger_cfg.get("handlers", []):
            _logger_cfg["handlers"].remove(_h_name)
    if _h_name in _cfg.LOGGING.get("root", {}).get("handlers", []):
        _cfg.LOGGING["root"]["handlers"].remove(_h_name)

# ── Запуск Django ──────────────────────────────────────────────────────────
import django  # noqa: E402
django.setup()
