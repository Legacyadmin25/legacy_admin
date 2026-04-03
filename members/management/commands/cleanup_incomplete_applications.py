from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
import logging
from datetime import timedelta

from members.utils.autosave_cleanup import cleanup_stale_applications

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Cleans up stale incomplete applications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days of inactivity to consider an application stale'
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete stale applications instead of marking them as abandoned'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it'
        )

    def handle(self, *args, **options):
        days_threshold = options['days']
        mark_as_abandoned = not options['delete']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days_threshold)
        
        self.stdout.write(f"Looking for incomplete applications with no activity since {cutoff_date}")
        
        if dry_run:
            from members.models_incomplete import IncompleteApplication
            count = IncompleteApplication.objects.filter(
                last_activity__lt=cutoff_date,
                status__in=['draft', 'in_progress']
            ).count()
            
            action = "mark as abandoned" if mark_as_abandoned else "delete"
            self.stdout.write(
                self.style.WARNING(f"DRY RUN: Would {action} {count} stale applications")
            )
        else:
            count = cleanup_stale_applications(
                days_threshold=days_threshold,
                mark_as_abandoned=mark_as_abandoned
            )
            
            action = "marked as abandoned" if mark_as_abandoned else "deleted"
            self.stdout.write(
                self.style.SUCCESS(f"Successfully {action} {count} stale applications")
            )
