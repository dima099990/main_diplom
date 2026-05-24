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

    open_statuses = ['new', 'diagnosis', 'waiting_parts', 'in_progress', 'approval']
    open_orders_count = RepairOrder.objects.filter(status__in=open_statuses).count()

    unread_notifications_count = Notification.objects.filter(
        user=request.user, is_read=False
    ).count()

    # Новые записи (с сайта + из Telegram) для значка в сайдбаре
    new_appointments_count = Appointment.objects.filter(
        status='new', source__in=('website', 'telegram')
    ).count() if role in ('admin', 'manager') else 0

    is_admin   = role == 'admin'
    is_manager = role in ('admin', 'manager')  # admin тоже считается менеджером

    return {
        'role': role,
        'is_admin': is_admin,
        'is_manager': is_manager,
        'user_role_display': role_display,
        'open_orders_count': open_orders_count,
        'unread_notifications_count': unread_notifications_count,
        'new_appointments_count': new_appointments_count,
    }
