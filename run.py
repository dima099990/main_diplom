#!/usr/bin/env python
"""
Запуск сайта + Telegram-бота одновременно.

Использование:
    python run.py              # сайт + бот
    python run.py --site-only  # только сайт
    python run.py --bot-only   # только бот
    python run.py --port 8080  # другой порт сайта
"""
import sys
import os
import subprocess
import threading
import argparse
from pathlib import Path

ROOT = Path(__file__).parent
PYTHON = sys.executable


def _stream(proc, prefix):
    """Читает вывод процесса и печатает с префиксом."""
    for line in iter(proc.stdout.readline, b""):
        text = line.decode("utf-8", errors="replace").rstrip()
        print(f"{prefix} {text}", flush=True)


def run_site(port: str = "8000"):
    print(f"[САЙТ] Запуск на http://127.0.0.1:{port} ...", flush=True)
    proc = subprocess.Popen(
        [PYTHON, "manage.py", "runserver", f"0.0.0.0:{port}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    _stream(proc, "[САЙТ]")
    proc.wait()


def run_bot():
    print("[БОТ]  Запуск Telegram-бота ...", flush=True)
    proc = subprocess.Popen(
        [PYTHON, "-u", "bot/main.py"],   # -u = небуферизованный вывод
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    _stream(proc, "[БОТ] ")
    proc.wait()


def main():
    parser = argparse.ArgumentParser(description="Kayros CRM — запуск")
    parser.add_argument("--site-only", action="store_true", help="Только сайт")
    parser.add_argument("--bot-only",  action="store_true", help="Только бот")
    parser.add_argument("--port", default="8000", help="Порт Django (по умолч. 8000)")
    args = parser.parse_args()

    print("=" * 52)
    print("   Kayros CRM")
    if not args.bot_only:
        print(f"   Сайт:  http://127.0.0.1:{args.port}")
        print(f"   CRM:   http://127.0.0.1:{args.port}/crm/")
    if not args.site_only:
        print("   Бот:   работает в фоне")
    print("   Стоп:  Ctrl+C")
    print("=" * 52)

    threads = []

    if not args.bot_only:
        t = threading.Thread(target=run_site, args=(args.port,), daemon=True)
        t.start()
        threads.append(t)

    if not args.site_only:
        t = threading.Thread(target=run_bot, daemon=True)
        t.start()
        threads.append(t)

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\n[СТОП] Завершение работы...")


if __name__ == "__main__":
    main()
