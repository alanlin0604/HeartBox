"""Simple audit logging helper."""
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Extract client IP. Behind Cloud Run, the real client IP is the
    rightmost entry in X-Forwarded-For (appended by the trusted proxy).
    We take the rightmost non-private entry, falling back to REMOTE_ADDR."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        # Rightmost entry is added by the trusted reverse proxy (Cloud Run)
        ips = [ip.strip() for ip in xff.split(',')]
        if ips:
            return ips[-1]
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
