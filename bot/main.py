"""VK-бот сервисного центра."""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import django_setup  # noqa

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from typing import Any

import aiohttp
from vkbottle.api import API
from vkbottle.bot import Bot, Message
from vkbottle.http import AiohttpClient


class _NoSSLClient(AiohttpClient):
    """AiohttpClient с отключённой проверкой SSL.

    На Windows антивирус / корпоративный прокси подменяет сертификат
    api.vk.ru — стандартная проверка падает с SSLCertVerificationError.
    Создаём TCPConnector(ssl=False) внутри async-метода request, где
    уже гарантированно запущен event loop (иначе aiohttp бросает
    RuntimeError: no running event loop).
    """

    @asynccontextmanager
    async def request(
        self,
        url: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[aiohttp.ClientResponse, None]:
        if not self.session:
            connector = aiohttp.TCPConnector(ssl=False)
            self.session = aiohttp.ClientSession(
                connector=connector,
                json_serialize=self.json_processing_module.dumps,
                **self._session_params,
            )
        async with self.session.request(url=url, method=method, data=data, **kwargs) as resp:
            yield resp

import user_data as ud
from db import _get_settings as get_settings_sync
from handlers.start import (
    cmd_start, reg_ask_phone, reg_got_phone, reg_got_consent,
    STATE_REG_PHONE, STATE_REG_CONSENT,
)
from handlers.prices import prices_start, prices_got_query, STATE_PRICES_QUERY
from handlers.booking import (
    booking_start, booking_got_name, booking_got_phone,
    booking_got_device, booking_got_problem, booking_got_confirm,
    STATE_BOOK_NAME, STATE_BOOK_PHONE, STATE_BOOK_DEVICE,
    STATE_BOOK_PROBLEM, STATE_BOOK_CONFIRM,
)
from handlers.chat import (
    handle_chat, handle_contacts, handle_chat_state,
    ST_AIBOOK_DEVICE, ST_AIBOOK_PROBLEM, ST_AIBOOK_DATE,
    ST_AIBOOK_TIME, ST_AIBOOK_NAME, ST_AIBOOK_PHONE, ST_AIBOOK_CONFIRM,
)
from handlers.buyout import (
    buyout_start,
    buyout_got_device, buyout_got_memory, buyout_got_screen,
    buyout_got_battery, buyout_got_body,
    buyout_got_offer,
    buyout_book_got_name, buyout_book_got_phone,
    STATE_BUYOUT_DEVICE, STATE_BUYOUT_MEMORY, STATE_BUYOUT_SCREEN,
    STATE_BUYOUT_BATTERY, STATE_BUYOUT_BODY,
    STATE_BUYOUT_OFFER, STATE_BUYOUT_BOOK_NAME, STATE_BUYOUT_BOOK_PHONE,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

_AIBOOK_STATES = {
    ST_AIBOOK_DEVICE, ST_AIBOOK_PROBLEM, ST_AIBOOK_DATE,
    ST_AIBOOK_TIME, ST_AIBOOK_NAME, ST_AIBOOK_PHONE, ST_AIBOOK_CONFIRM,
}

_BUYOUT_STATES = {
    STATE_BUYOUT_DEVICE, STATE_BUYOUT_MEMORY, STATE_BUYOUT_SCREEN,
    STATE_BUYOUT_BATTERY, STATE_BUYOUT_BODY,
    STATE_BUYOUT_OFFER, STATE_BUYOUT_BOOK_NAME, STATE_BUYOUT_BOOK_PHONE,
}


def build_bot(token: str) -> Bot:
    api = API(token=token, http_client=_NoSSLClient())
    bot = Bot(api=api)

    @bot.on.message()
    async def router(message: Message) -> None:
        uid  = message.from_id
        text = (message.text or "").strip()
        s    = ud.state(uid)

        logger.info(f"VK uid={uid} state={s!r} text={text!r}")

        # ─── Активное состояние ────────────────────────────────────────────
        if s:
            if s == STATE_REG_PHONE:
                await reg_got_phone(message, uid, text);    return
            if s == STATE_REG_CONSENT:
                await reg_got_consent(message, uid, text);  return
            if s == STATE_BOOK_NAME:
                await booking_got_name(message, uid, text);    return
            if s == STATE_BOOK_PHONE:
                await booking_got_phone(message, uid, text);   return
            if s == STATE_BOOK_DEVICE:
                await booking_got_device(message, uid, text);  return
            if s == STATE_BOOK_PROBLEM:
                await booking_got_problem(message, uid, text); return
            if s == STATE_BOOK_CONFIRM:
                await booking_got_confirm(message, uid, text); return
            if s == STATE_PRICES_QUERY:
                await prices_got_query(message, uid, text);    return
            if s in _AIBOOK_STATES:
                await handle_chat_state(message, uid, text, s); return
            if s == STATE_BUYOUT_DEVICE:
                await buyout_got_device(message, uid, text);     return
            if s == STATE_BUYOUT_MEMORY:
                await buyout_got_memory(message, uid, text);     return
            if s == STATE_BUYOUT_SCREEN:
                await buyout_got_screen(message, uid, text);     return
            if s == STATE_BUYOUT_BATTERY:
                await buyout_got_battery(message, uid, text);    return
            if s == STATE_BUYOUT_BODY:
                await buyout_got_body(message, uid, text);       return
            if s == STATE_BUYOUT_OFFER:
                await buyout_got_offer(message, uid, text);      return
            if s == STATE_BUYOUT_BOOK_NAME:
                await buyout_book_got_name(message, uid, text);  return
            if s == STATE_BUYOUT_BOOK_PHONE:
                await buyout_book_got_phone(message, uid, text); return

        # ─── Кнопки меню (без состояния) ──────────────────────────────────
        tl = text.lower()

        if tl in ("начать", "start", "/start") or not text:
            await cmd_start(message, uid);              return
        if text == "💰 Узнать цены":
            await prices_start(message, uid);           return
        if text == "📅 Записаться":
            await booking_start(message, uid);          return
        if text == "📞 Контакты":
            await handle_contacts(message, uid);        return
        if text == "📝 Зарегистрироваться":
            await reg_ask_phone(message, uid);          return
        if text == "📦 Выкуп":
            await buyout_start(message, uid);           return

        # ─── Свободный текст → ИИ-чат ──────────────────────────────────────
        await handle_chat(message, uid, text)

    return bot


def main() -> None:
    s = get_settings_sync()
    if not s.bot_token:
        logger.error("Токен VK-бота не задан! CRM → Настройки компании → VK Бот")
        sys.exit(1)
    logger.info(f"Запуск VK-бота для '{s.company_name}'...")
    bot = build_bot(s.bot_token)
    bot.run_forever()


if __name__ == "__main__":
    main()
