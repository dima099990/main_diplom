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
    .add(Text("💬 Задать вопрос"), color=KeyboardButtonColor.SECONDARY)
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


# ── Динамические клавиатуры ───────────────────────────────────────────────────

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
