"""Свободный чат с ИИ-ассистентом и раздел «Контакты»."""
from telegram import Update
from telegram.ext import ContextTypes


async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from db import get_settings, get_all_prices_text
    from ai import get_ai_response

    user_text = update.message.text.strip()
    s = await get_settings()

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    if s.bot_deepseek_key or s.bot_ollama_url:
        prices_text = await get_all_prices_text()
        answer = get_ai_response(
            user_message=user_text,
            system_prompt=s.bot_prompt,
            api_key=s.bot_deepseek_key,
            prices_context=prices_text,
            base_url=s.bot_ollama_url,
            model=s.bot_ollama_model,
        )
    else:
        answer = (
            f"Задайте вопрос или позвоните нам напрямую:\n"
            f"📞 {s.phone}\n"
            f"⏰ {s.working_hours}"
        )

    await update.message.reply_text(answer)


async def handle_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from db import get_settings
    s = await get_settings()
    await update.message.reply_text(
        f"📍 *{s.company_name}*\n\n"
        f"📞 {s.phone}\n"
        f"⏰ {s.working_hours}\n"
        f"📍 {s.address}",
        parse_mode="Markdown",
    )
