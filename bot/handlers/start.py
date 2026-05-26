"""Команда /start, согласие на ПД, обработка контакта."""
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from telegram.ext import ContextTypes

# ── Клавиатуры ────────────────────────────────────────────────────────────────

# Полное меню для зарегистрированных пользователей
MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💰 Узнать цены"),  KeyboardButton("📅 Записаться")],
        [KeyboardButton("📞 Контакты"),     KeyboardButton("💬 Задать вопрос")],
    ],
    resize_keyboard=True,
)

# Меню для незарегистрированных: только цены + кнопка поделиться контактом
UNREGISTERED_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💰 Узнать цены")],
        [KeyboardButton("📱 Поделиться контактом", request_contact=True)],
    ],
    resize_keyboard=True,
)

# Inline-кнопки согласия на обработку персональных данных
_CONSENT_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Согласен",       callback_data="pd_yes")],
    [InlineKeyboardButton("❌ Не соглашаюсь",  callback_data="pd_no")],
])

_PD_TEXT = (
    "📋 *Обработка персональных данных*\n\n"
    "Для регистрации нам необходимо сохранить ваши персональные данные "
    "(имя и номер телефона) в соответствии с ФЗ-152 «О персональных данных».\n\n"
    "Данные используются исключительно для записи на ремонт и связи с вами. "
    "Вы можете запросить их удаление в любой момент.\n\n"
    "Вы согласны?"
)


# ── Хендлеры ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start — точка входа."""
    from db import get_settings, get_customer_by_telegram

    tid      = update.effective_user.id
    s        = await get_settings()
    customer = await get_customer_by_telegram(tid)

    if customer:
        first = customer.name.split()[0]
        await update.message.reply_text(
            f"👋 С возвращением, *{first}*!\n\nЧем могу помочь?",
            parse_mode="Markdown",
            reply_markup=MAIN_MENU,
        )
    else:
        tg_name = update.effective_user.first_name or ""
        await update.message.reply_text(
            f"👋 Привет{', ' + tg_name if tg_name else ''}!\n\n"
            f"Я бот сервисного центра *{s.company_name}*.\n"
            f"Помогу узнать цены на ремонт и записаться на сервис.\n\n"
            f"🔒 Без регистрации доступны только цены.\n"
            f"📱 Нажмите *«Поделиться контактом»* — это займёт несколько секунд "
            f"и откроет полный функционал: запись на ремонт и чат с мастером.",
            parse_mode="Markdown",
            reply_markup=UNREGISTERED_MENU,
        )


async def handle_registration_contact(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Получаем контакт от пользователя (кнопка «Поделиться контактом»).
    Если уже зарегистрирован — приветствуем.
    Если нет — показываем согласие на ПД.
    Если идёт ai_book и ждём телефон — перекидываем туда.
    """
    from db import get_customer_by_telegram

    tid = update.effective_user.id

    # Если идёт ai_book-запись и ждём телефон — передаём туда
    ai_book = context.user_data.get("ai_book")
    if ai_book and ai_book.get("step") == "ask_phone":
        from handlers.chat import _finish_ai_book_phone
        await _finish_ai_book_phone(update, context)
        return

    contact = update.message.contact

    # Проверяем — может уже зарегистрирован
    existing = await get_customer_by_telegram(tid)
    if existing:
        first = existing.name.split()[0] if existing.name else "Клиент"
        await update.message.reply_text(
            f"👋 *{first}*, вы уже зарегистрированы!\n\nЧем могу помочь?",
            parse_mode="Markdown",
            reply_markup=MAIN_MENU,
        )
        return

    # Сохраняем контакт в сессии, показываем форму согласия на ПД
    context.user_data["pending_contact"] = {
        "first_name": contact.first_name or "",
        "last_name":  contact.last_name  or "",
        "phone":      contact.phone_number or "",
    }
    context.user_data["pending_flow"] = "register"

    await update.message.reply_text(
        _PD_TEXT,
        parse_mode="Markdown",
        reply_markup=_CONSENT_KB,
    )


async def handle_consent_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Обработка inline-кнопок согласия на обработку персональных данных."""
    from db import get_settings, set_pd_consent, get_or_create_customer_from_telegram
    query = update.callback_query
    await query.answer()
    tid = update.effective_user.id

    if query.data == "pd_yes":
        context.user_data["pd_consent"] = True
        await set_pd_consent(tid)
        pending_flow = context.user_data.pop("pending_flow", "register")

        if pending_flow == "register":
            # Создаём клиента из сохранённого контакта
            pending = context.user_data.pop("pending_contact", None)
            s = await get_settings()

            if pending:
                customer, _ = await get_or_create_customer_from_telegram(
                    telegram_id=tid,
                    first_name=pending.get("first_name", ""),
                    last_name=pending.get("last_name", ""),
                    phone=pending.get("phone", ""),
                    pd_consent=True,
                )
                first = customer.name.split()[0] if customer.name else "Клиент"
                await query.edit_message_text(
                    f"✅ *Отлично, {first}!* Регистрация завершена.\n\n"
                    f"Вы добавлены в базу клиентов *{s.company_name}*.\n"
                    f"Теперь вам доступна запись на ремонт и чат с мастером.",
                    parse_mode="Markdown",
                )
                await query.message.reply_text("Чем могу помочь?", reply_markup=MAIN_MENU)
            else:
                # Контакт не сохранился — просим поделиться снова
                await query.edit_message_text(
                    "✅ Согласие принято!\n\nПоделитесь контактом для завершения регистрации:",
                    parse_mode="Markdown",
                )
                await query.message.reply_text("👇", reply_markup=UNREGISTERED_MENU)

        elif pending_flow == "ai_booking":
            await query.edit_message_text(
                "✅ *Спасибо!* Согласие принято. Оформляю запись...",
                parse_mode="Markdown",
            )
            ai_book = context.user_data.get("ai_book", {})
            from handlers.chat import _continue_ai_booking
            await _continue_ai_booking(query.message, context, ai_book)

    elif query.data == "pd_no":
        context.user_data.pop("pending_flow", None)
        context.user_data.pop("pd_consent", None)
        context.user_data.pop("ai_book", None)
        context.user_data.pop("pending_contact", None)
        s = await get_settings()
        await query.edit_message_text(
            "❌ Без согласия на обработку персональных данных регистрация невозможна.\n\n"
            "Если передумаете — нажмите *«Поделиться контактом»* ещё раз.\n\n"
            f"Также вы можете позвонить нам напрямую:\n📞 {s.phone}",
            parse_mode="Markdown",
        )
        await query.message.reply_text(
            "Без регистрации доступны только цены 👇",
            reply_markup=UNREGISTERED_MENU,
        )
