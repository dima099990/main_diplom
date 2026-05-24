"""Свободный чат с ИИ-ассистентом, история, запись через ИИ."""
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


def _is_booking_intent(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _BOOKING_KEYWORDS)


def _add_history(context, role: str, content: str) -> None:
    """Добавляет сообщение в историю, хранит последние 5 обменов (10 сообщений)."""
    history = context.user_data.setdefault("chat_history", [])
    history.append({"role": role, "content": content})
    if len(history) > 10:
        context.user_data["chat_history"] = history[-10:]


# ── Хелпер для обработки контакта в ai_book-потоке ───────────────────────────
async def _finish_ai_book_phone(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Вызывается из handle_registration_contact когда ai_book ждёт телефон."""
    from db import get_settings, create_appointment

    ai_book = context.user_data.get("ai_book", {})
    contact = update.message.contact
    ai_book["phone"] = contact.phone_number or ""
    ai_book["step"]  = "confirm"
    context.user_data["ai_book"] = ai_book
    s = await get_settings()

    await update.message.reply_text(
        f"📋 *Проверьте данные:*\n\n"
        f"👤 {ai_book['name']}\n"
        f"📞 {ai_book['phone']}\n"
        f"📱 {ai_book['device']}\n"
        f"🔧 {ai_book['problem']}\n\n"
        f"Подтвердить запись?",
        parse_mode="Markdown",
        reply_markup=_CONFIRM_KB,
    )


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
    # Машина состояний для записи через ИИ
    # ══════════════════════════════════════════════════════════════════════
    ai_book = context.user_data.get("ai_book")

    if ai_book:
        step = ai_book.get("step")

        # Шаг: ждём устройство
        if step == "ask_device":
            ai_book["device"] = user_text
            ai_book["step"]   = "ask_problem"
            context.user_data["ai_book"] = ai_book
            await update.message.reply_text(
                f"📱 Устройство: *{user_text}*\n\nОпишите проблему или вид работы:",
                parse_mode="Markdown",
            )
            return

        # Шаг: ждём проблему
        if step == "ask_problem":
            ai_book["problem"] = user_text
            customer = await get_customer_by_telegram(tid)
            if customer:
                ai_book.update(name=customer.name, phone=customer.phone, step="confirm")
                context.user_data["ai_book"] = ai_book
                await update.message.reply_text(
                    f"📋 *Проверьте данные:*\n\n"
                    f"👤 {ai_book['name']}\n📞 {ai_book['phone']}\n"
                    f"📱 {ai_book['device']}\n🔧 {ai_book['problem']}\n\n"
                    f"Подтвердить запись?",
                    parse_mode="Markdown",
                    reply_markup=_CONFIRM_KB,
                )
            else:
                ai_book["step"] = "ask_name"
                context.user_data["ai_book"] = ai_book
                await update.message.reply_text(
                    "Как вас зовут?",
                    reply_markup=ReplyKeyboardRemove(),
                )
            return

        # Шаг: ждём имя
        if step == "ask_name":
            ai_book["name"] = user_text
            ai_book["step"] = "ask_phone"
            context.user_data["ai_book"] = ai_book
            await update.message.reply_text(
                "Укажите ваш номер телефона:",
                reply_markup=_PHONE_KB,
            )
            return

        # Шаг: ждём телефон (текстом; контакт обрабатывается в start.py)
        if step == "ask_phone":
            ai_book["phone"] = user_text
            ai_book["step"]  = "confirm"
            context.user_data["ai_book"] = ai_book
            await update.message.reply_text(
                f"📋 *Проверьте данные:*\n\n"
                f"👤 {ai_book['name']}\n📞 {ai_book['phone']}\n"
                f"📱 {ai_book['device']}\n🔧 {ai_book['problem']}\n\n"
                f"Подтвердить запись?",
                parse_mode="Markdown",
                reply_markup=_CONFIRM_KB,
            )
            return

        # Шаг: подтверждение
        if step == "confirm":
            if "отмена" in user_text.lower() or "❌" in user_text:
                context.user_data.pop("ai_book", None)
                await update.message.reply_text("Запись отменена.", reply_markup=MAIN_MENU)
                return

            appt = await create_appointment(
                name=ai_book["name"],
                phone=ai_book["phone"],
                device=ai_book["device"],
                problem=ai_book["problem"],
                telegram_chat_id=tid,
            )
            context.user_data.pop("ai_book", None)
            await update.message.reply_text(
                f"✅ *Заявка принята!*\n\n"
                f"Мы свяжемся с вами в ближайшее время.\n\n"
                f"📞 {s.phone}\n"
                f"⏰ {s.working_hours}\n\n"
                f"_Номер вашей записи: #{appt.pk}_",
                parse_mode="Markdown",
                reply_markup=MAIN_MENU,
            )
            return

    # ══════════════════════════════════════════════════════════════════════
    # Определение намерения записаться
    # ══════════════════════════════════════════════════════════════════════
    if _is_booking_intent(user_text) and s.bot_deepseek_key:
        info    = extract_booking_info(user_text, s.bot_deepseek_key)
        device  = info.get("device", "")
        problem = info.get("problem", "")

        ai_book = {"device": device, "problem": problem}

        if not device:
            ai_book["step"] = "ask_device"
            context.user_data["ai_book"] = ai_book
            await update.message.reply_text(
                "📅 Записываю вас!\n\n"
                "Какое устройство нужно отремонтировать?\n"
                "Например: *iPhone 15 Pro*, *Samsung Galaxy S24*",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        if not problem:
            ai_book["step"] = "ask_problem"
            context.user_data["ai_book"] = ai_book
            await update.message.reply_text(
                f"📅 Устройство: *{device}*\n\nОпишите проблему или вид работы:",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        # Устройство и проблема известны
        customer = await get_customer_by_telegram(tid)
        if customer:
            ai_book.update(name=customer.name, phone=customer.phone, step="confirm")
            context.user_data["ai_book"] = ai_book
            await update.message.reply_text(
                f"📋 *Записываю вас:*\n\n"
                f"👤 {customer.name}\n📞 {customer.phone}\n"
                f"📱 {device}\n🔧 {problem}\n\n"
                f"Подтвердить запись?",
                parse_mode="Markdown",
                reply_markup=_CONFIRM_KB,
            )
        else:
            ai_book["step"] = "ask_name"
            context.user_data["ai_book"] = ai_book
            await update.message.reply_text(
                f"📅 Записываю:\n📱 *{device}*\n🔧 *{problem}*\n\nКак вас зовут?",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove(),
            )
        return

    # ══════════════════════════════════════════════════════════════════════
    # Обычный чат с ИИ (с историей)
    # ══════════════════════════════════════════════════════════════════════
    if s.bot_deepseek_key:
        prices_text = await get_all_prices_text()
        history     = context.user_data.get("chat_history", [])

        answer = get_ai_response(
            user_message=user_text,
            system_prompt=s.bot_prompt,
            api_key=s.bot_deepseek_key,
            prices_context=prices_text,
            history=history,
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
