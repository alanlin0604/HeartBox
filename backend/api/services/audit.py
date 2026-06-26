"""Simple audit logging helper."""
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Extract client IP from X-Forwarded-For, walking right-to-left and
    skipping known trusted-proxy IPs.

    XFF is appended-only: ``<client>, <proxy1>, <proxy2>``. The leftmost
    entry is what the original client sent (spoofable!), the rightmost is
    appended by the last hop. The correct algorithm is:
      1. Start at the rightmost entry (the last trusted appender).
      2. Walk left, skipping any IP in ``settings.TRUSTED_PROXIES``.
      3. The first non-trusted entry is the real client IP.

    Falls back to ``REMOTE_ADDR`` when XFF is missing OR when every entry
    is in TRUSTED_PROXIES (which would mean the request never crossed a
    public boundary). Configure via ``settings.TRUSTED_PROXIES`` — empty
    set means "trust whichever side of XFF we land on" (legacy behavior).
    """
    from django.conf import settings as _s
    trusted = set(getattr(_s, 'TRUSTED_PROXIES', set()) or set())
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        ips = [ip.strip() for ip in xff.split(',') if ip.strip()]
        for ip in reversed(ips):
            if ip not in trusted:
                return ip
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
