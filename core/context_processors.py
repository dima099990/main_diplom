from .models import SiteSettings


def site_settings(request):
    return {'site': SiteSettings.get()}


def crm_context(request):
    if not request.user.is_authenticated or not request.path.startswith('/crm/'):
        return {}
    from crm.models import Notification, RepairOrder, UserProfile
    from core.models import CallRequest

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

    return {
        'role': role,
        'user_role_display': role_display,
        'call_req_count': CallRequest.objects.filter(is_processed=False).count() if role in ('admin', 'manager') else 0,
        'open_orders_count': open_orders_count,
        'unread_notifications_count': unread_notifications_count,
    }
