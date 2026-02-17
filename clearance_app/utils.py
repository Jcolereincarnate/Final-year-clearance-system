from .models import AuditLog
from django.core.mail import send_mail
from django.conf import settings



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
        print(f"Error creating audit log: {e}")


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def send_email_notification(subject, message, receipient_email):
       send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[receipient_email],
        fail_silently=False,
    )