"""ИИ-ассистент для бота (Groq API через httpx, без openai-пакета)."""
from __future__ import annotations
import re
import json
import logging
import httpx

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

# Цепочка моделей: если основная исчерпала суточный лимит токенов (TPD),
# автоматически переключаемся на следующую — у каждой свой независимый лимит.
GROQ_MODELS = [
    "llama-3.3-70b-versatile",   # основная: высокое качество
    "llama-3.1-8b-instant",      # резерв 1: быстрая, экономичная
    "gemma2-9b-it",              # резерв 2: Google Gemma 2
    "mixtral-8x7b-32768",        # резерв 3: Mistral
]


def _groq_request(
    api_key: str,
    messages: list[dict],
    model: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """Синхронный запрос к Groq API. Возвращает текст ответа."""
    resp = httpx.post(
        GROQ_BASE_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        timeout=30,
    )
    if resp.status_code == 429:
        raise _RateLimitError(resp.text)
    if resp.status_code in (401, 403):
        raise _AuthError(f"HTTP {resp.status_code}: {resp.text}")
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"] or ""


class _RateLimitError(Exception):
    pass

class _AuthError(Exception):
    pass


def _try_models(
    api_key: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
) -> tuple[str, str]:
    """
    Пробует модели по порядку из GROQ_MODELS.
    Возвращает (content, model_used).
    """
    last_exc: Exception | None = None
    for model in GROQ_MODELS:
        try:
            content = _groq_request(api_key, messages, model, max_tokens, temperature)
            if model != GROQ_MODELS[0]:
                logger.info(f"Используем резервную модель: {model}")
            return content, model
        except _RateLimitError as e:
            logger.warning(f"Модель {model} исчерпала лимит, переключаемся... ({e})")
            last_exc = e
            continue
    raise last_exc  # type: ignore[misc]


def get_ai_response(
    user_message: str,
    system_prompt: str,
    api_key: str = "",
    prices_context: str = "",
    history: list | None = None,
) -> str:
    if not api_key:
        return "ИИ-ассистент не настроен. Позвоните нам — ответим на все вопросы!"

    full_system = system_prompt or "Ты помощник сервисного центра по ремонту телефонов."
    if prices_context:
        if len(prices_context) > 6000:
            prices_context = prices_context[:6000] + "\n... (прайс сокращён, уточните у оператора)"
        full_system += f"\n\n=== АКТУАЛЬНЫЙ ПРАЙС-ЛИСТ ===\n{prices_context}"

    messages: list[dict] = [{"role": "system", "content": full_system}]
    if history:
        messages.extend(history[-6:])
    messages.append({"role": "user", "content": user_message})

    try:
        content, _ = _try_models(api_key, messages, max_tokens=600, temperature=0.7)
        return content or "Не удалось получить ответ."
    except _RateLimitError as e:
        logger.error(f"Все модели Groq исчерпали лимит: {e}")
        return (
            "⏳ ИИ-ассистент временно недоступен — суточный лимит запросов исчерпан.\n\n"
            "Позвоните нам напрямую, мы всё расскажем! 📞"
        )
    except _AuthError as e:
        logger.error(f"Groq AuthError (401/403): {e}")
        return (
            "⚠️ ИИ-ассистент временно недоступен.\n\n"
            "Позвоните нам — ответим на все вопросы! 📞"
        )
    except httpx.ConnectError as e:
        logger.error(f"Groq ConnectError: {e}")
        return "🔌 Нет соединения с сервером ИИ. Позвоните нам напрямую!"
    except Exception as e:
        logger.error(f"Groq error: {type(e).__name__}: {e}", exc_info=True)
        return "🔌 Нейросеть временно недоступна. Позвоните нам — ответим на все вопросы!"


def estimate_buyout_price(
    device: str,
    memory: str,
    screen: str,
    battery: str,
    body: str,
    api_key: str,
) -> str:
    """
    Оценивает стоимость выкупа б/у смартфона по его характеристикам.
    Возвращает текст с диапазоном цен и кратким пояснением.
    """
    if not api_key:
        return "ИИ-оценщик не настроен."

    # Убираем emoji-префиксы кнопок для чистоты промпта
    def clean(val: str) -> str:
        for prefix in ("✨ ", "👍 ", "😐 ", "💔 ", "🔋 ", "🪫 ", "❓ "):
            if val.startswith(prefix):
                return val[len(prefix):]
        return val

    system = (
        "Ты — эксперт по скупке б/у смартфонов в сервисном центре в России. "
        "Оценивай реалистично по актуальным рыночным ценам (2025 год, цены в рублях). "
        "Выкупная цена обычно составляет 40–65% от рыночной стоимости аналогичного б/у устройства — "
        "учитывай это при расчёте. "
        "Учитывай все параметры: модель, память, состояние экрана, аккумулятора и корпуса. "
        "Давай конкретный диапазон цен выкупа (например: 'Ориентировочная стоимость выкупа: от 8 000 до 11 000 ₽'). "
        "Коротко объясни, что влияет на цену (1–2 предложения). "
        "Отвечай только оценкой и кратким пояснением — без лишних оговорок и дисклеймеров."
    )

    user_msg = (
        f"Устройство: {device}\n"
        f"Объём памяти: {memory}\n"
        f"Состояние экрана: {clean(screen)}\n"
        f"Ёмкость аккумулятора: {clean(battery)}\n"
        f"Состояние корпуса: {clean(body)}\n\n"
        "Оцени стоимость выкупа этого устройства нашим сервисным центром."
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user_msg},
    ]

    try:
        content, _ = _try_models(api_key, messages, max_tokens=300, temperature=0.3)
        return content or "Не удалось получить оценку."
    except _RateLimitError:
        logger.warning("Все модели Groq исчерпали лимит при оценке выкупа")
        return (
            "⏳ ИИ-оценщик временно недоступен — суточный лимит запросов исчерпан. "
            "Обратитесь к нам напрямую, мастер оценит устройство бесплатно!"
        )
    except _AuthError as e:
        logger.error(f"Groq AuthError при оценке выкупа: {e}")
        return "⚠️ Сервис оценки временно недоступен. Обратитесь к нам напрямую."
    except Exception as e:
        logger.error(f"estimate_buyout_price error: {type(e).__name__}: {e}", exc_info=True)
        return "Не удалось получить автоматическую оценку. Обратитесь к нам напрямую."


