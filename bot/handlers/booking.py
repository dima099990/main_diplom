"""Запись на ремонт — пошаговый диалог (только для зарегистрированных)."""
import logging
from vkbottle.bot import Message

import user_data as ud
from keyboards import MAIN_MENU, UNREGISTERED_MENU, CONFIRM_KB, CANCEL_KB

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

    ud.set_state(uid, STATE_BOOK_NAME,
                 _customer_name=customer.name or "",
                 _customer_phone=customer.phone or "")

    hint = f"\n(или нажмите Enter, чтобы использовать: {customer.name})" if customer.name else ""
    await message.answer(
        f"📅 Запись на ремонт\n\n"
        f"Шаг 1 из 4 — Как вас зовут?{hint}",
        keyboard=CANCEL_KB,
    )


async def booking_got_name(message: Message, uid: int, text: str) -> None:
    if text == "❌ Отмена":
        ud.clear(uid)
        await message.answer("Запись отменена.", keyboard=MAIN_MENU)
        return

    data = ud.get(uid)
    name = data.get("_customer_name", "") if text in ("-", ".", "") else text
    if not name:
        name = text

    ud.set_state(uid, STATE_BOOK_PHONE, name=name)
    await message.answer(
        "Шаг 2 из 4 — Укажите номер телефона:",
        keyboard=CANCEL_KB,
    )


async def booking_got_phone(message: Message, uid: int, text: str) -> None:
    import re

    if text == "❌ Отмена":
        ud.clear(uid)
        await message.answer("Запись отменена.", keyboard=MAIN_MENU)
        return

    data = ud.get(uid)

    # Принимаем кнопку с сохранённым телефоном клиента
    if text == "📱 Мой номер" and data.get("_customer_phone"):
        phone = data["_customer_phone"]
    else:
        digits = re.sub(r"\D", "", text)
        if len(digits) < 10:
            await message.answer(
                "Похоже, это не номер телефона. Введите ещё раз:",
                keyboard=CANCEL_KB,
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
