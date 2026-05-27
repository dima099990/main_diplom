"""Свободный чат с ИИ-ассистентом и умная запись через ИИ."""
from __future__ import annotations
import asyncio
import logging
import re
from datetime import date, time, timedelta

from vkbottle.bot import Message

import user_data as ud
from keyboards import (
    MAIN_MENU, UNREGISTERED_MENU, CONFIRM_KB, SKIP_KB, CANCEL_KB, date_kb,
)

logger = logging.getLogger(__name__)

# ── Состояния умной записи ────────────────────────────────────────────────────
ST_AIBOOK_DEVICE  = "aibook_device"
ST_AIBOOK_PROBLEM = "aibook_problem"
ST_AIBOOK_DATE    = "aibook_date"
ST_AIBOOK_TIME    = "aibook_time"
ST_AIBOOK_NAME    = "aibook_name"
ST_AIBOOK_PHONE   = "aibook_phone"
ST_AIBOOK_CONFIRM = "aibook_confirm"

# ── Ключевые слова намерения записаться ───────────────────────────────────────
_BOOKING_KEYWORDS = [
    "записаться", "записать меня", "запиши меня", "запиши",
    "хочу записаться", "хочу записать", "хочу запись",
    "запишите меня", "запишите", "оформить запись",
    "запись на ремонт", "хочу на ремонт", "запись на сервис",
]

_MONTHS_RU = ["янв", "фев", "мар", "апр", "май", "июн",
               "июл", "авг", "сен", "окт", "ноя", "дек"]


# ── Парсеры даты и времени ────────────────────────────────────────────────────

def _parse_date(text: str) -> date | None:
    t = text.strip().lower()
    today = date.today()

    if "сегодня" in t:
        return today
    if "послезавтра" in t:
        return today + timedelta(days=2)
    if "завтра" in t:
        return today + timedelta(days=1)

    days_ru = {
        "понедельник": 0, "пнд": 0,
        "вторник": 1,     "вт": 1,
        "среда": 2, "среду": 2, "ср": 2,
        "четверг": 3,     "чт": 3,
        "пятница": 4, "пятницу": 4, "пт": 4,
        "суббота": 5, "субботу": 5, "сб": 5,
        "воскресенье": 6, "вс": 6,
    }
    for name, num in days_ru.items():
        if name in t:
            ahead = num - today.weekday()
            if ahead <= 0:
                ahead += 7
            return today + timedelta(days=ahead)

    m = re.search(r"(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?", t)
    if m:
        try:
            d, mo = int(m.group(1)), int(m.group(2))
            yr = int(m.group(3)) if m.group(3) else today.year
            if yr < 100:
                yr += 2000
            result = date(yr, mo, d)
            if result < today:
                result = date(yr + 1, mo, d)
            return result
        except ValueError:
            pass

    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    return None


def _parse_time(text: str) -> time | None:
    t = text.strip().lower()
    m = re.search(r"\b(\d{1,2})[:\.](\d{2})\b", t)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return time(h, mi)
    m = re.search(r"\b(\d{1,2})\b", t)
    if m:
        h = int(m.group(1))
        if 0 <= h <= 23:
            return time(h, 0)
    return None


def _is_skip(text: str) -> bool:
    t = text.strip().lower()
    return "пропустить" in t or t.startswith("⏭")


def _fmt_date(val: str) -> str:
    if not val or val == "skip":
        return "—"
    try:
        d = date.fromisoformat(val)
        return f"{d.day} {_MONTHS_RU[d.month - 1]} {d.year}"
    except Exception:
        return val


def _fmt_time(val: str) -> str:
    return "—" if not val or val == "skip" else val


def _next_aibook_step(data: dict) -> str:
    if not data.get("ai_device"):  return ST_AIBOOK_DEVICE
    if not data.get("ai_problem"): return ST_AIBOOK_PROBLEM
    if not data.get("ai_date"):    return ST_AIBOOK_DATE
    if not data.get("ai_time"):    return ST_AIBOOK_TIME
    if not data.get("ai_name"):    return ST_AIBOOK_NAME
    if not data.get("ai_phone"):   return ST_AIBOOK_PHONE
    return ST_AIBOOK_CONFIRM


