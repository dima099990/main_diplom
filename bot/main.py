import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import django_setup  # noqa

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from db import _get_settings as get_settings_sync
from proxy import find_working_proxy
from handlers.start import cmd_start, handle_registration_contact
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
    logger.error("Исключение при обработке обновления:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Произошла ошибка. Попробуйте ещё раз или напишите /start"
        )


def build_app(token: str, proxy_url: str | None = None) -> Application:
    builder = Application.builder().token(token)
    if proxy_url:
        builder = builder.proxy(proxy_url).get_updates_proxy(proxy_url)
    app = builder.build()
    app.add_error_handler(error_handler)

    app.add_handler(CommandHandler("start", cmd_start))

    app.add_handler(ConversationHandler(
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
    ))

    app.add_handler(ConversationHandler(
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
    ))

    app.add_handler(MessageHandler(filters.CONTACT, handle_registration_contact))
    app.add_handler(MessageHandler(filters.Regex("^📞 Контакты$"), handle_contacts))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat))

    return app


def main() -> None:
    s = get_settings_sync()
    if not s.bot_token:
        logger.error("Токен бота не задан! CRM → Настройки → Telegram-бот")
        sys.exit(1)
    logger.info(f"Запуск бота для '{s.company_name}'...")
    proxy_url = find_working_proxy()
    build_app(s.bot_token, proxy_url).run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
