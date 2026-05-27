"""VK keyboard definitions for the bot."""
from datetime import date, timedelta
from vkbottle import Keyboard, Text, KeyboardButtonColor

# ── Постоянные клавиатуры ─────────────────────────────────────────────────────

MAIN_MENU = (
    Keyboard(one_time=False)
    .add(Text("💰 Узнать цены"),   color=KeyboardButtonColor.PRIMARY)
    .add(Text("📅 Записаться"),    color=KeyboardButtonColor.POSITIVE)
    .row()
    .add(Text("📞 Контакты"),      color=KeyboardButtonColor.SECONDARY)
    .add(Text("📦 Выкуп"),         color=KeyboardButtonColor.SECONDARY)
    .get_json()
)

UNREGISTERED_MENU = (
    Keyboard(one_time=False)
    .add(Text("💰 Узнать цены"),         color=KeyboardButtonColor.PRIMARY)
    .row()
    .add(Text("📝 Зарегистрироваться"),  color=KeyboardButtonColor.POSITIVE)
    .get_json()
)

# ── Одноразовые клавиатуры (исчезают после нажатия) ──────────────────────────

CONSENT_KB = (
    Keyboard(one_time=True)
    .add(Text("✅ Согласен"),        color=KeyboardButtonColor.POSITIVE)
    .add(Text("❌ Не соглашаюсь"),   color=KeyboardButtonColor.NEGATIVE)
    .get_json()
)

CONFIRM_KB = (
    Keyboard(one_time=True)
    .add(Text("✅ Подтвердить"),     color=KeyboardButtonColor.POSITIVE)
    .add(Text("❌ Отмена"),          color=KeyboardButtonColor.NEGATIVE)
    .get_json()
)

SKIP_KB = (
    Keyboard(one_time=True)
    .add(Text("⏭ Пропустить"), color=KeyboardButtonColor.SECONDARY)
    .get_json()
)

CANCEL_KB = (
    Keyboard(one_time=True)
    .add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE)
    .get_json()
)

# ── Клавиатуры выкупа устройств ───────────────────────────────────────────────

MEMORY_KB = (
    Keyboard(one_time=True)
    .add(Text("64 ГБ"),  color=KeyboardButtonColor.SECONDARY)
    .add(Text("128 ГБ"), color=KeyboardButtonColor.SECONDARY)
    .row()
    .add(Text("256 ГБ"), color=KeyboardButtonColor.SECONDARY)
    .add(Text("512 ГБ"), color=KeyboardButtonColor.SECONDARY)
    .row()
    .add(Text("1 ТБ"),   color=KeyboardButtonColor.SECONDARY)
    .add(Text("Другой"), color=KeyboardButtonColor.SECONDARY)
    .row()
    .add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE)
    .get_json()
)

SCREEN_KB = (
    Keyboard(one_time=True)
    .add(Text("✨ Отличное"),          color=KeyboardButtonColor.POSITIVE)
    .add(Text("👍 Хорошее"),           color=KeyboardButtonColor.POSITIVE)
    .row()
    .add(Text("😐 Удовлетворительное"), color=KeyboardButtonColor.SECONDARY)
    .add(Text("💔 Повреждён"),          color=KeyboardButtonColor.NEGATIVE)
    .row()
    .add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE)
    .get_json()
)

BATTERY_KB = (
    Keyboard(one_time=True)
    .add(Text("🔋 90–100%"), color=KeyboardButtonColor.POSITIVE)
    .add(Text("🔋 80–89%"),  color=KeyboardButtonColor.POSITIVE)
    .row()
    .add(Text("🔋 70–79%"),  color=KeyboardButtonColor.SECONDARY)
    .add(Text("🪫 Ниже 70%"), color=KeyboardButtonColor.NEGATIVE)
    .row()
    .add(Text("❓ Не знаю"), color=KeyboardButtonColor.SECONDARY)
    .add(Text("❌ Отмена"),  color=KeyboardButtonColor.NEGATIVE)
    .get_json()
)

BODY_KB = (
    Keyboard(one_time=True)
    .add(Text("✨ Отличное"),          color=KeyboardButtonColor.POSITIVE)
    .add(Text("👍 Хорошее"),           color=KeyboardButtonColor.POSITIVE)
    .row()
    .add(Text("😐 Удовлетворительное"), color=KeyboardButtonColor.SECONDARY)
    .add(Text("💔 Повреждён"),          color=KeyboardButtonColor.NEGATIVE)
    .row()
    .add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE)
    .get_json()
)

BUYOUT_OFFER_KB = (
    Keyboard(one_time=True)
    .add(Text("✅ Записаться на выкуп"), color=KeyboardButtonColor.POSITIVE)
    .row()
    .add(Text("❌ Нет, спасибо"),        color=KeyboardButtonColor.NEGATIVE)
    .get_json()
)


# ── Динамические клавиатуры ───────────────────────────────────────────────────

def name_kb(name: str) -> str:
    """Клавиатура с кнопкой подтверждения имени из профиля + отмена."""
    return (
        Keyboard(one_time=True)
        .add(Text(f"✅ {name}"), color=KeyboardButtonColor.POSITIVE)
        .row()
        .add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE)
        .get_json()
    )


def phone_kb(phone: str) -> str:
    """Клавиатура с кнопкой подтверждения телефона из профиля + отмена."""
    return (
        Keyboard(one_time=True)
        .add(Text(f"📱 {phone}"), color=KeyboardButtonColor.POSITIVE)
        .row()
        .add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE)
        .get_json()
    )


def date_kb() -> str:
    today    = date.today()
    tomorrow = today + timedelta(days=1)
    day2     = today + timedelta(days=2)
    return (
        Keyboard(one_time=True)
        .add(Text(f"Сегодня ({today.strftime('%d.%m')})"),    color=KeyboardButtonColor.SECONDARY)
        .add(Text(f"Завтра ({tomorrow.strftime('%d.%m')})"),  color=KeyboardButtonColor.SECONDARY)
        .row()
        .add(Text(day2.strftime("%d.%m")),                    color=KeyboardButtonColor.SECONDARY)
        .add(Text("⏭ Пропустить"),                            color=KeyboardButtonColor.SECONDARY)
        .get_json()
    )
