"""ИИ-ассистент для бота (Groq API)."""
from __future__ import annotations
import re
import json
import logging
import httpx
from openai import OpenAI, AuthenticationError, RateLimitError, APIConnectionError, APIStatusError
from proxy import get_active_proxy

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL    = "llama-3.3-70b-versatile"


def get_ai_response(
    user_message: str,
    system_prompt: str,
    api_key: str = "",
    prices_context: str = "",
    history: list | None = None,
) -> str:
    """
    Отправляет сообщение в Groq и возвращает ответ.
    history — список {"role": "user"/"assistant", "content": "..."}, последние 5 обменов.
    """
    if not api_key:
        return "ИИ-ассистент не настроен. Позвоните нам — ответим на все вопросы!"

    proxy_url = get_active_proxy()
    http_client = httpx.Client(proxy=proxy_url) if proxy_url else None
    client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL, http_client=http_client)

    full_system = system_prompt or "Ты помощник сервисного центра по ремонту телефонов."
    if prices_context:
        # Ограничиваем размер прайс-листа, чтобы не превысить лимит токенов Groq Free Tier
        if len(prices_context) > 6000:
            prices_context = prices_context[:6000] + "\n... (прайс сокращён, уточните у оператора)"
        full_system += f"\n\n=== АКТУАЛЬНЫЙ ПРАЙС-ЛИСТ ===\n{prices_context}"

    messages = [{"role": "system", "content": full_system}]
    if history:
        messages.extend(history[-6:])   # последние 3 обмена = 6 сообщений (экономим токены)
    messages.append({"role": "user", "content": user_message})

    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=600,
            temperature=0.7,
        )
        return resp.choices[0].message.content or "Не удалось получить ответ."
    except AuthenticationError as e:
        logger.error(f"Groq AuthenticationError: {e}")
        return "❌ Неверный Groq API ключ. Проверьте настройки в CRM."
    except RateLimitError as e:
        logger.error(f"Groq RateLimitError: {e}")
        return "⏳ Слишком много запросов к ИИ. Попробуйте через минуту."
    except APIConnectionError as e:
        logger.error(f"Groq APIConnectionError: {e}")
        return "🔌 Нет соединения с сервером ИИ. Позвоните нам напрямую!"
    except APIStatusError as e:
        logger.error(f"Groq APIStatusError {e.status_code}: {e.message}")
        if e.status_code == 413:
            return "⚠️ Слишком большой запрос. Попробуйте задать более короткий вопрос."
        return "🔌 Ошибка сервера ИИ. Позвоните нам — ответим на все вопросы!"
    except Exception as e:
        logger.error(f"Groq unexpected error: {type(e).__name__}: {e}", exc_info=True)
        return "🔌 Нейросеть временно недоступна. Позвоните нам — ответим на все вопросы!"


def extract_booking_info(text: str, api_key: str) -> dict:
    """
    Извлекает из сообщения клиента все поля для записи:
    device, problem, name, phone, date (YYYY-MM-DD), time (HH:MM).
    Пустые строки если поле не найдено.
    """
    empty = {"device": "", "problem": "", "name": "", "phone": "", "date": "", "time": ""}
    if not api_key:
        return empty

    from datetime import date as _date
    today_str = _date.today().isoformat()

    proxy_url = get_active_proxy()
    http_client = httpx.Client(proxy=proxy_url) if proxy_url else None
    client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL, http_client=http_client)

    system = (
        f"Сегодня {today_str}. "
        "Ты — парсер данных для сервисного центра по ремонту телефонов. "
        "Извлеки из сообщения клиента следующие поля:\n"
        "  device  — устройство (марка и модель, например 'iPhone X')\n"
        "  problem — проблема или вид работы (например 'не включается')\n"
        "  name    — имя клиента\n"
        "  phone   — номер телефона (в том виде, как написано)\n"
        f"  date    — дата в формате YYYY-MM-DD (переведи относительные: "
        f"'сегодня'={today_str}, 'завтра', 'послезавтра', 'в пятницу', '20 июля' и т.д.)\n"
        "  time    — время в формате HH:MM (24-часовой)\n\n"
        "Ответь ТОЛЬКО валидным JSON без пояснений.\n"
        f'Пример: {{"device":"iPhone X","problem":"не включается","name":"Дмитрий",'
        f'"phone":"","date":"{today_str}","time":"16:00"}}\n'
        "Если поле не указано — оставь пустую строку."
    )

    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            max_tokens=180,
            temperature=0.1,
        )
        content = resp.choices[0].message.content or "{}"
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return {
                "device":  str(data.get("device",  "")).strip(),
                "problem": str(data.get("problem", "")).strip(),
                "name":    str(data.get("name",    "")).strip(),
                "phone":   str(data.get("phone",   "")).strip(),
                "date":    str(data.get("date",    "")).strip(),
                "time":    str(data.get("time",    "")).strip(),
            }
    except Exception:
        pass
    return empty
