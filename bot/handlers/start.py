"""Команда /start и обработка контакта при регистрации."""
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

# ── Клавиатуры ────────────────────────────────────────────────────────────

MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💰 Узнать цены"),  KeyboardButton("📅 Записаться")],
        [KeyboardButton("📞 Контакты"),     KeyboardButton("💬 Задать вопрос")],
    ],
    resize_keyboard=True,
)

# Меню для новых пользователей — всё то же самое + кнопка регистрации
NEW_USER_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💰 Узнать цены"),  KeyboardButton("📅 Записаться")],
        [KeyboardButton("📞 Контакты"),     KeyboardButton("💬 Задать вопрос")],
        [KeyboardButton("📱 Зарегистрироваться", request_contact=True)],
    ],
    resize_keyboard=True,
)


# ── Хендлеры ──────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start — точка входа."""
    from db import get_settings, get_customer_by_telegram

    tid = update.effective_user.id
    s   = await get_settings()
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
            f"Нажмите *«Зарегистрироваться»* чтобы поделиться номером "
            f"и мы создадим вашу карточку клиента. "
            f"Или сразу выберите нужный раздел 👇",
            parse_mode="Markdown",
            reply_markup=NEW_USER_MENU,
        )


async def handle_registration_contact(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Получаем контакт (кнопка «Зарегистрироваться» из /start).
    Если в процессе ai_book-записи — перекидываем туда.
    """
    from db import get_settings, get_or_create_customer_from_telegram

    # Если идёт ai_book-запись и ждём телефон — передаём туда
    ai_book = context.user_data.get("ai_book")
    if ai_book and ai_book.get("step") == "ask_phone":
        from handlers.chat import _finish_ai_book_phone
        await _finish_ai_book_phone(update, context)
        return

    contact  = update.message.contact
    s        = await get_settings()

    customer, is_new = await get_or_create_customer_from_telegram(
        telegram_id=update.effective_user.id,
        first_name=contact.first_name or "",
        last_name=contact.last_name  or "",
        phone=contact.phone_number   or "",
    )

    first = customer.name.split()[0] if customer.name else "Клиент"

    if is_new:
        text = (
            f"✅ *Отлично, {first}!*\n\n"
            f"Вы добавлены в базу клиентов *{s.company_name}*.\n"
            f"Теперь можем записать вас на ремонт или узнать цены.\n\n"
            f"Чем могу помочь?"
        )
    else:
        text = (
            f"👋 *{first}*, мы вас знаем!\n\n"
            f"Рады снова видеть. Чем могу помочь?"
        )

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=MAIN_MENU)
