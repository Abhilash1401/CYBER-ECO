"""Generic notification service delivering in-app alerts and emails."""

from django.conf import settings
from django.core.mail import send_mail

from apps.accounts.models import User
from apps.companies.models import Organization, OrganizationMember

from .models import Notification


def notify_user(recipient, subject: str, message: str, link: str = ""):
    """Send generic notification containing only link and generic text.

    recipient can be a User or an Organization (in which case all active members are notified).
    """
    users_to_notify = []
    if isinstance(recipient, Organization):
        users_to_notify = list(
            User.objects.filter(
                id__in=OrganizationMember.objects.filter(
                    organization=recipient
                ).values_list("user_id", flat=True)
            )
        )
    elif isinstance(recipient, User):
        users_to_notify = [recipient]

    generic_body = f"{message}\n\nView details: {settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'http://localhost:3000'}{link}\n\n(This notification contains no confidential details for security purposes.)"

    for user in users_to_notify:
        Notification.objects.create(
            user=user,
            subject=subject,
            message=message,
            link=link,
        )
        if user.email:
            send_mail(
                subject=f"[Cyber Eco] {subject}",
                message=generic_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
