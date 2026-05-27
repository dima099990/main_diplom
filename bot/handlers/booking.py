"""Запись на ремонт — пошаговый диалог (только для зарегистрированных)."""
import logging
from vkbottle.bot import Message

import user_data as ud
from keyboards import MAIN_MENU, UNREGISTERED_MENU, CONFIRM_KB, CANCEL_KB, name_kb, phone_kb

logger = logging.getLogger(__name__)

# Состояния
STATE_BOOK_NAME    = "booking_name"
STATE_BOOK_PHONE   = "booking_phone"
STATE_BOOK_DEVICE  = "booking_device"
STATE_BOOK_PROBLEM = "booking_problem"
STATE_BOOK_CONFIRM = "booking_confirm"


async def booking_start(message: Message, uid: int) -> None:
    """Начало записи — только для зарегистрированных."""
    from db import get_customer_by_vk

    customer = await get_customer_by_vk(uid)
    if not customer:
        await message.answer(
            "Для записи на ремонт необходима регистрация.\n\n"
            "Нажмите «Зарегистрироваться» 👇",
            keyboard=UNREGISTERED_MENU,
        )
        return

    cust_name  = customer.name  or ""
    cust_phone = customer.phone or ""

    ud.set_state(uid, STATE_BOOK_NAME,
                 _customer_name=cust_name,
                 _customer_phone=cust_phone)

    if cust_name:
        kb  = name_kb(cust_name)
        msg = (
            f"📅 Запись на ремонт\n\n"
            f"Шаг 1 из 4 — Как вас зовут?\n"
            f"Нажмите кнопку ниже, чтобы использовать имя из профиля, "
            f"или введите другое:"
        )
    else:
        kb  = CANCEL_KB
        msg = "📅 Запись на ремонт\n\nШаг 1 из 4 — Как вас зовут?"

    await message.answer(msg, keyboard=kb)


async def booking_got_name(message: Message, uid: int, text: str) -> None:
    if text == "❌ Отмена":
        ud.clear(uid)
        await message.answer("Запись отменена.", keyboard=MAIN_MENU)
        return

    data = ud.get(uid)
    stored_name = data.get("_customer_name", "")

    # Кнопка «✅ Имя» из профиля → убираем префикс
    if text.startswith("✅ "):
        name = text[2:].strip() or stored_name
    else:
        name = text.strip() or stored_name

    cust_phone = data.get("_customer_phone", "")
    ud.set_state(uid, STATE_BOOK_PHONE, name=name, _customer_phone=cust_phone)

    if cust_phone:
        kb  = phone_kb(cust_phone)
        msg = (
            f"Шаг 2 из 4 — Укажите номер телефона:\n"
            f"Нажмите кнопку ниже, чтобы использовать номер из профиля, "
            f"или введите другой:"
        )
    else:
        kb  = CANCEL_KB
        msg = "Шаг 2 из 4 — Укажите номер телефона:"

    await message.answer(msg, keyboard=kb)


async def booking_got_phone(message: Message, uid: int, text: str) -> None:
    import re

    if text == "❌ Отмена":
        ud.clear(uid)
        await message.answer("Запись отменена.", keyboard=MAIN_MENU)
        return

    data = ud.get(uid)

    cust_phone = data.get("_customer_phone", "")

    # Кнопка «📱 +7...» из профиля
    if text.startswith("📱 ") and cust_phone:
        phone = cust_phone
    else:
        digits = re.sub(r"\D", "", text)
        if len(digits) < 10:
            kb = phone_kb(cust_phone) if cust_phone else CANCEL_KB
            await message.answer(
                "Похоже, это не номер телефона. Введите ещё раз:",
                keyboard=kb,
            )
            return
        phone = text

    ud.set_state(uid, STATE_BOOK_DEVICE, phone=phone)
    await message.answer(
        "Шаг 3 из 4 — Какое устройство нужно отремонтировать?\n\n"
        "Например: iPhone 15 Pro, Samsung Galaxy S24",
        keyboard=CANCEL_KB,
    )


async def booking_got_device(message: Message, uid: int, text: str) -> None:
    if text == "❌ Отмена":
        ud.clear(uid)
        await message.answer("Запись отменена.", keyboard=MAIN_MENU)
        return

    ud.set_state(uid, STATE_BOOK_PROBLEM, device=text)
    await message.answer(
        "Шаг 4 из 4 — Опишите проблему:\n\n"
        "Например: разбит экран, не держит зарядку, не включается",
        keyboard=CANCEL_KB,
    )


async def booking_got_problem(message: Message, uid: int, text: str) -> None:
    if text == "❌ Отмена":
        ud.clear(uid)
        await message.answer("Запись отменена.", keyboard=MAIN_MENU)
        return

    ud.update(uid, problem=text)
    ud.set_state(uid, STATE_BOOK_CONFIRM)

    d = ud.get(uid)
    await message.answer(
        f"📋 Проверьте данные:\n\n"
        f"👤 Имя: {d['name']}\n"
        f"📞 Телефон: {d['phone']}\n"
        f"📱 Устройство: {d['device']}\n"
        f"🔧 Проблема: {d['problem']}\n\n"
        f"Всё верно?",
        keyboard=CONFIRM_KB,
    )


async def booking_got_confirm(message: Message, uid: int, text: str) -> None:
    from db import create_appointment, get_settings

    if text == "❌ Отмена":
        ud.clear(uid)
        await message.answer("Запись отменена.", keyboard=MAIN_MENU)
        return

    if text != "✅ Подтвердить":
        await message.answer(
            "Пожалуйста, нажмите одну из кнопок ниже:",
            keyboard=CONFIRM_KB,
        )
        return

    d = ud.get(uid)
    appt = await create_appointment(
        name=d["name"],
        phone=d["phone"],
        device=d["device"],
        problem=d["problem"],
        vk_user_id=uid,
    )
    ud.clear(uid)
    s = await get_settings()

    await message.answer(
        f"✅ Заявка принята!\n\n"
        f"Мы свяжемся с вами в ближайшее время.\n\n"
        f"📞 {s.phone}\n"
        f"⏰ {s.working_hours}\n\n"
        f"Номер вашей записи: #{appt.pk}",
        keyboard=MAIN_MENU,
    )
