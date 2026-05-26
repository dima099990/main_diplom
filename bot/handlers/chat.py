"""Свободный чат с ИИ-ассистентом, история, умная запись через ИИ."""
from __future__ import annotations
import asyncio
import re
from datetime import date, time, timedelta

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from handlers.start import MAIN_MENU

# ── Ключевые слова для определения намерения записаться ──────────────────────
_BOOKING_KEYWORDS = [
    "записаться", "записать меня", "запиши меня", "запиши",
    "хочу записаться", "хочу записать", "хочу запись",
    "запишите меня", "запишите", "оформить запись",
    "запись на ремонт", "хочу на ремонт", "запись на сервис",
]

_CONFIRM_KB = ReplyKeyboardMarkup(
    [["✅ Подтвердить", "❌ Отмена"]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

_PHONE_KB = ReplyKeyboardMarkup(
    [[KeyboardButton("📱 Поделиться номером", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

_SKIP_KB = ReplyKeyboardMarkup(
    [["⏭ Пропустить"]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

_MONTHS_RU = ["янв", "фев", "мар", "апр", "май", "июн",
               "июл", "авг", "сен", "окт", "ноя", "дек"]


def _date_kb() -> ReplyKeyboardMarkup:
    today    = date.today()
    tomorrow = today + timedelta(days=1)
    day2     = today + timedelta(days=2)
    return ReplyKeyboardMarkup(
        [
            [
                f"Сегодня ({today.strftime('%d.%m')})",
                f"Завтра ({tomorrow.strftime('%d.%m')})",
                f"{day2.strftime('%d.%m')}",
            ],
            ["⏭ Пропустить"],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


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

    # dd.mm, dd.mm.yyyy, dd/mm, dd/mm/yyyy
    m = re.search(r'(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?', t)
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

    # YYYY-MM-DD
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', t)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    return None


def _parse_time(text: str) -> time | None:
    t = text.strip().lower()

    # HH:MM или HH.MM
    m = re.search(r'\b(\d{1,2})[:\.](\d{2})\b', t)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return time(h, mi)

    # просто "16", "в 16 часов"
    m = re.search(r'\b(\d{1,2})\b', t)
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


# ── Машина состояний ─────────────────────────────────────────────────────────

def _next_step(ai_book: dict) -> str:
    """Возвращает название следующего незаполненного шага."""
    if not ai_book.get("device"):  return "ask_device"
    if not ai_book.get("problem"): return "ask_problem"
    if not ai_book.get("date"):    return "ask_date"
    if not ai_book.get("time"):    return "ask_time"
    if not ai_book.get("name"):    return "ask_name"
    if not ai_book.get("phone"):   return "ask_phone"
    return "confirm"


async def _ask_step(update: Update, ai_book: dict, step: str) -> None:
    """Задаёт вопрос для нужного шага и обновляет step в ai_book."""
    ai_book["step"] = step

    if step == "ask_device":
        await update.message.reply_text(
            "📱 Какое устройство нужно отремонтировать?\n"
            "_Например: iPhone 15 Pro, Samsung Galaxy S24_",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )

    elif step == "ask_problem":
        await update.message.reply_text(
            f"📱 Устройство: *{ai_book.get('device')}*\n\n"
            "🔧 Опишите проблему или вид работы:",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )

    elif step == "ask_date":
        await update.message.reply_text(
            "📅 На какую дату записать?\nВыберите или введите вручную:",
            reply_markup=_date_kb(),
        )

    elif step == "ask_time":
        await update.message.reply_text(
            "⏰ В какое время удобно?\n"
            "_Например: 14:00 или 16:30_",
            parse_mode="Markdown",
            reply_markup=_SKIP_KB,
        )

    elif step == "ask_name":
        await update.message.reply_text(
            "👤 Как вас зовут?",
            reply_markup=ReplyKeyboardRemove(),
        )

    elif step == "ask_phone":
        await update.message.reply_text(
            "📞 Укажите номер телефона или поделитесь контактом:",
            reply_markup=_PHONE_KB,
        )

    elif step == "confirm":
        await _show_confirm(update, ai_book)


async def _show_confirm(update: Update, ai_book: dict) -> None:
    """Показывает итоговые данные записи для подтверждения."""
    ai_book["step"] = "confirm"
    await update.message.reply_text(
        f"📋 *Проверьте данные записи:*\n\n"
        f"👤 Имя:        {ai_book.get('name') or '—'}\n"
        f"📞 Телефон:    {ai_book.get('phone') or '—'}\n"
        f"📱 Устройство: {ai_book.get('device') or '—'}\n"
        f"🔧 Проблема:   {ai_book.get('problem') or '—'}\n"
        f"📅 Дата:       {_fmt_date(ai_book.get('date', ''))}\n"
        f"⏰ Время:      {_fmt_time(ai_book.get('time', ''))}\n\n"
        "Всё верно?",
        parse_mode="Markdown",
        reply_markup=_CONFIRM_KB,
    )


def _validate_ai_extract(info: dict) -> dict:
    """Валидирует и нормализует поля, извлечённые ИИ."""
    result = {}

    result["device"]  = info.get("device",  "").strip()
    result["problem"] = info.get("problem", "").strip()
    result["name"]    = info.get("name",    "").strip()

    # Телефон — минимум 10 цифр
    raw_phone = info.get("phone", "").strip()
    digits = re.sub(r'\D', '', raw_phone)
    result["phone"] = raw_phone if len(digits) >= 10 else ""

    # Дата — YYYY-MM-DD или парсим текст
    ai_date = info.get("date", "").strip()
    if ai_date:
        try:
            date.fromisoformat(ai_date)   # уже в нужном формате
            result["date"] = ai_date
        except ValueError:
            parsed = _parse_date(ai_date)
            result["date"] = parsed.isoformat() if parsed else ""
    else:
        result["date"] = ""

    # Время — HH:MM
    ai_time = info.get("time", "").strip()
    if ai_time:
        parsed_t = _parse_time(ai_time)
        result["time"] = parsed_t.strftime("%H:%M") if parsed_t else ""
    else:
        result["time"] = ""

    return result


# ── Хелпер для обработки контакта в ai_book-потоке ───────────────────────────
async def _finish_ai_book_phone(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Вызывается из start.py когда ai_book ждёт номер телефона."""
    ai_book = context.user_data.get("ai_book", {})
    contact = update.message.contact
    ai_book["phone"] = contact.phone_number or ""
    context.user_data["ai_book"] = ai_book
    await _show_confirm(update, ai_book)


# ── История чата ──────────────────────────────────────────────────────────────
def _add_history(context, role: str, content: str) -> None:
    history = context.user_data.setdefault("chat_history", [])
    history.append({"role": role, "content": content})
    if len(history) > 10:
        context.user_data["chat_history"] = history[-10:]


def _is_booking_intent(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _BOOKING_KEYWORDS)


# ── Основной хендлер ─────────────────────────────────────────────────────────
async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from db import (get_settings, get_all_prices_text,
                    get_customer_by_telegram, create_appointment)
    from ai import get_ai_response, extract_booking_info

    user_text = update.message.text.strip()
    s   = await get_settings()
    tid = update.effective_user.id

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # ══════════════════════════════════════════════════════════════════════
    # Машина состояний ai_book
    # ══════════════════════════════════════════════════════════════════════
    ai_book = context.user_data.get("ai_book")

    if ai_book:
        step = ai_book.get("step")

        # ── Устройство ───────────────────────────────────────────────────
        if step == "ask_device":
            ai_book["device"] = user_text
            next_s = _next_step(ai_book)
            context.user_data["ai_book"] = ai_book
            await _ask_step(update, ai_book, next_s)
            return

        # ── Проблема ─────────────────────────────────────────────────────
        if step == "ask_problem":
            ai_book["problem"] = user_text
            next_s = _next_step(ai_book)
            context.user_data["ai_book"] = ai_book
            await _ask_step(update, ai_book, next_s)
            return

        # ── Дата ─────────────────────────────────────────────────────────
        if step == "ask_date":
            if _is_skip(user_text):
                ai_book["date"] = "skip"
            else:
                parsed = _parse_date(user_text)
                if parsed:
                    ai_book["date"] = parsed.isoformat()
                else:
                    await update.message.reply_text(
                        "Не понял дату 🤔 Попробуйте ещё раз:\n"
                        "_Например: завтра, 20.07, пятница_",
                        parse_mode="Markdown",
                        reply_markup=_date_kb(),
                    )
                    return
            next_s = _next_step(ai_book)
            context.user_data["ai_book"] = ai_book
            await _ask_step(update, ai_book, next_s)
            return

        # ── Время ────────────────────────────────────────────────────────
        if step == "ask_time":
            if _is_skip(user_text):
                ai_book["time"] = "skip"
            else:
                parsed = _parse_time(user_text)
                if parsed:
                    ai_book["time"] = parsed.strftime("%H:%M")
                else:
                    await update.message.reply_text(
                        "Не понял время 🤔 Введите, например: *16:00* или *14:30*",
                        parse_mode="Markdown",
                        reply_markup=_SKIP_KB,
                    )
                    return
            next_s = _next_step(ai_book)
            context.user_data["ai_book"] = ai_book
            await _ask_step(update, ai_book, next_s)
            return

        # ── Имя ──────────────────────────────────────────────────────────
        if step == "ask_name":
            ai_book["name"] = user_text
            next_s = _next_step(ai_book)
            context.user_data["ai_book"] = ai_book
            await _ask_step(update, ai_book, next_s)
            return

        # ── Телефон текстом (контакт — в start.py) ───────────────────────
        if step == "ask_phone":
            digits = re.sub(r'\D', '', user_text)
            if len(digits) < 10:
                await update.message.reply_text(
                    "Похоже, это не номер телефона. Введите ещё раз или поделитесь контактом:",
                    reply_markup=_PHONE_KB,
                )
                return
            ai_book["phone"] = user_text
            context.user_data["ai_book"] = ai_book
            await _show_confirm(update, ai_book)
            return

        # ── Подтверждение ────────────────────────────────────────────────
        if step == "confirm":
            if "отмена" in user_text.lower() or "❌" in user_text:
                context.user_data.pop("ai_book", None)
                await update.message.reply_text("Запись отменена.", reply_markup=MAIN_MENU)
                return

            # Конвертируем date/time для БД
            pref_date = None
            pref_time = None
            d_val = ai_book.get("date", "")
            t_val = ai_book.get("time", "")
            if d_val and d_val != "skip":
                try:
                    pref_date = date.fromisoformat(d_val)
                except Exception:
                    pass
            if t_val and t_val != "skip":
                pref_time = _parse_time(t_val)

            appt = await create_appointment(
                name=ai_book["name"],
                phone=ai_book["phone"],
                device=ai_book["device"],
                problem=ai_book["problem"],
                telegram_chat_id=tid,
                preferred_date=pref_date,
                preferred_time=pref_time,
            )
            context.user_data.pop("ai_book", None)

            # Красивое подтверждение
            dt_line = ""
            if pref_date:
                dt_line += f"\n📅 {pref_date.day} {_MONTHS_RU[pref_date.month - 1]}"
            if pref_time:
                dt_line += f" в {pref_time.strftime('%H:%M')}"

            await update.message.reply_text(
                f"✅ *Заявка #{appt.pk} принята!*\n\n"
                f"Мы свяжемся с вами в ближайшее время.{dt_line}\n\n"
                f"📞 {s.phone}\n"
                f"⏰ {s.working_hours}",
                parse_mode="Markdown",
                reply_markup=MAIN_MENU,
            )
            return

    # ══════════════════════════════════════════════════════════════════════
    # Определение намерения записаться → умный парсинг всего сообщения
    # ══════════════════════════════════════════════════════════════════════
    if _is_booking_intent(user_text) and s.bot_deepseek_key:
        raw = await asyncio.to_thread(extract_booking_info, user_text, s.bot_deepseek_key)
        ai_book = _validate_ai_extract(raw)

        # Подтягиваем данные из БД если клиент знаком
        customer = await get_customer_by_telegram(tid)
        if customer:
            if not ai_book["name"]:
                ai_book["name"] = customer.name
            if not ai_book["phone"]:
                ai_book["phone"] = customer.phone

        # Показываем что уже распознали
        known = []
        if ai_book.get("device"):
            known.append(f"📱 {ai_book['device']}")
        if ai_book.get("problem"):
            known.append(f"🔧 {ai_book['problem']}")
        if ai_book.get("date"):
            known.append(f"📅 {_fmt_date(ai_book['date'])}")
        if ai_book.get("time"):
            known.append(f"⏰ {ai_book['time']}")
        if ai_book.get("name"):
            known.append(f"👤 {ai_book['name']}")
        if ai_book.get("phone"):
            known.append(f"📞 {ai_book['phone']}")

        if known:
            await update.message.reply_text(
                "📋 Записываю! Уже понял:\n" + "  ".join(known),
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            await update.message.reply_text(
                "📅 Отлично, оформляю запись!",
                reply_markup=ReplyKeyboardRemove(),
            )

        next_s = _next_step(ai_book)
        context.user_data["ai_book"] = ai_book

        if next_s == "confirm":
            # Всё распознано — сразу на подтверждение
            await _show_confirm(update, ai_book)
        else:
            await _ask_step(update, ai_book, next_s)
        return

    # ══════════════════════════════════════════════════════════════════════
    # Обычный чат с ИИ (с историей)
    # ══════════════════════════════════════════════════════════════════════
    if s.bot_deepseek_key:
        prices_text = await get_all_prices_text()
        history     = context.user_data.get("chat_history", [])

        answer = await asyncio.to_thread(
            get_ai_response,
            user_text,
            s.bot_prompt,
            s.bot_deepseek_key,
            prices_text,
            history,
        )

        _add_history(context, "user",      user_text)
        _add_history(context, "assistant", answer)
    else:
        answer = (
            f"Задайте вопрос или позвоните нам напрямую:\n"
            f"📞 {s.phone}\n"
            f"⏰ {s.working_hours}"
        )

    await update.message.reply_text(answer, reply_markup=MAIN_MENU)


async def handle_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from db import get_settings
    s = await get_settings()
    await update.message.reply_text(
        f"📍 *{s.company_name}*\n\n"
        f"📞 {s.phone}\n"
        f"⏰ {s.working_hours}\n"
        f"📍 {s.address}",
        parse_mode="Markdown",
        reply_markup=MAIN_MENU,
    )
