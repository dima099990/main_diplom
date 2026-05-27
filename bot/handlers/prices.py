"""Поиск цен по прайс-листу."""
import logging
from vkbottle.bot import Message

import user_data as ud
from keyboards import MAIN_MENU, UNREGISTERED_MENU, CANCEL_KB

logger = logging.getLogger(__name__)

STATE_PRICES_QUERY = "prices_query"


async def prices_start(message: Message, uid: int) -> None:
    """Запускает диалог поиска цен (доступен всем)."""
    ud.set_state(uid, STATE_PRICES_QUERY)
    await message.answer(
        "🔍 Напишите модель телефона или тип ремонта.\n\n"
        "Примеры: iPhone 15 Pro, Samsung S24, экран, батарея",
        keyboard=CANCEL_KB,
    )


async def prices_got_query(message: Message, uid: int, text: str) -> None:
    """Пользователь ввёл поисковый запрос."""
    from db import search_prices, get_all_prices_text, get_settings, get_customer_by_vk
    from ai import get_ai_response

    if text == "❌ Отмена":
        ud.clear(uid)
        customer = await get_customer_by_vk(uid)
        kb = MAIN_MENU if customer else UNREGISTERED_MENU
        await message.answer("Отменено.", keyboard=kb)
        return

    ud.clear(uid)
    customer = await get_customer_by_vk(uid)
    kb = MAIN_MENU if customer else UNREGISTERED_MENU

    results = await search_prices(text)

    if results:
        lines = [f"💰 Цены по запросу «{text}»:\n"]
        for r in results[:15]:
            duration = f" · ⏱ {r['duration']}" if r["duration"] else ""
            lines.append(
                f"📱 {r['brand']} {r['model']}\n"
                f"   {r['service']}: {r['price']}{duration}"
            )
        lines.append("\nТочная стоимость уточняется после диагностики.")
        await message.answer("\n".join(lines), keyboard=kb)
    else:
        s = await get_settings()
        if s.bot_deepseek_key:
            import asyncio
            prices_text = await get_all_prices_text()
            answer = await asyncio.to_thread(
                get_ai_response,
                f"Сколько стоит: {text}?",
                s.bot_prompt,
                s.bot_deepseek_key,
                prices_text,
            )
            await message.answer(answer, keyboard=kb)
        else:
            await message.answer(
                f"По запросу «{text}» цену не нашли в базе.\n\n"
                f"Позвоните — назовём точную стоимость!\n"
                f"☎️ {s.phone}",
                keyboard=kb,
            )
