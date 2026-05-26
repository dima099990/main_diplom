"""Запись на ремонт — пошаговый диалог."""
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from telegram.ext import ContextTypes, ConversationHandler

# Состояния (диапазон 20-25)
AWAIT_CONSENT = 20   # ожидание согласия на ПД
ASK_NAME      = 21
ASK_PHONE     = 22
ASK_DEVICE    = 23
ASK_PROBLEM   = 24
CONFIRM       = 25

# Inline-кнопка подтверждения записи (крепится к сообщению)
_CONFIRM_IKB = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("✅ Записать!", callback_data="book_confirm"),
        InlineKeyboardButton("❌ Отмена",   callback_data="book_cancel"),
    ]
])

# Inline-кнопки согласия на ПД (специфичные для шага booking, чтобы не конфликтовать с глобальным pd_*)
_BOOKING_PD_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Согласен",      callback_data="bpd_yes")],
    [InlineKeyboardButton("❌ Не соглашаюсь", callback_data="bpd_no")],
])

_PD_TEXT = (
    "📋 *Обработка персональных данных*\n\n"
    "Для записи на ремонт нам необходимо сохранить ваши персональные данные "
    "(имя и номер телефона) в соответствии с ФЗ-152 «О персональных данных».\n\n"
    "Данные используются исключительно для связи с вами и организации ремонта. "
    "Вы можете запросить их удаление в любой момент.\n\n"
    "Вы согласны?"
)


async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from db import get_pd_consent

    tid = update.effective_user.id

    # Проверяем согласие на ПД (сессия → БД)
    has_consent = context.user_data.get("pd_consent") or await get_pd_consent(tid)
    if has_consent:
        context.user_data["pd_consent"] = True
    else:
        # Показываем форму согласия, ждём ответа
        await update.message.reply_text(
            _PD_TEXT,
            parse_mode="Markdown",
            reply_markup=_BOOKING_PD_KB,
        )
        return AWAIT_CONSENT

    return await _do_start_booking(update, context)


async def handle_booking_consent(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Обработка согласия на ПД внутри ConversationHandler (bpd_yes / bpd_no)."""
    from db import set_pd_consent
    from handlers.start import MAIN_MENU

    query = update.callback_query
    await query.answer()
    tid = update.effective_user.id

    if query.data == "bpd_yes":
        context.user_data["pd_consent"] = True
        await set_pd_consent(tid)
        await query.edit_message_text("✅ Согласие принято! Начинаем запись...")
        await query.message.reply_text(
            "📅 *Запись на ремонт*\n\n"
            "Шаг 1 из 4 — Как вас зовут?",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ASK_NAME

    else:  # bpd_no
        await query.edit_message_text(
            "❌ Без согласия на обработку данных запись невозможна.\n\n"
            "Если хотите записаться — позвоните нам напрямую.",
        )
        await query.message.reply_text("Чем ещё могу помочь?", reply_markup=MAIN_MENU)
        return ConversationHandler.END


async def _do_start_booking(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Внутренний старт диалога после проверки согласия."""
    pd_ok = context.user_data.get("pd_consent", False)
    context.user_data.clear()
    context.user_data["pd_consent"] = pd_ok

    await update.message.reply_text(
        "📅 *Запись на ремонт*\n\n"
        "Шаг 1 из 4 — Как вас зовут?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_NAME


async def got_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text(
        "Шаг 2 из 4 — Укажите ваш номер телефона:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Поделиться номером", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )
    return ASK_PHONE


async def got_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.contact:
        context.user_data["phone"] = update.message.contact.phone_number
    else:
        context.user_data["phone"] = update.message.text.strip()
    await update.message.reply_text(
        "Шаг 3 из 4 — Какое устройство нужно отремонтировать?\n\n"
        "Например: *iPhone 15 Pro*, *Samsung Galaxy S24*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_DEVICE


async def got_device(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["device"] = update.message.text.strip()
    await update.message.reply_text(
        "Шаг 4 из 4 — Опишите проблему:\n\n"
        "Например: *разбит экран*, *не держит зарядку*, *не включается*",
        parse_mode="Markdown",
    )
    return ASK_PROBLEM


async def got_problem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["problem"] = update.message.text.strip()
    d = context.user_data
    await update.message.reply_text(
        "📋 *Проверьте данные:*\n\n"
        f"👤 Имя: *{d['name']}*\n"
        f"📞 Телефон: *{d['phone']}*\n"
        f"📱 Устройство: *{d['device']}*\n"
        f"🔧 Проблема: *{d['problem']}*\n\n"
        "Всё верно?",
        parse_mode="Markdown",
        reply_markup=_CONFIRM_IKB,
    )
    return CONFIRM


async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает inline-кнопки подтверждения записи."""
    from db import create_appointment, get_settings
    from handlers.start import MAIN_MENU

    query = update.callback_query
    await query.answer()

    if query.data == "book_cancel":
        await query.edit_message_text("❌ Запись отменена.")
        await query.message.reply_text("Чем ещё могу помочь?", reply_markup=MAIN_MENU)
        context.user_data.clear()
        return ConversationHandler.END

    # book_confirm
    d = context.user_data
    appt = await create_appointment(
        name=d["name"],
        phone=d["phone"],
        device=d["device"],
        problem=d["problem"],
        telegram_chat_id=update.effective_user.id,
    )

    s = await get_settings()
    await query.edit_message_text(
        f"📋 *Данные записи:*\n\n"
        f"👤 {d['name']}\n"
        f"📞 {d['phone']}\n"
        f"📱 {d['device']}\n"
        f"🔧 {d['problem']}",
        parse_mode="Markdown",
    )
    await query.message.reply_text(
        f"✅ *Заявка принята!*\n\n"
        f"Мы свяжемся с вами в ближайшее время.\n\n"
        f"📞 {s.phone}\n"
        f"⏰ {s.working_hours}\n\n"
        f"_Номер вашей записи: #{appt.pk}_",
        parse_mode="Markdown",
        reply_markup=MAIN_MENU,
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from handlers.start import MAIN_MENU
    await update.message.reply_text("Отменено.", reply_markup=MAIN_MENU)
    context.user_data.clear()
    return ConversationHandler.END
