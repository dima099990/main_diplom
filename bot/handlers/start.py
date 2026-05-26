"""Команда /start, согласие на ПД, обработка контакта."""
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from telegram.ext import ContextTypes

# ── Клавиатуры ────────────────────────────────────────────────────────────────

MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💰 Узнать цены"),  KeyboardButton("📅 Записаться")],
        [KeyboardButton("📞 Контакты"),     KeyboardButton("💬 Задать вопрос")],
    ],
    resize_keyboard=True,
)

_SHARE_PHONE_KB = ReplyKeyboardMarkup(
    [[KeyboardButton("📱 Поделиться номером", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True,
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
            f"Чтобы создать карточку клиента и ускорить запись — "
            f"нажмите *«Зарегистрироваться»* 👇",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                [
                    [KeyboardButton("💰 Узнать цены"),  KeyboardButton("📅 Записаться")],
                    [KeyboardButton("📞 Контакты"),     KeyboardButton("💬 Задать вопрос")],
                    [KeyboardButton("📝 Зарегистрироваться")],
                ],
                resize_keyboard=True,
            ),
        )


async def handle_register_button(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Нажатие на «Зарегистрироваться» — сначала показываем согласие на ПД."""
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
    from db import get_settings, set_pd_consent
    query = update.callback_query
    await query.answer()
    tid = update.effective_user.id

    if query.data == "pd_yes":
        context.user_data["pd_consent"] = True
        await set_pd_consent(tid)  # сохраняем в БД (если клиент существует)
        pending_flow = context.user_data.pop("pending_flow", "register")

        if pending_flow == "register":
            await query.edit_message_text(
                "✅ *Спасибо!* Согласие принято.\n\n"
                "Теперь поделитесь номером телефона — нажмите кнопку ниже:",
                parse_mode="Markdown",
            )
            await query.message.reply_text("👇", reply_markup=_SHARE_PHONE_KB)

        elif pending_flow == "ai_booking":
            # Продолжаем умную запись после получения согласия
            await query.edit_message_text(
                "✅ *Спасибо!* Согласие принято. Оформляю запись...",
                parse_mode="Markdown",
            )
            ai_book = context.user_data.get("ai_book", {})
            from handlers.chat import _continue_ai_booking
            await _continue_ai_booking(query.message, context, ai_book)

    elif query.data == "pd_no":
        pending_flow = context.user_data.pop("pending_flow", "register")
        context.user_data.pop("pd_consent", None)
        context.user_data.pop("ai_book", None)
        s = await get_settings()
        await query.edit_message_text(
            "❌ Без согласия на обработку персональных данных регистрация невозможна.\n\n"
            "Если передумаете — нажмите *«Зарегистрироваться»* ещё раз.\n\n"
            f"Также вы можете позвонить нам напрямую:\n📞 {s.phone}",
            parse_mode="Markdown",
        )
        # Показываем кнопку повторной регистрации, чтобы бот не завис
        await query.message.reply_text(
            "Для использования бота необходима регистрация 👇",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📝 Зарегистрироваться")]],
                resize_keyboard=True,
            ),
        )


async def handle_registration_contact(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Получаем контакт от пользователя.
    Если идёт ai_book-запись — перекидываем туда.
    """
    from db import get_settings, get_or_create_customer_from_telegram

    # Если идёт ai_book-запись и ждём телефон — передаём туда
    ai_book = context.user_data.get("ai_book")
    if ai_book and ai_book.get("step") == "ask_phone":
        from handlers.chat import _finish_ai_book_phone
        await _finish_ai_book_phone(update, context)
        return

    contact = update.message.contact
    s       = await get_settings()

    pd_ok = bool(context.user_data.get("pd_consent"))
    customer, is_new = await get_or_create_customer_from_telegram(
        telegram_id=update.effective_user.id,
        first_name=contact.first_name or "",
        last_name=contact.last_name   or "",
        phone=contact.phone_number    or "",
        pd_consent=pd_ok,
    )

    first = customer.name.split()[0] if customer.name else "Клиент"

    if is_new:
        text = (
            f"✅ *Отлично, {first}!*\n\n"
            f"Вы добавлены в базу клиентов *{s.company_name}*.\n"
            f"Теперь запись на ремонт пройдёт быстрее.\n\n"
            f"Чем могу помочь?"
        )
    else:
        text = (
            f"👋 *{first}*, мы вас знаем!\n\n"
            f"Рады снова видеть. Чем могу помочь?"
        )

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=MAIN_MENU)
