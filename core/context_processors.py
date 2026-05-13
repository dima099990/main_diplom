from .models import SiteSettings


def site_settings(request):
    return {'site': SiteSettings.get()}


def crm_context(request):
    if not request.user.is_authenticated or not request.path.startswith('/crm/'):
        return {}
    from crm.decorators import get_role
    from crm.models import UserProfile
    from core.models import CallRequest
    role = get_role(request.user)
    try:
        role_display = dict(UserProfile.ROLES).get(role, role)
    except Exception:
        role_display = role
    return {
        'role': role,
        'user_role_display': role_display,
        'call_req_count': CallRequest.objects.filter(is_processed=False).count() if role in ('admin', 'manager') else 0,
    }
