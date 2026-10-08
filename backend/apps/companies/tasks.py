"""Celery tasks for background operations such as DNS verification."""

from celery import shared_task

from .models import OrganizationVerifiedDomain
from .services import verify_domain_dns_txt


@shared_task(rate_limit="10/m")
def verify_organization_domain_dns_task(domain_id: str):
    """Celery task to verify DNS TXT record for a domain in background."""
    try:
        domain_obj = OrganizationVerifiedDomain.objects.get(id=domain_id)
        if not domain_obj.is_verified:
            verify_domain_dns_txt(domain_obj)
    except OrganizationVerifiedDomain.DoesNotExist:
        pass
