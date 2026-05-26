from .models import SiteSettings


def site_settings(request):
    return {'site': SiteSettings.get()}


def crm_context(request):
    if not request.user.is_authenticated or not request.path.startswith('/crm/'):
        return {}
    from crm.models import Notification, RepairOrder, UserProfile, Appointment

    try:
        profile = request.user.profile
        role = profile.role
    except Exception:
        role = 'employee'

    try:
        role_display = dict(UserProfile.ROLES).get(role, role)
    except Exception:
        role_display = role

    is_admin   = role == 'admin'
    is_manager = role in ('admin', 'manager')

    open_statuses = ['new', 'diagnosis', 'waiting_parts', 'in_progress', 'approval']

    # Определяем активный филиал сотрудника
    try:
        active_branch = profile.branch  # FK — текущая точка работы
    except Exception:
        active_branch = None

    # Счётчик открытых заказов: для админа/менеджера — все, для остальных — только своей точки
    orders_qs = RepairOrder.objects.filter(status__in=open_statuses)
    if not is_manager and active_branch:
        orders_qs = orders_qs.filter(branch=active_branch)
    elif not is_manager and not active_branch:
        orders_qs = orders_qs.none()
    open_orders_count = orders_qs.count()

    unread_notifications_count = Notification.objects.filter(
        user=request.user, is_read=False
    ).count()

    # Новые записи (с сайта + из Telegram) для значка в сайдбаре
    if role in ('admin', 'manager'):
        new_appointments_count = Appointment.objects.filter(
            status='new', source__in=('website', 'telegram')
        ).count()
    elif active_branch:
        new_appointments_count = Appointment.objects.filter(
            status='new', source__in=('website', 'telegram'),
            branch=active_branch,
        ).count()
    else:
        new_appointments_count = 0

    return {
        'role': role,
        'is_admin': is_admin,
        'is_manager': is_manager,
        'user_role_display': role_display,
        'open_orders_count': open_orders_count,
        'unread_notifications_count': unread_notifications_count,
        'new_appointments_count': new_appointments_count,
    }