def _is_booking_intent(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _BOOKING_KEYWORDS)


def _validate_ai_extract(info: dict, customer=None) -> dict:
    result = {
        "ai_device":  info.get("device",  "").strip(),
        "ai_problem": info.get("problem", "").strip(),
        "ai_name":    info.get("name",    "").strip(),
    }
    raw_phone = info.get("phone", "").strip()
    digits = re.sub(r"\D", "", raw_phone)
    result["ai_phone"] = raw_phone if len(digits) >= 10 else ""

    ai_date = info.get("date", "").strip()
    if ai_date:
        try:
            date.fromisoformat(ai_date)
            result["ai_date"] = ai_date
        except ValueError:
            parsed = _parse_date(ai_date)
            result["ai_date"] = parsed.isoformat() if parsed else ""
    else:
        result["ai_date"] = ""

    ai_time = info.get("time", "").strip()
    if ai_time:
        parsed_t = _parse_time(ai_time)
        result["ai_time"] = parsed_t.strftime("%H:%M") if parsed_t else ""
    else:
        result["ai_time"] = ""

    # Подтягиваем из профиля клиента если пусто
    if customer:
        if not result["ai_name"]:
            result["ai_name"] = customer.name or ""
        if not result["ai_phone"]:
            result["ai_phone"] = customer.phone or ""

    return result


# ── Шаги умной записи ─────────────────────────────────────────────────────────

async def _show_confirm(message: Message, uid: int) -> None:
    data = ud.get(uid)
    ud.set_state(uid, ST_AIBOOK_CONFIRM)
    await message.answer(
        f"📋 Проверьте данные записи:\n\n"
        f"👤 Имя:        {data.get('ai_name') or '—'}\n"
        f"📞 Телефон:    {data.get('ai_phone') or '—'}\n"
        f"📱 Устройство: {data.get('ai_device') or '—'}\n"
        f"🔧 Проблема:   {data.get('ai_problem') or '—'}\n"
        f"📅 Дата:       {_fmt_date(data.get('ai_date', ''))}\n"
        f"⏰ Время:      {_fmt_time(data.get('ai_time', ''))}\n\n"
        f"Всё верно?",
        keyboard=CONFIRM_KB,
    )


async def _ask_aibook_step(message: Message, uid: int, step: str) -> None:
    ud.update(uid, **{"_state": step})

    if step == ST_AIBOOK_DEVICE:
        await message.answer(
            "📱 Какое устройство нужно отремонтировать?\n"
            "Например: iPhone 15 Pro, Samsung Galaxy S24",
            keyboard=CANCEL_KB,
        )
    elif step == ST_AIBOOK_PROBLEM:
        data = ud.get(uid)
        await message.answer(
            f"📱 Устройство: {data.get('ai_device')}\n\n"
            "🔧 Опишите проблему или вид работы:",
            keyboard=CANCEL_KB,
        )
    elif step == ST_AIBOOK_DATE:
        await message.answer(
            "📅 На какую дату записать? Выберите или введите вручную:",
            keyboard=date_kb(),
        )
    elif step == ST_AIBOOK_TIME:
        await message.answer(
            "⏰ В какое время удобно?\nНапример: 14:00 или 16:30",
            keyboard=SKIP_KB,
        )
    elif step == ST_AIBOOK_NAME:
        await message.answer("👤 Как вас зовут?", keyboard=CANCEL_KB)
    elif step == ST_AIBOOK_PHONE:
        await message.answer(
            "📞 Укажите номер телефона для связи:",
            keyboard=CANCEL_KB,
        )
    elif step == ST_AIBOOK_CONFIRM:
        await _show_confirm(message, uid)


# ── Обработчик состояний умной записи ────────────────────────────────────────

