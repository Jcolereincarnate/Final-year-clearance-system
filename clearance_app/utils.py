"""
Utility functions for the clearance system
"""
from .models import AuditLog


def create_audit_log(user, action, description, ip_address=None, clearance=None):
    """Create an audit log entry"""
    try:
        AuditLog.objects.create(
            user=user,
            action=action,
            description=description,
            ip_address=ip_address,
            clearance=clearance
        )
    except Exception as e:
        # Log error but don't break the flow
        print(f"Error creating audit log: {e}")


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip