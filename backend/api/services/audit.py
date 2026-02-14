"""Simple audit logging helper."""
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_action(user, action, request=None, target_type='', target_id=None, details=None):
    """Create an audit log entry. Fire-and-forget; never raises."""
    try:
        from api.models import AuditLog
        AuditLog.objects.create(
            user=user,
            action=action,
            target_type=target_type,
            target_id=target_id,
            ip_address=get_client_ip(request) if request else None,
            details=details or {},
        )
    except Exception as e:
        logger.warning('Audit log failed: %s', e)
