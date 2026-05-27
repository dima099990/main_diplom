"""
Слой доступа к данным для VK-бота.

Использует Django ORM и ОБЩУЮ базу данных проекта.
VK user ID хранится в поле telegram_id модели Customer (без миграций).
"""
import django_setup  # noqa — must be first

from asgiref.sync import sync_to_async

from core.models import SiteSettings, Brand, RepairService
from crm.models import Appointment, Customer


# ══════════════════════════════════════════════════════════════════════════
# SYNC-функции
# ══════════════════════════════════════════════════════════════════════════

def _get_settings() -> SiteSettings:
    return SiteSettings.get()


def _get_customer_by_vk(vk_id: int | str) -> Customer | None:
    return Customer.objects.filter(telegram_id=str(vk_id)).first()


def _get_or_create_customer_from_vk(
    vk_id: int | str,
    name: str,
    phone: str,
    pd_consent: bool = False,
) -> tuple[Customer, bool]:
    """
    Находит или создаёт клиента по VK user ID.
    VK ID хранится в поле telegram_id.
    Порядок поиска: vk_id → номер телефона → создать нового.
    """
    from django.utils import timezone

    tid = str(vk_id)
    full_name = name.strip() or "Клиент"

    # 1. Ищем по VK ID
    customer = Customer.objects.filter(telegram_id=tid).first()
    if customer:
        return customer, False

    # 2. Ищем по последним 10 цифрам телефона
    digits = "".join(c for c in phone if c.isdigit())
    last10 = digits[-10:] if len(digits) >= 10 else digits
    if last10:
        customer = Customer.objects.filter(phone__endswith=last10).first()
        if customer:
            customer.telegram_id = tid
            if not customer.name:
                customer.name = full_name
            customer.save(update_fields=["telegram_id", "name"])
            return customer, False

    # 3. Создаём нового клиента
    phone_fmt = f"+{digits}" if digits and not phone.startswith("+") else phone
    customer = Customer.objects.create(
        name=full_name,
        phone=phone_fmt or phone,
        telegram_id=tid,
        pd_consent=pd_consent,
        pd_consent_at=timezone.now() if pd_consent else None,
    )
    return customer, True


def _search_prices(query: str) -> list[dict]:
    q = query.strip()
    qs = (
        RepairService.objects.select_related("phone_model__brand")
        .filter(is_active=True, phone_model__name__icontains=q)
        | RepairService.objects.select_related("phone_model__brand")
        .filter(is_active=True, name__icontains=q)
        | RepairService.objects.select_related("phone_model__brand")
        .filter(is_active=True, phone_model__brand__name__icontains=q)
    )
    results = []
    for svc in qs.distinct()[:20]:
        price_str = f"от {svc.price_from} ₽"
        if svc.price_to and svc.price_to != svc.price_from:
            price_str = f"{svc.price_from}–{svc.price_to} ₽"
        results.append({
            "service":  svc.name,
            "model":    svc.phone_model.name if svc.phone_model else "—",
            "brand":    svc.phone_model.brand.name if svc.phone_model and svc.phone_model.brand else "—",
            "price":    price_str,
            "duration": svc.duration or "",
        })
    return results


def _get_all_prices_text() -> str:
    lines = []
    for brand in Brand.objects.filter(is_active=True).prefetch_related(
        "phone_models__services"
    ):
        for model in brand.phone_models.filter(is_active=True):
            services = model.services.filter(is_active=True)
            if not services.exists():
                continue
            lines.append(f"\n{brand.name} {model.name}:")
            for svc in services:
                price_str = f"от {svc.price_from} ₽"
                if svc.price_to and svc.price_to != svc.price_from:
                    price_str = f"{svc.price_from}–{svc.price_to} ₽"
                lines.append(f"  - {svc.name}: {price_str}")
    return "\n".join(lines) if lines else "Прайс пока не заполнен."


def _create_appointment(
    name: str,
    phone: str,
    device: str,
    problem: str,
    vk_user_id: int | str,
    preferred_date=None,
    preferred_time=None,
) -> Appointment:
    return Appointment.objects.create(
        name=name,
        phone=phone,
        device=device,
        problem=problem,
        source="vk",
        telegram_chat_id=str(vk_user_id),
        status="new",
        preferred_date=preferred_date,
        preferred_time=preferred_time,
    )


# ══════════════════════════════════════════════════════════════════════════
# ASYNC-обёртки
# ══════════════════════════════════════════════════════════════════════════

get_settings                  = sync_to_async(_get_settings)
get_customer_by_vk            = sync_to_async(_get_customer_by_vk)
get_or_create_customer_from_vk = sync_to_async(_get_or_create_customer_from_vk)
search_prices                 = sync_to_async(_search_prices)
get_all_prices_text           = sync_to_async(_get_all_prices_text)
create_appointment            = sync_to_async(_create_appointment)
