"""Поиск цен по прайс-листу из БД."""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

# Состояние диалога (диапазон 30)
WAITING_PRICE_QUERY = 30


async def ask_price_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🔍 Напишите модель телефона или тип ремонта.\n\n"
        "Примеры: *iPhone 15 Pro*, *Samsung S24*, *экран*, *батарея*",
        parse_mode="Markdown",
    )
    return WAITING_PRICE_QUERY


async def show_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from db import search_prices, get_all_prices_text, get_settings
    from ai import get_ai_response

    query = update.message.text.strip()
    results = await search_prices(query)

    if results:
        lines = [f"💰 *Цены по запросу «{query}»:*\n"]
        for r in results[:15]:
            duration = f" · ⏱ {r['duration']}" if r["duration"] else ""
            lines.append(
                f"📱 *{r['brand']} {r['model']}*\n"
                f"   {r['service']}: *{r['price']}*{duration}"
            )
        lines.append("\n_Точная стоимость уточняется после диагностики._")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    else:
        s = await get_settings()
        if s.bot_deepseek_key or s.bot_ollama_url:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action="typing"
            )
            prices_text = await get_all_prices_text()
            answer = get_ai_response(
                user_message=f"Сколько стоит: {query}?",
                system_prompt=s.bot_prompt,
                api_key=s.bot_deepseek_key,
                prices_context=prices_text,
                base_url=s.bot_ollama_url,
                model=s.bot_ollama_model,
            )
            await update.message.reply_text(answer)
        else:
            await update.message.reply_text(
                f"По запросу *«{query}»* цену не нашли в базе.\n\n"
                f"Позвоните — назовём точную стоимость!\n"
                f"☎️ {s.phone}",
                parse_mode="Markdown",
            )

    return ConversationHandler.END
