from django.core.mail import send_mail
from django.conf import settings

def email_user(to_email, subject, message):
    """Sends an email notification to a user."""
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [to_email],
        fail_silently=False,
    )
