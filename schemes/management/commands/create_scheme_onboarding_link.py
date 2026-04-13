from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from branches.models import Branch
from schemes.onboarding.models import BranchSchemeOnboarding


class Command(BaseCommand):
    help = 'Create a secure scheme self-onboarding link for a branch.'

    def add_arguments(self, parser):
        parser.add_argument('--branch', type=int, required=True, help='Branch ID')
        parser.add_argument('--expires', type=int, default=7, help='Expiry in days (default: 7)')

    def handle(self, *args, **options):
        try:
            branch = Branch.objects.get(pk=options['branch'])
        except Branch.DoesNotExist as exc:
            raise CommandError('Branch not found.') from exc

        expires_at = timezone.now() + timedelta(days=options['expires'])
        onboarding = BranchSchemeOnboarding.create_with_token(branch=branch, expires_at=expires_at)

        site = getattr(settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')
        link = f"{site}/scheme-onboarding/start/{onboarding.onboarding_token}/"

        self.stdout.write(self.style.SUCCESS('Scheme onboarding link created.'))
        self.stdout.write(f'Branch: {branch.name}')
        self.stdout.write(f'Token: {onboarding.onboarding_token}')
        self.stdout.write(f'Expires: {onboarding.expires_at}')
        self.stdout.write(f'URL: {link}')
