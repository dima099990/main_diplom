"""Запись на ремонт — пошаговый диалог (только для зарегистрированных)."""
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from telegram.ext import ContextTypes, ConversationHandler

# Состояния (диапазон 20-24)
ASK_NAME   = 20
ASK_PHONE  = 21
ASK_DEVICE = 22
ASK_PROBLEM = 23
CONFIRM    = 24

# Inline-кнопка подтверждения записи (крепится к сообщению, не к низу экрана)
_CONFIRM_IKB = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("✅ Записать!", callback_data="book_confirm"),
        InlineKeyboardButton("❌ Отмена",   callback_data="book_cancel"),
    ]
])


async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало записи — только для зарегистрированных пользователей."""
    from db import get_customer_by_telegram
    from handlers.start import UNREGISTERED_MENU, MAIN_MENU

    tid = update.effective_user.id
    customer = await get_customer_by_telegram(tid)

    if not customer:
        await update.message.reply_text(
            "Для записи на ремонт необходима регистрация.\n\n"
            "Нажмите *«Поделиться контактом»* 👇",
            parse_mode="Markdown",
            reply_markup=UNREGISTERED_MENU,
        )
        return ConversationHandler.END

    # Зарегистрирован — начинаем запись, подтягиваем данные из профиля
    pd_ok = context.user_data.get("pd_consent", True)  # зарегистрированные уже дали согласие
    context.user_data.clear()
    context.user_data["pd_consent"] = pd_ok

    # Если есть данные клиента — используем их как умолчание
    context.user_data["_customer_name"]  = customer.name  or ""
    context.user_data["_customer_phone"] = customer.phone or ""

    await update.message.reply_text(
        "📅 *Запись на ремонт*\n\n"
        "Шаг 1 из 4 — Как вас зовут?\n"
        f"_(или нажмите Enter чтобы использовать: {customer.name})_"
        if customer.name else
        "📅 *Запись на ремонт*\n\n"
        "Шаг 1 из 4 — Как вас зовут?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_NAME


async def got_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    # Если пользователь ничего не ввёл или написал "-" — используем из профиля
    if text in ("-", ".") and context.user_data.get("_customer_name"):
        context.user_data["name"] = context.user_data["_customer_name"]
    else:
        context.user_data["name"] = text

    await update.message.reply_text(
        "Шаг 2 из 4 — Укажите номер телефона:",
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
