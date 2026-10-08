import os

from apps.accounts.models import HunterProfile, User, UserRole
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Seeds initial local development accounts (hunter, company admin, platform admin)."

    def handle(self, *args, **options):
        # Refuse to run unless DEBUG is True / running in local environment
        if not getattr(settings, "DEBUG", False) or "local" not in getattr(
            settings, "SETTINGS_MODULE", os.environ.get("DJANGO_SETTINGS_MODULE", "")
        ):
            raise CommandError(
                "Security Guard: seed_dev_users can only be run in local development environments (DEBUG=True)."
            )

        # 1. Platform Admin / Superuser
        admin_email = "admin@gmail.com"
        admin_pass = "123456"  # nosec B105
        admin_user, created = User.objects.get_or_create(
            email=admin_email,
            defaults={
                "role": UserRole.PLATFORM_ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "is_verified": True,
                "mfa_enabled": False,  # Ready for user to configure in /settings/security
            },
        )
        admin_user.set_password(admin_pass)
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.is_verified = True
        admin_user.role = UserRole.PLATFORM_ADMIN
        admin_user.save()
        self.stdout.write(
            self.style.SUCCESS(
                f"Configured platform admin: {admin_email} / {admin_pass}"
            )
        )

        # 2. Security Researcher / Hunter
        hunter_email = "hunter@gmail.com"
        hunter_pass = "123456"  # nosec B105
        hunter_user, created = User.objects.get_or_create(
            email=hunter_email,
            defaults={
                "role": UserRole.HUNTER,
                "is_verified": True,
                "mfa_enabled": False,
            },
        )
        hunter_user.set_password(hunter_pass)
        hunter_user.is_verified = True
        hunter_user.role = UserRole.HUNTER
        hunter_user.save()
        HunterProfile.objects.get_or_create(
            user=hunter_user,
            defaults={
                "username": "hunter",
                "bio": "Passionate web security researcher and bug hunter.",
                "is_public": True,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Configured hunter user: {hunter_email} / {hunter_pass}"
            )
        )

        # 3. Company Admin
        company_email = "company@cybereco.local"
        company_pass = "CompanyPass123!"  # nosec B105
        company_user, created = User.objects.get_or_create(
            email=company_email,
            defaults={
                "role": UserRole.COMPANY_ADMIN,
                "is_verified": True,
                "mfa_enabled": False,
            },
        )
        company_user.set_password(company_pass)
        company_user.is_verified = True
        company_user.role = UserRole.COMPANY_ADMIN
        company_user.save()
        self.stdout.write(
            self.style.SUCCESS(
                f"Configured company admin: {company_email} / {company_pass}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS("All development accounts seeded successfully!")
        )
