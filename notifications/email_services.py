from django.core.mail import send_mail
from django.conf import settings
import logging


logger = logging.getLogger(__name__)

def send_email_notification(to_email, subject, message):
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            fail_silently=False,
        )
        logger.info(f"Email sent successfully to {to_email}")

    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {e}")
        print(f"Error sending email: {e}")