def extract_booking_info(text: str, api_key: str) -> dict:
    """
    Извлекает из сообщения клиента поля для записи:
    device, problem, name, phone, date (YYYY-MM-DD), time (HH:MM).
    """
    empty = {"device": "", "problem": "", "name": "", "phone": "", "date": "", "time": ""}
    if not api_key:
        return empty

    from datetime import date as _date
    today_str = _date.today().isoformat()

    system = (
        f"Сегодня {today_str}. "
        "Ты — парсер данных для сервисного центра по ремонту телефонов. "
        "Извлеки из сообщения клиента следующие поля:\n"
        "  device  — устройство (марка и модель, например 'iPhone X')\n"
        "  problem — проблема или вид работы (например 'не включается')\n"
        "  name    — имя клиента\n"
        "  phone   — номер телефона (в том виде, как написано)\n"
        f"  date    — дата в формате YYYY-MM-DD\n"
        "  time    — время в формате HH:MM (24-часовой)\n\n"
        "Ответь ТОЛЬКО валидным JSON без пояснений.\n"
        f'Пример: {{"device":"iPhone X","problem":"не включается","name":"Дмитрий",'
        f'"phone":"","date":"{today_str}","time":"16:00"}}\n'
        "Если поле не указано — оставь пустую строку."
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": text},
    ]

    try:
        content, _ = _try_models(api_key, messages, max_tokens=180, temperature=0.1)
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
    except _RateLimitError:
        logger.warning("Все модели Groq исчерпали лимит при извлечении данных записи")
    except Exception:
        pass
    return empty