async def handle_chat_state(message: Message, uid: int, text: str, state: str) -> None:
    """Роутинг состояний умной записи (aibook_*)."""
    if text == "❌ Отмена":
        ud.clear(uid)
        await message.answer("Запись отменена.", keyboard=MAIN_MENU)
        return

    data = ud.get(uid)

    if state == ST_AIBOOK_DEVICE:
        ud.update(uid, ai_device=text)
        next_s = _next_aibook_step(ud.get(uid))
        await _ask_aibook_step(message, uid, next_s)

    elif state == ST_AIBOOK_PROBLEM:
        ud.update(uid, ai_problem=text)
        next_s = _next_aibook_step(ud.get(uid))
        await _ask_aibook_step(message, uid, next_s)

    elif state == ST_AIBOOK_DATE:
        if _is_skip(text):
            ud.update(uid, ai_date="skip")
        else:
            parsed = _parse_date(text)
            if parsed:
                ud.update(uid, ai_date=parsed.isoformat())
            else:
                await message.answer(
                    "Не понял дату. Попробуйте ещё раз:\n"
                    "Например: завтра, 20.07, пятница",
                    keyboard=date_kb(),
                )
                return
        next_s = _next_aibook_step(ud.get(uid))
        await _ask_aibook_step(message, uid, next_s)

    elif state == ST_AIBOOK_TIME:
        if _is_skip(text):
            ud.update(uid, ai_time="skip")
        else:
            parsed = _parse_time(text)
            if parsed:
                ud.update(uid, ai_time=parsed.strftime("%H:%M"))
            else:
                await message.answer(
                    "Не понял время. Введите, например: 16:00 или 14:30",
                    keyboard=SKIP_KB,
                )
                return
        next_s = _next_aibook_step(ud.get(uid))
        await _ask_aibook_step(message, uid, next_s)

    elif state == ST_AIBOOK_NAME:
        ud.update(uid, ai_name=text)
        next_s = _next_aibook_step(ud.get(uid))
        await _ask_aibook_step(message, uid, next_s)

    elif state == ST_AIBOOK_PHONE:
        digits = re.sub(r"\D", "", text)
        if len(digits) < 10:
            await message.answer(
                "Похоже, это не номер телефона. Введите ещё раз:",
                keyboard=CANCEL_KB,
            )
            return
        ud.update(uid, ai_phone=text)
        await _show_confirm(message, uid)

    elif state == ST_AIBOOK_CONFIRM:
        if text == "✅ Подтвердить":
            await _finish_aibook(message, uid)
        else:
            await message.answer(
                "Пожалуйста, нажмите одну из кнопок ниже:",
                keyboard=CONFIRM_KB,
            )


async def _finish_aibook(message: Message, uid: int) -> None:
    """Создаём запись после подтверждения."""
    from db import create_appointment, get_settings

    data = ud.get(uid)
    s = await get_settings()

    pref_date = None
    pref_time = None
    d_val = data.get("ai_date", "")
    t_val = data.get("ai_time", "")
    if d_val and d_val != "skip":
        try:
            pref_date = date.fromisoformat(d_val)
        except Exception:
            pass
    if t_val and t_val != "skip":
        pref_time = _parse_time(t_val)

    appt = await create_appointment(
        name=data.get("ai_name", ""),
        phone=data.get("ai_phone", ""),
        device=data.get("ai_device", ""),
        problem=data.get("ai_problem", ""),
        vk_user_id=uid,
        preferred_date=pref_date,
        preferred_time=pref_time,
    )
    ud.clear(uid)

    dt_line = ""
    if pref_date:
        dt_line += f"\n📅 {pref_date.day} {_MONTHS_RU[pref_date.month - 1]}"
    if pref_time:
        dt_line += f" в {pref_time.strftime('%H:%M')}"

    await message.answer(
        f"✅ Заявка #{appt.pk} принята!\n\n"
        f"Мы свяжемся с вами в ближайшее время.{dt_line}\n\n"
        f"📞 {s.phone}\n"
        f"⏰ {s.working_hours}",
        keyboard=MAIN_MENU,
    )


