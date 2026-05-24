#!/usr/bin/env python
"""
Запуск сайта + Telegram-бота одновременно.

Использование:
    python run.py                              # сайт + бот (localhost:8000)
    python run.py --host 0.0.0.0 --port 8000  # доступен снаружи
    python run.py --site-only                  # только сайт
    python run.py --bot-only                   # только бот
"""
import sys
import os
import subprocess
import threading
import argparse
from pathlib import Path

ROOT   = Path(__file__).parent
PYTHON = sys.executable


def _stream(proc, prefix):
    for line in iter(proc.stdout.readline, b""):
        text = line.decode("utf-8", errors="replace").rstrip()
        print(f"{prefix} {text}", flush=True)


def run_site(host: str, port: str):
    bind = f"{host}:{port}"
    print(f"[САЙТ] Запуск на {bind} ...", flush=True)
    proc = subprocess.Popen(
        [PYTHON, "-u", "manage.py", "runserver", bind],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    _stream(proc, "[САЙТ]")
    proc.wait()


def run_bot():
    print("[БОТ]  Запуск Telegram-бота ...", flush=True)
    proc = subprocess.Popen(
        [PYTHON, "-u", "bot/main.py"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    _stream(proc, "[БОТ] ")
    proc.wait()


def main():
    parser = argparse.ArgumentParser(description="Kayros CRM — запуск")
    parser.add_argument("--host",      default="127.0.0.1",
                        help="IP для привязки (по умолч. 127.0.0.1, для сервера — 0.0.0.0)")
    parser.add_argument("--port",      default="8000",
                        help="Порт (по умолч. 8000)")
    parser.add_argument("--site-only", action="store_true", help="Только сайт")
    parser.add_argument("--bot-only",  action="store_true", help="Только бот")
    args = parser.parse_args()

    display_host = args.host if args.host != "0.0.0.0" else "<ваш-ip>"

    print("=" * 52)
    print("   Kayros CRM")
    if not args.bot_only:
        print(f"   Сайт:  http://{display_host}:{args.port}")
        print(f"   CRM:   http://{display_host}:{args.port}/crm/")
    if not args.site_only:
        print("   Бот:   работает в фоне")
    print("   Стоп:  Ctrl+C")
    print("=" * 52)

    threads = []

    if not args.bot_only:
        t = threading.Thread(target=run_site, args=(args.host, args.port), daemon=True)
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
