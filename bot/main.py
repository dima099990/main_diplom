import sys
import logging
import traceback
from pathlib import Path

# ── Инициализация Django (ПЕРВЫМ, до любых импортов моделей) ──────────────
sys.path.insert(0, str(Path(__file__).parent))
import django_setup  # noqa

# ── Импорты бота ──────────────────────────────────────────────────────────
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# get_settings вызывается синхронно при старте — используем sync-версию напрямую
from db import _get_settings as get_settings_sync

from handlers.start import cmd_start, handle_registration_contact, MAIN_MENU
from handlers.prices import ask_price_query, show_prices, WAITING_PRICE_QUERY
from handlers.booking import (
    start_booking, got_name, got_phone, got_device,
    got_problem, confirm_booking, cancel_booking,
    ASK_NAME, ASK_PHONE, ASK_DEVICE, ASK_PROBLEM, CONFIRM,
)
from handlers.chat import handle_chat, handle_contacts

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирует все необработанные исключения из хендлеров."""
    logger.error("Исключение при обработке обновления:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Произошла ошибка. Попробуйте ещё раз или напишите /start"
        )


def build_app(token: str) -> Application:
    app = Application.builder().token(token).build()

    # Обработчик ошибок — ловит все исключения из хендлеров
    app.add_error_handler(error_handler)

    # /start — проверяет регистрацию, показывает нужный экран
    app.add_handler(CommandHandler("start", cmd_start))

    # ── Запись на ремонт ──────────────────────────────────────────────────
    # Регистрируется ДО глобального обработчика контактов:
    # когда пользователь в шаге ASK_PHONE, его контакт попадает сюда.
    booking_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📅 Записаться$"), start_booking),
            CommandHandler("book", start_booking),
        ],
        states={
            ASK_NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, got_name)],
            ASK_PHONE:   [
                MessageHandler(filters.CONTACT, got_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, got_phone),
            ],
            ASK_DEVICE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, got_device)],
            ASK_PROBLEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_problem)],
            CONFIRM:     [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_booking)],
        },
        fallbacks=[CommandHandler("cancel", cancel_booking)],
        allow_reentry=True,
    )
    app.add_handler(booking_conv)

    # ── Цены ─────────────────────────────────────────────────────────────
    prices_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^💰 Узнать цены$"), ask_price_query),
            CommandHandler("prices", ask_price_query),
        ],
        states={
            WAITING_PRICE_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, show_prices)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_booking)],
        allow_reentry=True,
    )
    app.add_handler(prices_conv)

    # ── Контакт (регистрация через /start) ────────────────────────────────
    # Стоит ПОСЛЕ booking_conv: когда пользователь НЕ в диалоге записи —
    # его контакт попадает сюда (регистрация нового клиента).
    app.add_handler(MessageHandler(filters.CONTACT, handle_registration_contact))

    # ── Контакты компании ─────────────────────────────────────────────────
    app.add_handler(MessageHandler(filters.Regex("^📞 Контакты$"), handle_contacts))

    # ── Свободный чат с ИИ (все остальные сообщения) ─────────────────────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat))

    return app


def main() -> None:
    s = get_settings_sync()
    token = s.bot_token

    if not token:
        logger.error(
            "Токен бота не задан!\n"
            "Откройте CRM → Настройки → Telegram-бот и введите токен."
        )
        sys.exit(1)

    logger.info(f"Запуск бота для '{s.company_name}'...")
    app = build_app(token)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
