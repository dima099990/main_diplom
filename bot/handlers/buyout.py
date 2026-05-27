"""Оценка стоимости выкупа устройства — пошаговый диалог."""
from __future__ import annotations
import asyncio
import logging
import re

from vkbottle.bot import Message

import user_data as ud
from keyboards import (
    MAIN_MENU, CANCEL_KB,
    MEMORY_KB, SCREEN_KB, BATTERY_KB, BODY_KB,
    BUYOUT_OFFER_KB,
    name_kb, phone_kb,
)

logger = logging.getLogger(__name__)

# ── Состояния ─────────────────────────────────────────────────────────────────
STATE_BUYOUT_DEVICE     = "buyout_device"
STATE_BUYOUT_MEMORY     = "buyout_memory"
STATE_BUYOUT_SCREEN     = "buyout_screen"
STATE_BUYOUT_BATTERY    = "buyout_battery"
STATE_BUYOUT_BODY       = "buyout_body"
STATE_BUYOUT_OFFER      = "buyout_offer"       # предложение записаться
STATE_BUYOUT_BOOK_NAME  = "buyout_book_name"   # ввод имени для записи
STATE_BUYOUT_BOOK_PHONE = "buyout_book_phone"  # ввод телефона для записи

_CANCEL = "❌ Отмена"


# ── Вспомогательные функции ───────────────────────────────────────────────────

def _clean(val: str) -> str:
    """Убирает emoji-префиксы с кнопок для чистого вывода."""
    for prefix in ("✨ ", "👍 ", "😐 ", "💔 ", "🔋 ", "🪫 ", "❓ "):
        if val.startswith(prefix):
            return val[len(prefix):]
    return val


def _build_problem(d: dict) -> str:
    """Формирует строку-комментарий к заявке на выкуп."""
    device  = d.get("buyout_device",  "")
    memory  = d.get("buyout_memory",  "")
    screen  = _clean(d.get("buyout_screen",  ""))
    battery = _clean(d.get("buyout_battery", ""))
    body    = _clean(d.get("buyout_body",    ""))
    parts = [f"Выкуп: {device}"]
    if memory:  parts.append(f"{memory}")
    if screen:  parts.append(f"экран: {screen}")
    if battery: parts.append(f"АКБ: {battery}")
    if body:    parts.append(f"корпус: {body}")
    return " | ".join(parts)


# ── Старт ─────────────────────────────────────────────────────────────────────

async def buyout_start(message: Message, uid: int) -> None:
    ud.set_state(uid, STATE_BUYOUT_DEVICE)
    await message.answer(
        "📦 Оценка стоимости выкупа устройства\n\n"
        "Шаг 1 из 5 — Укажите модель устройства:\n\n"
        "Например: iPhone 13, Samsung Galaxy S21, Xiaomi 13 Pro",
        keyboard=CANCEL_KB,
    )


# ── Шаги оценки ───────────────────────────────────────────────────────────────

async def buyout_got_device(message: Message, uid: int, text: str) -> None:
    if text == _CANCEL:
        ud.clear(uid)
        await message.answer("Оценка отменена.", keyboard=MAIN_MENU)
        return

    ud.set_state(uid, STATE_BUYOUT_MEMORY, buyout_device=text)
    await message.answer(
        f"📱 Устройство: {text}\n\n"
        "Шаг 2 из 5 — Укажите объём встроенной памяти:",
        keyboard=MEMORY_KB,
    )


async def buyout_got_memory(message: Message, uid: int, text: str) -> None:
    if text == _CANCEL:
        ud.clear(uid)
        await message.answer("Оценка отменена.", keyboard=MAIN_MENU)
        return

    ud.set_state(uid, STATE_BUYOUT_SCREEN, buyout_memory=text)
    await message.answer(
        "Шаг 3 из 5 — Оцените состояние экрана:\n\n"
        "✨ Отличное — без царапин, как новый\n"
        "👍 Хорошее — мелкие царапины, не заметны при работе\n"
        "😐 Удовлетворительное — заметные царапины, потёртости\n"
        "💔 Повреждён — трещины, сколы, битые пиксели",
        keyboard=SCREEN_KB,
    )