# ── История чата ──────────────────────────────────────────────────────────────

def _add_history(uid: int, role: str, content: str) -> None:
    data = ud.get(uid)
    history = data.setdefault("chat_history", [])
    history.append({"role": role, "content": content})
    if len(history) > 10:
        data["chat_history"] = history[-10:]


# ── Основной хендлер чата ─────────────────────────────────────────────────────

async def handle_chat(message: Message, uid: int, text: str) -> None:
    from db import get_settings, get_all_prices_text, get_customer_by_vk
    from ai import get_ai_response, extract_booking_info

    if not text:
        return

    s        = await get_settings()
    customer = await get_customer_by_vk(uid)

    if not customer:
        await message.answer(
            "Для чата и записи на ремонт необходима регистрация.\n\n"
            "Нажмите «Зарегистрироваться» 👇",
            keyboard=UNREGISTERED_MENU,
        )
        return

    # Показываем "печатает..."
    try:
        await message.ctx_api.messages.set_activity(peer_id=message.peer_id, type="typing")
    except Exception:
        pass

    # ── Умная запись: распознаём намерение ────────────────────────────────────
    if _is_booking_intent(text):
        # Пытаемся извлечь данные через ИИ (если ключ есть)
        if s.bot_deepseek_key:
            try:
                raw = await asyncio.to_thread(extract_booking_info, text, s.bot_deepseek_key)
                fields = _validate_ai_extract(raw, customer)
            except Exception:
                fields = _validate_ai_extract({}, customer)
        else:
            # Нет ключа Groq — просто берём имя/телефон из профиля
            fields = _validate_ai_extract({}, customer)

        known = []
        if fields.get("ai_device"):  known.append(f"📱 {fields['ai_device']}")
        if fields.get("ai_problem"): known.append(f"🔧 {fields['ai_problem']}")
        if fields.get("ai_date"):    known.append(f"📅 {_fmt_date(fields['ai_date'])}")
        if fields.get("ai_time"):    known.append(f"⏰ {fields['ai_time']}")
        if fields.get("ai_name"):    known.append(f"👤 {fields['ai_name']}")
        if fields.get("ai_phone"):   known.append(f"📞 {fields['ai_phone']}")

        if known:
            await message.answer("📋 Записываю! Уже понял:\n" + "  ".join(known))
        else:
            await message.answer("📅 Отлично, оформляю запись на ремонт!")

        ud.update(uid, **fields)
        ud.update(uid, **{"_state": None})   # сброс перед выбором следующего шага
        next_s = _next_aibook_step(ud.get(uid))
        await _ask_aibook_step(message, uid, next_s)
        return

    # ── Обычный чат с ИИ ──────────────────────────────────────────────────────
    if s.bot_deepseek_key:
        prices_text = await get_all_prices_text()
        history     = ud.get(uid).get("chat_history", [])

        answer = await asyncio.to_thread(
            get_ai_response,
            text,
            s.bot_prompt,
            s.bot_deepseek_key,
            prices_text,
            history,
        )
        _add_history(uid, "user",      text)
        _add_history(uid, "assistant", answer)
    else:
        answer = (
            f"Задайте вопрос или позвоните нам напрямую:\n"
            f"📞 {s.phone}\n"
            f"⏰ {s.working_hours}"
        )

    await message.answer(answer, keyboard=MAIN_MENU)


async def handle_contacts(message: Message, uid: int) -> None:
    from db import get_settings, get_customer_by_vk

    s        = await get_settings()
    customer = await get_customer_by_vk(uid)
    kb       = MAIN_MENU if customer else UNREGISTERED_MENU

    await message.answer(
        f"📍 {s.company_name}\n\n"
        f"📞 {s.phone}\n"
        f"⏰ {s.working_hours}\n"
        f"📍 {s.address}",
        keyboard=kb,
    )
