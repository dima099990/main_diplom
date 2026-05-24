"""Запись на ремонт — пошаговый диалог."""
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

# Состояния (диапазон 20-24)
ASK_NAME = 20
ASK_PHONE = 21
ASK_DEVICE = 22
ASK_PROBLEM = 23
CONFIRM = 24


async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "📅 *Запись на ремонт*\n\nШаг 1 из 4 — Как вас зовут?",
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
        reply_markup=ReplyKeyboardMarkup(
            [["✅ Да, записать!", "❌ Отмена"]],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )
    return CONFIRM


async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from db import create_appointment, get_settings
    from handlers.start import MAIN_MENU

    if update.message.text.strip() == "❌ Отмена":
        await update.message.reply_text("Запись отменена.", reply_markup=MAIN_MENU)
        context.user_data.clear()
        return ConversationHandler.END

    d = context.user_data
    appt = await create_appointment(
        name=d["name"],
        phone=d["phone"],
        device=d["device"],
        problem=d["problem"],
        telegram_chat_id=update.effective_user.id,
    )

    s = await get_settings()
    await update.message.reply_text(
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