async def buyout_got_screen(message: Message, uid: int, text: str) -> None:
    if text == _CANCEL:
        ud.clear(uid)
        await message.answer("Оценка отменена.", keyboard=MAIN_MENU)
        return

    ud.set_state(uid, STATE_BUYOUT_BATTERY, buyout_screen=text)
    await message.answer(
        "Шаг 4 из 5 — Ёмкость аккумулятора\n\n"
        "Посмотреть в настройках:\n"
        "iOS: Настройки → Аккумулятор → Состояние аккумулятора\n"
        "Android: Настройки → Батарея",
        keyboard=BATTERY_KB,
    )


async def buyout_got_battery(message: Message, uid: int, text: str) -> None:
    if text == _CANCEL:
        ud.clear(uid)
        await message.answer("Оценка отменена.", keyboard=MAIN_MENU)
        return

    ud.set_state(uid, STATE_BUYOUT_BODY, buyout_battery=text)
    await message.answer(
        "Шаг 5 из 5 — Оцените состояние корпуса:\n\n"
        "✨ Отличное — без царапин и вмятин\n"
        "👍 Хорошее — мелкие царапины, не заметны\n"
        "😐 Удовлетворительное — заметные царапины, потёртости\n"
        "💔 Повреждён — трещины, вмятины, сколы",
        keyboard=BODY_KB,
    )


async def buyout_got_body(message: Message, uid: int, text: str) -> None:
    if text == _CANCEL:
        ud.clear(uid)
        await message.answer("Оценка отменена.", keyboard=MAIN_MENU)
        return

    ud.update(uid, buyout_body=text)
    d = ud.get(uid)

    device  = d.get("buyout_device",  "")
    memory  = d.get("buyout_memory",  "")
    screen  = d.get("buyout_screen",  "")
    battery = d.get("buyout_battery", "")
    body    = text

    await message.answer("⏳ Оцениваю стоимость, подождите немного...")

    from db import get_settings
    from ai import estimate_buyout_price

    s = await get_settings()

    if s.bot_deepseek_key:
        try:
            ai_answer = await asyncio.to_thread(
                estimate_buyout_price,
                device, memory, screen, battery, body,
                s.bot_deepseek_key,
            )
        except Exception as e:
            logger.error(f"Ошибка ИИ-оценки выкупа: {e}", exc_info=True)
            ai_answer = (
                "Не удалось получить автоматическую оценку. "
                "Обратитесь к нам — мастер оценит устройство бесплатно!"
            )
    else:
        ai_answer = (
            "ИИ-оценщик не настроен. Приходите к нам — "
            "мастер оценит устройство бесплатно!"
        )

    # Переводим в состояние "предложить запись", данные оценки сохраняем
    ud.set_state(uid, STATE_BUYOUT_OFFER)

    await message.answer(
        f"📊 Результат оценки\n\n"
        f"📱 Модель:       {device}\n"
        f"💾 Память:       {memory}\n"
        f"🖥 Экран:        {_clean(screen)}\n"
        f"🔋 Аккумулятор: {_clean(battery)}\n"
        f"📦 Корпус:       {_clean(body)}\n\n"
        f"💰 {ai_answer}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 Для точной оценки обратитесь в наш сервисный центр — "
        f"мастер бесплатно осмотрит устройство и назовёт окончательную стоимость выкупа.\n\n"
        f"📅 Хотите записаться на сдачу устройства прямо сейчас?",
        keyboard=BUYOUT_OFFER_KB,
    )


# ── Предложение записи ────────────────────────────────────────────────────────

