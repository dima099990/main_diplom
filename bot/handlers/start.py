"""Приветствие, регистрация через VK."""
import logging
import re
from vkbottle.bot import Message

import user_data as ud
from keyboards import MAIN_MENU, UNREGISTERED_MENU, CONSENT_KB, CANCEL_KB

logger = logging.getLogger(__name__)

# Состояния регистрации
STATE_REG_PHONE   = "reg_phone"
STATE_REG_CONSENT = "reg_consent"

PD_TEXT = (
    "📋 Обработка персональных данных\n\n"
    "Для регистрации нам необходимо сохранить ваши персональные данные "
    "(имя и номер телефона) в соответствии с ФЗ-152 «О персональных данных».\n\n"
    "Данные используются исключительно для записи на ремонт и связи с вами. "
    "Вы можете запросить их удаление в любой момент.\n\n"
    "Вы согласны на обработку данных?"
)


async def cmd_start(message: Message, uid: int) -> None:
    """/start или нажатие «Начать»."""
    from db import get_settings, get_customer_by_vk

    s        = await get_settings()
    customer = await get_customer_by_vk(uid)

    if customer:
        first = customer.name.split()[0] if customer.name else "Клиент"
        await message.answer(
            f"👋 С возвращением, {first}!\n\nЧем могу помочь?",
            keyboard=MAIN_MENU,
        )
    else:
        try:
            users = await message.ctx_api.users.get(user_ids=[uid])
            vk_name = users[0].first_name if users else ""
        except Exception:
            vk_name = ""

        await message.answer(
            f"👋 Привет{', ' + vk_name if vk_name else ''}!\n\n"
            f"Я бот сервисного центра {s.company_name}.\n"
            f"Помогу узнать цены на ремонт и записаться на сервис.\n\n"
            f"🔒 Без регистрации доступны только цены.\n"
            f"📝 Нажмите «Зарегистрироваться» — это займёт несколько секунд "
            f"и откроет полный функционал: запись на ремонт и чат с мастером.",
            keyboard=UNREGISTERED_MENU,
        )


async def reg_ask_phone(message: Message, uid: int) -> None:
    """Начало регистрации — запрашиваем телефон. Имя берём из VK API."""
    from db import get_customer_by_vk

    customer = await get_customer_by_vk(uid)
    if customer:
        first = customer.name.split()[0] if customer.name else "Клиент"
        await message.answer(
            f"👋 {first}, вы уже зарегистрированы!\n\nЧем могу помочь?",
            keyboard=MAIN_MENU,
        )
        return

    # Получаем имя из VK API
    try:
        users = await message.ctx_api.users.get(user_ids=[uid])
        u = users[0]
        first_name = u.first_name or ""
        last_name  = u.last_name  or ""
    except Exception:
        first_name = ""
        last_name  = ""

    full_name = " ".join(p for p in [first_name, last_name] if p).strip()
    ud.set_state(uid, STATE_REG_PHONE, vk_name=full_name)

    name_line = f"Ваше имя из ВКонтакте: {full_name}\n\n" if full_name else ""
    await message.answer(
        f"📝 Регистрация\n\n{name_line}Укажите номер телефона для связи:",
        keyboard=CANCEL_KB,
    )


async def reg_got_phone(message: Message, uid: int, text: str) -> None:
    """Получили номер телефона — показываем согласие на ПД."""
    if text == "❌ Отмена":
        ud.clear(uid)
        await message.answer("Регистрация отменена.", keyboard=UNREGISTERED_MENU)
        return

    digits = re.sub(r"\D", "", text)
    if len(digits) < 10:
        await message.answer(
            "Похоже, это не номер телефона. Пожалуйста, введите корректный номер:",
            keyboard=CANCEL_KB,
        )
        return

    phone = f"+{digits}" if not text.startswith("+") else text
    ud.update(uid, vk_phone=phone)
    ud.set_state(uid, STATE_REG_CONSENT)

    await message.answer(PD_TEXT, keyboard=CONSENT_KB)


async def reg_got_consent(message: Message, uid: int, text: str) -> None:
    """Пользователь ответил на согласие ПД."""
    from db import get_settings, get_or_create_customer_from_vk

    data = ud.get(uid)

    if text == "✅ Согласен":
        s = await get_settings()
        customer, _ = await get_or_create_customer_from_vk(
            vk_id=uid,
            name=data.get("vk_name", "Клиент"),
            phone=data.get("vk_phone", ""),
            pd_consent=True,
        )
        ud.clear(uid)
        first = customer.name.split()[0] if customer.name else "Клиент"
        await message.answer(
            f"✅ Отлично, {first}! Регистрация завершена.\n\n"
            f"Вы добавлены в базу клиентов {s.company_name}.\n"
            f"Теперь вам доступна запись на ремонт и чат с мастером.",
            keyboard=MAIN_MENU,
        )

    elif text == "❌ Не соглашаюсь":
        s = await get_settings()
        ud.clear(uid)
        await message.answer(
            "❌ Без согласия на обработку персональных данных регистрация невозможна.\n\n"
            "Если передумаете — нажмите «Зарегистрироваться» ещё раз.\n\n"
            f"Также вы можете позвонить нам напрямую:\n📞 {s.phone}",
            keyboard=UNREGISTERED_MENU,
        )

    else:
        await message.answer(
            "Пожалуйста, нажмите одну из кнопок ниже:",
            keyboard=CONSENT_KB,
        )
