"""
ИИ-ассистент для бота.

Поддерживает два режима:
  1. DeepSeek API (облако) — задаётся api_key в настройках CRM
  2. Ollama (локально)     — задаётся base_url вида http://localhost:11434/v1

Приоритет: если задан api_key → DeepSeek API, иначе → Ollama (если задан base_url).
"""
from __future__ import annotations
from openai import OpenAI


def get_ai_response(
    user_message: str,
    system_prompt: str,
    api_key: str = "",
    prices_context: str = "",
    base_url: str = "",
    model: str = "",
) -> str:
    """
    Отправляет сообщение в LLM и возвращает ответ.

    Режимы:
      - api_key задан                → DeepSeek API (https://api.deepseek.com)
      - base_url задан, api_key нет  → Ollama или любой OpenAI-совместимый сервер
      - ничего не задано             → возвращает заглушку
    """
    # Определяем куда идём
    if api_key:
        _base_url = base_url or "https://api.deepseek.com"
        _api_key = api_key
        _model = model or "deepseek-chat"
    elif base_url:
        _base_url = base_url
        _api_key = "ollama"   # Ollama принимает любую строку
        _model = model or "deepseek-r1:7b"
    else:
        return "ИИ-ассистент не настроен. Позвоните нам — ответим на все вопросы!"

    client = OpenAI(api_key=_api_key, base_url=_base_url)

    full_system = system_prompt or "Ты помощник сервисного центра по ремонту телефонов."
    if prices_context:
        full_system += f"\n\n=== АКТУАЛЬНЫЙ ПРАЙС-ЛИСТ ===\n{prices_context}"

    try:
        resp = client.chat.completions.create(
            model=_model,
            messages=[
                {"role": "system", "content": full_system},
                {"role": "user",   "content": user_message},
            ],
            max_tokens=600,
            temperature=0.7,
        )
        # DeepSeek-R1 оборачивает рассуждения в <think>...</think> — убираем их
        text = resp.choices[0].message.content or ""
        if "<think>" in text and "</think>" in text:
            start = text.find("</think>")
            text = text[start + len("</think>"):].strip()
        return text or "Не удалось получить ответ."
    except Exception as e:
        return f"Ошибка ИИ: {e}\nПозвоните нам — ответим на все вопросы!"