async def buyout_got_offer(message: Message, uid: int, text: str) -> None:
    """Пользователь ответил на предложение записаться."""
    if text != "✅ Записаться на выкуп":
        # «Нет, спасибо» или что угодно другое
        ud.clear(uid)
        await message.answer(
            "Хорошо! Если надумаете — мы всегда рады. 😊",
            keyboard=MAIN_MENU,
        )
        return

    # Проверяем регистрацию и подтягиваем имя/телефон из профиля
    from db import get_customer_by_vk
    from keyboards import UNREGISTERED_MENU

    customer = await get_customer_by_vk(uid)
    if not customer:
        ud.clear(uid)
        await message.answer(
            "Для записи необходима регистрация.\n\n"
            "Нажмите «Зарегистрироваться» 👇",
            keyboard=UNREGISTERED_MENU,
        )
        return

    cust_name  = customer.name  or ""
    cust_phone = customer.phone or ""

    # Переходим к вводу имени, сохраняем данные профиля
    ud.set_state(
        uid, STATE_BUYOUT_BOOK_NAME,
        _cust_name=cust_name,
        _cust_phone=cust_phone,
    )

    if cust_name:
        kb  = name_kb(cust_name)
        msg = (
            "📝 Оформляем запись на выкуп!\n\n"
            "Шаг 1 из 2 — Как вас зовут?\n"
            "Нажмите кнопку, чтобы использовать имя из профиля, или введите другое:"
        )
    else:
        kb  = CANCEL_KB
        msg = "📝 Оформляем запись на выкуп!\n\nШаг 1 из 2 — Как вас зовут?"

    await message.answer(msg, keyboard=kb)


# ── Запись: имя ───────────────────────────────────────────────────────────────

async def buyout_book_got_name(message: Message, uid: int, text: str) -> None:
    if text == _CANCEL:
        ud.clear(uid)
        await message.answer("Запись отменена.", keyboard=MAIN_MENU)
        return

    data = ud.get(uid)
    stored_name = data.get("_cust_name", "")

    if text.startswith("✅ "):
        name = text[2:].strip() or stored_name
    else:
        name = text.strip() or stored_name

    cust_phone = data.get("_cust_phone", "")
    ud.set_state(uid, STATE_BUYOUT_BOOK_PHONE, _book_name=name, _cust_phone=cust_phone)

    if cust_phone:
        kb  = phone_kb(cust_phone)
        msg = (
            "Шаг 2 из 2 — Укажите номер телефона:\n"
            "Нажмите кнопку, чтобы использовать номер из профиля, или введите другой:"
        )
    else:
        kb  = CANCEL_KB
        msg = "Шаг 2 из 2 — Укажите номер телефона для связи:"

    await message.answer(msg, keyboard=kb)


# ── Запись: телефон → создаём заявку ─────────────────────────────────────────

async def buyout_book_got_phone(message: Message, uid: int, text: str) -> None:
    if text == _CANCEL:
        ud.clear(uid)
        await message.answer("Запись отменена.", keyboard=MAIN_MENU)
        return

    data = ud.get(uid)
    cust_phone = data.get("_cust_phone", "")

    if text.startswith("📱 ") and cust_phone:
        phone = cust_phone
    else:
        digits = re.sub(r"\D", "", text)
        if len(digits) < 10:
            kb = phone_kb(cust_phone) if cust_phone else CANCEL_KB
            await message.answer(
                "Похоже, это не номер телефона. Введите ещё раз:",
                keyboard=kb,
            )
            return
        phone = text

    name    = data.get("_book_name", "")
    device  = data.get("buyout_device", "")
    problem = _build_problem(data)   # "Выкуп: iPhone 13 128 ГБ | экран: Хорошее | ..."

    from db import create_appointment, get_settings

    s    = await get_settings()
    appt = await create_appointment(
        name=name,
        phone=phone,
        device=device,
        problem=problem,
        vk_user_id=uid,
    )
    ud.clear(uid)

    await message.answer(
        f"✅ Заявка на выкуп #{appt.pk} принята!\n\n"
        f"Мы свяжемся с вами в ближайшее время.\n\n"
        f"📞 {s.phone}\n"
        f"⏰ {s.working_hours}",
        keyboard=MAIN_MENU,
    )
